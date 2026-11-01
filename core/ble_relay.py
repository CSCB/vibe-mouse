"""
BLE 继电器控制模块（集成自 ble_switch 项目）

3 通道 BLE 继电器（JDY 蓝牙透传方案）的连接、鉴权与控制。
独立 asyncio 事件循环线程，对外暴露非阻塞同步 API，
供 executor（relay:on_1 动作）、feedback（硬件反馈）和 GUI 面板共享。

协议:
  写特征 TX 0000ff68-...  控制帧 / AT 指令
  通知特征 RX 0000ff69-...  状态帧 START<12位0/1>@ 与 AT 回复
  鉴权: 连接后 1 秒发送 AT+SEND<password>@
  控制帧: FD <channel> 80(open)/90(close) 00 00 00 00 00 DF
  AT: AT+NAME...@ 改名 / AT+PIN6位@ 改密，回复 PIN PASS / PIN ERROR / Name Set OK

自测: python -m core.ble_relay  （扫描 → 连接第一个 ff26 设备 → 通道1通电2秒 → 断开）
"""
import asyncio
import re
import threading

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "0000ff26-0000-1000-8000-00805f9b34fb"
TX_UUID = "0000ff68-0000-1000-8000-00805f9b34fb"  # 写 (Write)
RX_UUID = "0000ff69-0000-1000-8000-00805f9b34fb"  # 通知 (Notify)

# relay:on_1 / relay_on_1 / relay:off_2 / relay_pulse_3 / relay:toggle_3
RELAY_ACTION_RE = re.compile(r"^relay[:_](on|off|toggle|pulse)[_:](\d{1,2})$")

# 默认配置（写入 config.json 的 ble_relay 字段）
DEFAULT_BLE_RELAY = {
    "enabled": True,
    "auto_connect": True,
    "last_address": "",
    "last_name": "",
    "password": "151811",
    "channels": 3,
    "scan_timeout": 5.0,
    "ui_expanded": False,
}

# 重连尝试上限，防止设备离电时无限循环耗电
_MAX_RECONNECT = 3

# 两次写控制帧之间的最小间隔（秒）。
# 实测继电器 MCU 对毫秒级连发会丢帧（如 on_submit 表连发 通道2 on + 通道3 off 时，
# 通道2 的帧被静默丢弃，状态帧无该通道回报），逐帧保持间隔后全部可靠生效
_WRITE_GAP_S = 0.2


def parse_relay_action(action_name):
    """解析 relay 动作字符串，返回 (verb, channel) 或 None"""
    m = RELAY_ACTION_RE.match(action_name.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2))


class RelayController:
    """BLE 继电器控制器（进程内单例，见 get_relay_controller）"""

    def __init__(self, config):
        self.config = config
        self.client = None
        self.is_connected = False

        # 回调订阅列表（在 asyncio 线程触发；UI 层需自行 marshal 到主线程。
        # 多订阅者安全：面板与设置对话框各自 append，关闭时 remove）
        self.on_scan_result = []          # list[(name, address)]
        self.on_connection_change = []    # str 状态文本
        self.on_status_update = []        # dict{channel: bool}
        self.on_raw_msg = []              # str AT 回复（PIN PASS 等）

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()

        self._discovered_devices = {}
        self._status = {}                 # {channel: bool} 状态缓存
        self._status_lock = threading.Lock()
        self._write_lock = asyncio.Lock()  # 串行化写特征值，防帧交错
        self._reconnect_count = 0
        self._shutting_down = False

    # ------------------------------------------------------------------
    # 事件循环
    # ------------------------------------------------------------------
    def _start_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _submit(self, coro):
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError:
            pass  # loop 已关闭

    def _notify(self, callbacks, *args):
        for callback in list(callbacks):
            try:
                callback(*args)
            except Exception as e:
                print(f"[Relay] 回调异常: {e}")

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    def scan(self, timeout=None):
        if timeout is None:
            timeout = self._relay_cfg().get("scan_timeout", 5.0)
        self._notify(self.on_connection_change, "Scanning...")
        self._submit(self._scan_task(timeout))

    async def _scan_task(self, timeout):
        devices = await BleakScanner.discover(timeout=timeout)
        device_list = []
        self._discovered_devices = {}
        for d in devices:
            if d.name:  # 只保留有名称的设备
                device_list.append((d.name, d.address))
                self._discovered_devices[d.address] = d
        self._notify(self.on_scan_result, device_list)
        self._notify(self.on_connection_change, "Scan Complete")

    def connect(self, address, password=None):
        if password is None:
            password = self._relay_cfg().get("password", "151811")
        self._submit(self._connect_task(address, password))

    def disconnect(self):
        self._submit(self._disconnect_task())

    async def _disconnect_task(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def _connect_task(self, address, password):
        self._notify(self.on_connection_change, f"Connecting to {address}...")
        try:
            # 优先用扫描缓存的对象，否则重新解析（重启后缓存对象失效，必须重新扫描）
            device = self._discovered_devices.get(address)
            if device is None:
                self._notify(self.on_connection_change, "Resolving device...")
                device = await BleakScanner.find_device_by_address(address, timeout=5.0)
            if device is None:
                raise Exception("无法解析该地址的设备，请重新扫描")

            # 修复 Bleak 在 Windows 下只收到 SCAN_RSP 导致 adv 为 None 的 bug
            if hasattr(device, "details") and device.details is not None:
                adv = getattr(device.details, "adv", None)
                scan = getattr(device.details, "scan", None)
                if adv is None and scan is not None:
                    class _PatchedDetails:
                        def __init__(self, s):
                            self.adv = s
                            self.scan = s
                    device.details = _PatchedDetails(scan)

            self.client = BleakClient(device, disconnected_callback=self._handle_disconnect)
            await self.client.connect()
            self.is_connected = True
            self._reconnect_count = 0

            # 记住设备用于自动重连
            cfg = self._relay_cfg()
            cfg["last_address"] = address
            cfg["last_name"] = getattr(device, "name", "") or ""
            self._save_relay_cfg()

            # 订阅状态通知
            await self.client.start_notify(RX_UUID, self._notification_handler)

            # 连接后 1 秒发送鉴权密码
            self._notify(self.on_connection_change, "Authenticating...")
            await asyncio.sleep(1)
            async with self._write_lock:
                await self.client.write_gatt_char(
                    TX_UUID, f"AT+SEND{password}@".encode("utf-8"))

            self._notify(self.on_connection_change,
                         f"Connected: {cfg.get('last_name') or address}")

        except Exception as e:
            print(f"[Relay] 连接失败: {e}")
            self.is_connected = False
            self._notify(self.on_connection_change, f"Connection Failed: {e}")
            # 初始连接失败也安排自动重试（此前只有已连接后断开才会重连，
            # 导致启动时设备未就绪就一直处于断开状态）
            self._schedule_reconnect(address)

    def _schedule_reconnect(self, address=None):
        """安排一次自动重连（受 auto_connect 与最大次数限制）"""
        cfg = self._relay_cfg()
        target = address or cfg.get("last_address")
        if (self._shutting_down
                or not cfg.get("auto_connect")
                or not target):
            return
        if self._reconnect_count >= _MAX_RECONNECT:
            print("[Relay] 自动重连次数用尽，停止重连")
            return
        self._reconnect_count += 1
        print(f"[Relay] 3秒后自动重连 ({self._reconnect_count}/{_MAX_RECONNECT})...")
        self._submit(self._auto_reconnect_task(target))

    def _handle_disconnect(self, client):
        self.is_connected = False
        with self._status_lock:
            self._status = {}
        self._notify(self.on_status_update, dict(self._status))
        self._notify(self.on_connection_change, "Disconnected")

        # 自动重连（与初始连接失败共用同一重试逻辑）
        self._schedule_reconnect(self._relay_cfg().get("last_address"))

    async def _auto_reconnect_task(self, address):
        await asyncio.sleep(3)
        if not self._shutting_down and not self.is_connected:
            # 注意：这里不能回退 _reconnect_count，否则失败重试的计数
            # 永远在 0/1 之间震荡，_MAX_RECONNECT 上限失效导致无限重连。
            # 计数只在连接成功时清零（见 _connect_task）。
            await self._connect_task(address, self._relay_cfg().get("password", "151811"))

    # ------------------------------------------------------------------
    # 控制指令
    # ------------------------------------------------------------------
    def set_channel(self, channel, on):
        self._submit(self._set_channel_task(channel, on))

    async def _paced_write(self, frame):
        """写控制帧并保持帧间隔（须在持有 _write_lock 时调用），防止 MCU 丢帧"""
        await self.client.write_gatt_char(TX_UUID, frame)
        await asyncio.sleep(_WRITE_GAP_S)

    async def _set_channel_task(self, channel, on):
        if not self.is_connected or not self.client:
            print("[Relay] 未连接，忽略通道指令")
            return
        frame = self._frame(channel, 0x80 if on else 0x90)
        try:
            async with self._write_lock:
                await self._paced_write(frame)
            with self._status_lock:
                self._status[channel] = on
        except Exception as e:
            print(f"[Relay] 通道指令失败: {e}")

    def pulse_channel(self, channel, duration_ms=500):
        """通电 duration_ms 毫秒后自动断电（用于硬件反馈脉冲）"""
        self._submit(self._pulse_task(channel, duration_ms))

    async def _pulse_task(self, channel, duration_ms):
        if not self.is_connected or not self.client:
            return
        try:
            async with self._write_lock:
                await self._paced_write(self._frame(channel, 0x80))
                try:
                    await asyncio.sleep(duration_ms / 1000.0)
                finally:
                    # 无论中途断连还是异常，都尽力补发断电帧，
                    # 防止外设（灯/风扇）滞留在通电状态
                    try:
                        await self._paced_write(self._frame(channel, 0x90))
                        with self._status_lock:
                            self._status[channel] = False
                    except Exception as e:
                        print(f"[Relay] 脉冲复位失败（通道{channel}可能保持通电）: {e}")
        except Exception as e:
            print(f"[Relay] 脉冲失败: {e}")

    def drop_channel(self, channel, duration_ms=2000):
        """断电 duration_ms 毫秒后恢复通电（掉落模式：结束断电触发装置后复电待命）"""
        self._submit(self._drop_task(channel, duration_ms))

    async def _drop_task(self, channel, duration_ms):
        if not self.is_connected or not self.client:
            return
        try:
            async with self._write_lock:
                await self._paced_write(self._frame(channel, 0x90))  # 断电
                try:
                    await asyncio.sleep(duration_ms / 1000.0)
                finally:
                    # 无论中途断连还是异常，都尽力补发复电帧，
                    # 防止掉落装置滞留在断电状态
                    try:
                        await self._paced_write(self._frame(channel, 0x80))  # 复电
                        with self._status_lock:
                            self._status[channel] = True
                    except Exception as e:
                        print(f"[Relay] 复电失败（通道{channel}可能保持断电）: {e}")
        except Exception as e:
            print(f"[Relay] 掉落动作失败: {e}")

    def send_at(self, cmd_str):
        self._submit(self._send_at_task(cmd_str))

    async def _send_at_task(self, cmd_str):
        if not self.is_connected or not self.client:
            print("[Relay] 未连接，忽略 AT 指令")
            return
        try:
            async with self._write_lock:
                await self.client.write_gatt_char(TX_UUID, cmd_str.encode("utf-8"))
        except Exception as e:
            print(f"[Relay] AT 指令失败: {e}")

    def get_status(self):
        with self._status_lock:
            return dict(self._status)

    @property
    def channels(self):
        return int(self._relay_cfg().get("channels", 3))

    # ------------------------------------------------------------------
    # 通知解析
    # ------------------------------------------------------------------
    def _notification_handler(self, sender, data):
        try:
            msg = data.decode("utf-8")
            if msg.startswith("START") and msg.endswith("@"):
                status_str = msg[5:-1]
                status_dict = {i + 1: (c == "1") for i, c in enumerate(status_str[:12])}
                with self._status_lock:
                    self._status.update(status_dict)
                self._notify(self.on_status_update, status_dict)
            else:
                # PIN PASS / PIN ERROR / Name Set OK 等 AT 回复
                self._notify(self.on_raw_msg, msg)
        except UnicodeDecodeError:
            pass
        except Exception as e:
            print(f"[Relay] 通知解析异常: {e}")

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _frame(channel, action_hex):
        return bytearray([0xFD, channel, action_hex, 0x00, 0x00, 0x00, 0x00, 0x00, 0xDF])

    def _relay_cfg(self):
        cfg = getattr(self.config, "ble_relay", None)
        if cfg is None:
            cfg = dict(DEFAULT_BLE_RELAY)
        return cfg

    def _save_relay_cfg(self):
        try:
            if hasattr(self.config, "save_config"):
                self.config.save_config()
        except Exception as e:
            print(f"[Relay] 配置保存失败: {e}")

    def shutdown(self):
        """停事件循环并断开连接（应用退出时调用）"""
        self._shutting_down = True

        async def _graceful():
            try:
                # 退出前把已通电的通道断电，防止灯/风扇在应用关闭后滞留
                if self.client and self.client.is_connected:
                    with self._status_lock:
                        on_channels = [ch for ch, on in self._status.items() if on]
                    for ch in on_channels:
                        try:
                            async with self._write_lock:
                                await self.client.write_gatt_char(
                                    TX_UUID, self._frame(ch, 0x90))
                        except Exception:
                            pass
            finally:
                try:
                    await self._disconnect_task()
                finally:
                    self._loop.stop()

        try:
            # 等待断开完成（未连接时瞬间返回；最长等 2 秒防退出卡死）
            asyncio.run_coroutine_threadsafe(_graceful(), self._loop).result(timeout=2)
        except Exception:
            try:
                self._loop.stop()
            except RuntimeError:
                pass


# ----------------------------------------------------------------------
# 进程内单例
# ----------------------------------------------------------------------
_relay_instance = None
_relay_lock = threading.Lock()


def get_relay_controller(config=None):
    """获取 RelayController 单例。config.ble_relay.enabled=False 时返回 None"""
    global _relay_instance
    if config is not None and not getattr(config, "ble_relay", {}).get("enabled", True):
        return None
    with _relay_lock:
        if _relay_instance is None and config is not None:
            _relay_instance = RelayController(config)
        return _relay_instance


# ----------------------------------------------------------------------
# 命令行自测：python -m core.ble_relay
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import time as _time

    class _Cfg:
        ble_relay = dict(DEFAULT_BLE_RELAY)
        def save_config(self):
            pass

    ctrl = RelayController(_Cfg())
    ctrl.on_scan_result.append(lambda devs: print(
        f"[自测] 扫描到 {len(devs)} 个有名设备:",
        *(f"\n  {n} ({a})" for n, a in devs[:10]) or ""))
    ctrl.on_connection_change.append(lambda s: print(f"[自测] 状态: {s}"))
    ctrl.on_status_update.append(lambda d: print(f"[自测] 设备状态帧: {d}"))
    ctrl.on_raw_msg.append(lambda m: print(f"[自测] 设备回复: {m}"))

    print("[自测] 扫描中...")
    ctrl.scan(5.0)
    _time.sleep(6.5)

    addr = _Cfg.ble_relay.get("last_address") or input(
        "输入继电器 MAC 地址（回车跳过连接测试）: ").strip()
    if addr:
        ctrl.connect(addr)
        _time.sleep(8)  # 等待连接 + 鉴权
        if ctrl.is_connected:
            print("[自测] 通道 1 通电 2 秒...")
            ctrl.set_channel(1, True)
            _time.sleep(2)
            ctrl.set_channel(1, False)
            _time.sleep(1)
            ctrl.disconnect()
            _time.sleep(1)
    ctrl.shutdown()
    print("[自测] 完成")
