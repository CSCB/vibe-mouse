import os
import sys
import json
import time
import threading
import platform
from typing import Optional
from pynput.keyboard import Controller, Key, KeyCode
from .feedback import FeedbackManager, FeedbackTiming
from .voice_llm import VoiceLLMBridge
from .skill_engine import SkillEngine
from .ble_relay import parse_relay_action, get_relay_controller

# Windows API for reliable keyboard input (Electron/Chromium 兼容)
_IS_WINDOWS = platform.system() == "Windows"
if _IS_WINDOWS:
    import ctypes
    _user32 = ctypes.windll.user32

    # 虚拟键码映射
    _VK_MAP = {
        Key.ctrl: 0x11,       # VK_CONTROL (不是 VK_LCONTROL)
        Key.cmd: 0x5B,        # VK_LWIN
        Key.alt: 0x12,        # VK_MENU
        Key.shift: 0x10,      # VK_SHIFT
        Key.enter: 0x0D,      # VK_RETURN
        Key.esc: 0x1B,        # VK_ESCAPE
        Key.space: 0x20,      # VK_SPACE
        Key.tab: 0x09,        # VK_TAB
        Key.backspace: 0x08,  # VK_BACK
        Key.delete: 0x2E,     # VK_DELETE
        Key.up: 0x26,         # VK_UP
        Key.down: 0x28,       # VK_DOWN
        Key.left: 0x25,       # VK_LEFT
        Key.right: 0x27,      # VK_RIGHT
    }

    KEYEVENTF_KEYDOWN = 0x0000
    KEYEVENTF_KEYUP = 0x0002

class ActionExecutor:
    def __init__(self, config):
        self.config = config
        self.keyboard = Controller()
        self.feedback = FeedbackManager(config.feedback if hasattr(config, 'feedback') else None)

        # Skill 引擎（整体功能层面）
        skill_config = config.skills if hasattr(config, 'skills') else None
        self.skill_engine = SkillEngine(skill_config) if skill_config else None

        # 当前激活的 Skill
        self._active_skill = None
        self._active_skill_context = {}

        # 语音输入状态：防止并发录音
        self._recording = False
        self._funasr_proc = None  # FunASR 常驻子进程
        self._trae_done_callback = None  # Trae 完成回调（由 main.py 注入）

        # 后台启动 FunASR 常驻服务
        self._preheat_whisper()

        # Trae 完成信号监听（监听信号文件，播放提示音）
        self._start_trae_notification_watcher()

        # 语音 + 大模型桥接器（华为云 Token Plan）
        tp_config = config.token_plan if hasattr(config, 'token_plan') else {}
        self.voice_llm = VoiceLLMBridge(tp_config, executor=self, skill_engine=self.skill_engine)

        # 字符串到 pynput.keyboard.Key 的映射
        self.key_map = {
            "ctrl": Key.ctrl,
            "cmd": Key.cmd,
            "alt": Key.alt,
            "shift": Key.shift,
            "enter": Key.enter,
            "esc": Key.esc,
            "space": Key.space,
            "tab": Key.tab,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right
        }

    def _notify_trae_done(self):
        """Trae AI 完成时的通知：独特蜂鸣 + 桌宠动画"""
        import threading
        def _beep():
            import winsound
            try:
                # 两声短促上扬蜂鸣，明显区别于 Trae 自带音效
                winsound.Beep(880, 150)   # A5
                winsound.Beep(1320, 200)  # E6
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()
        # 触发桌宠 done 动画
        if self._trae_done_callback:
            try:
                self._trae_done_callback()
            except Exception:
                pass
        # 走统一反馈管道（on_success 列表含 "relay" 时继电器脉冲等硬件反馈联动）
        try:
            self.feedback.trigger(FeedbackTiming.ON_SUCCESS, "ai_done")
        except Exception:
            pass
        # 事件音频：AI 结束播放 mama
        try:
            self.feedback.trigger_single("audio", FeedbackTiming.ON_SUCCESS, "ai_done")
        except Exception:
            pass

    def _start_trae_notification_watcher(self):
        """监控 ai-agent 日志：SessionControlStatus run/finish 标记精确检测"""
        import glob

        def _find_agent_log():
            """返回最新的 ai-agent stdout.log 路径（在 Modular/ 目录下）"""
            base = os.path.join(os.environ.get('APPDATA', ''), 'Trae CN', 'logs')
            if not os.path.isdir(base):
                return None
            dirs = sorted(glob.glob(os.path.join(base, '*T*')), reverse=True)
            for d in dirs:
                modular = os.path.join(d, 'Modular')
                if os.path.isdir(modular):
                    logs = sorted(glob.glob(os.path.join(modular, 'ai-agent_*stdout.log')), reverse=True)
                    if logs:
                        return logs[0]
                for root, dirs2, files in os.walk(d):
                    for fn in files:
                        if 'ai-agent' in fn and 'stdout' in fn and fn.endswith('.log'):
                            return os.path.join(root, fn)
            return None

        def _watch():
            import time as _time

            agent_log = _find_agent_log()
            if not agent_log:
                print("[Executor] 未找到 ai-agent 日志，完成通知不可用")
                return

            print(f"[Executor] SessionControl 监控启动: {agent_log}")

            offset = os.path.getsize(agent_log)
            state = "IDLE"  # IDLE: 等待 run, ACTIVE: 等待 finish

            while True:
                _time.sleep(0.5)
                try:
                    # 检查日志文件是否切换
                    new_log = _find_agent_log()
                    if new_log and new_log != agent_log:
                        agent_log = new_log
                        offset = 0
                        state = "IDLE"
                        continue

                    if not os.path.exists(agent_log):
                        continue

                    size = os.path.getsize(agent_log)
                    if size < offset:
                        offset = 0
                        state = "IDLE"

                    if size > offset:
                        with open(agent_log, 'r', encoding='utf-8', errors='replace') as f:
                            f.seek(offset)
                            new_data = f.read()
                        offset = size

                        # 检测开始标记
                        if state == "IDLE" and 'SessionControlStatus::run]' in new_data:
                            state = "ACTIVE"
                            print(f"[Executor] [SC] AI 对话开始")

                        # 检测完成标记
                        if state == "ACTIVE" and 'SessionControlStatus::finish]' in new_data:
                            state = "IDLE"
                            # 仅当前映射工具是 Trae 时才通知：
                            # 后台 Trae 的日志活动不应在其他工具下误触发蜂鸣/灯亮
                            if (getattr(self.config, "current_tool", "") or "trae") == "trae":
                                print(f"[Executor] [SC] AI 对话完成")
                                self._notify_trae_done()

                except Exception as e:
                    print(f"[Executor] SessionControl 监控异常: {e}")

        threading.Thread(target=_watch, daemon=True).start()

    def _preheat_whisper(self):
        """启动 FunASR 常驻后台服务（模型只加载一次）"""
        def _start():
            import subprocess
            print("[Executor] 启动 FunASR 常驻服务...")
            try:
                # stderr 记录到文件，便于排查 worker 崩溃原因
                self._funasr_err_file = open(
                    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "funasr_worker.err"), "ab"
                )
                self._funasr_proc = subprocess.Popen(
                    [sys.executable, "-u", "-m", "core.funasr_worker"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=self._funasr_err_file,
                    text=True,
                    encoding="utf-8",
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    # 强制子进程用 UTF-8 写管道，否则中文 Windows (cp936) 下
                    # 识别结果含中文时父进程按 utf-8 解码会抛 UnicodeDecodeError
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"}
                )
                # 等待 ready 信号（跳过 loading 行）
                while True:
                    line = self._funasr_proc.stdout.readline().strip()
                    if not line:
                        if self._funasr_proc.poll() is not None:
                            print("[Executor] FunASR 服务启动失败")
                            self._funasr_proc = None
                            return
                        continue
                    try:
                        data = json.loads(line)
                        status = data.get("status") or data.get("error", "")
                        if status == "ready":
                            print("[Executor] FunASR 常驻服务就绪")
                            return
                        elif "error" in data:
                            print(f"[Executor] FunASR 服务错误: {data['error']}")
                            self._funasr_proc = None
                            return
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                print(f"[Executor] FunASR 服务启动异常: {e}")
                self._funasr_proc = None
        threading.Thread(target=_start, daemon=True).start()

    def _get_key(self, key_str):
        key_str = key_str.lower()
        if key_str in self.key_map:
            return self.key_map[key_str]
        elif len(key_str) == 1:
            return KeyCode.from_char(key_str)
        return None

    def _send_keys(self, parsed_keys):
        """
        发送快捷键组合。

        Windows 上使用 keybd_event API，解决 pynput 对 Electron/Chromium 应用
        (Trae/Cursor/VSCode/Windsurf) 的快捷键发送不可靠问题。
        关键差异：使用 VK_CONTROL(0x11) 而非 pynput 默认的 VK_LCONTROL(0xA2)，
        因为 Chromium 对通用 VK_CONTROL 的响应更可靠。
        """
        if _IS_WINDOWS:
            # keybd_event 方式
            vk_codes = []
            for key in parsed_keys:
                vk = self._pynput_to_vk(key)
                if vk:
                    vk_codes.append(vk)

            if not vk_codes:
                raise ValueError("No valid VK codes")

            # 按下所有键（修饰键先按）
            for vk in vk_codes:
                _user32.keybd_event(vk, 0, KEYEVENTF_KEYDOWN, 0)
                time.sleep(0.02)

            # 保持一小段时间（Electron 需要更长的注册时间）
            time.sleep(0.08)

            # 反向释放所有键
            for vk in reversed(vk_codes):
                _user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.02)
        else:
            # 非 Windows：用 pynput 标准方式
            for key in parsed_keys:
                self.keyboard.press(key)
            time.sleep(0.08)
            for key in reversed(parsed_keys):
                self.keyboard.release(key)

    def _pynput_to_vk(self, key) -> int:
        """将 pynput 键对象转换为 Windows 虚拟键码"""
        if key in _VK_MAP:
            return _VK_MAP[key]
        if isinstance(key, KeyCode):
            char = key.char
            if char and len(char) == 1:
                # 字母/数字直接用大写 ASCII（VK_A = 0x41 ...）
                return ord(char.upper())
        return 0

    def execute_action(self, action_name):
        """
        执行动作。支持两种格式：
        - 原生动作："inline_edit", "toggle_chat" 等 → 按快捷键
        - Skill 引用："skill:<name>" → 触发 Skill（应用配置覆盖 + 激活上下文）
        """
        # ===== 1. 检查是否为 Skill 引用 =====
        if self.skill_engine and action_name.startswith("skill:"):
            self._execute_skill(action_name)
            return

        # ===== 1.5. 特殊处理：语音输入 (push-to-talk) =====
        if action_name == "voice_input":
            self._trigger_voice_input()
            return

        # ===== 1.55. 特殊处理：BLE 继电器动作 (relay:on_1 / relay_on_1) =====
        relay_parsed = parse_relay_action(action_name)
        if relay_parsed:
            self._execute_relay_action(*relay_parsed)
            return

        # ===== 1.6. 特殊处理：提交内容（激活窗口 + Enter 提交）=====
        if action_name in ("accept_diff", "submit_chat"):
            self._activate_tool_window()

        # ===== 2. 原生快捷键动作 =====
        shortcuts = self.config.get_current_shortcuts()
        if action_name not in shortcuts:
            print(f"[Executor] Action '{action_name}' not found in current tool shortcuts")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        keys_to_press = shortcuts[action_name]
        print(f"[Executor] 执行动作: {action_name} -> {keys_to_press}")

        # 注意：按键动作不播放声音反馈，避免与 AI 完成通知混淆
        parsed_keys = [self._get_key(k) for k in keys_to_press if self._get_key(k) is not None]

        if not parsed_keys:
            print(f"[Executor] No valid keys for action '{action_name}'")
            return

        try:
            self._send_keys(parsed_keys)
            # 提交对话 = AI 任务开始的确定性信号：灭灯（relay 常亮模式）。
            # 比 IO 推断"开始"更可靠：用户自己触发的动作，无噪声误判、不会漏判
            if action_name == "submit_chat":
                self.feedback.trigger_single("relay", FeedbackTiming.ON_RECEIVED, "ai_submit")
                self.feedback.trigger_single("audio", FeedbackTiming.ON_RECEIVED, "ai_submit")
        except Exception as e:
            print(f"[Executor] Error: {e}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)

    # ------------------------------------------------------------------
    # 语音输入 (Push-to-Talk)
    # ------------------------------------------------------------------
    def _trigger_voice_input(self):
        """
        触发语音输入。

        始终走应用内录音 → 语音识别，区别只在识别后的处理：
        A. Token Plan 已配置 → 识别文本 → VoiceLLMBridge（大模型纠错/生成/执行动作）→ 粘贴结果
        B. Token Plan 未配置 → 识别文本 → 直接粘贴到当前光标位置（纯语音转文字）
        """
        # 防止并发录音（双击中键可能触发多次）
        if self._recording:
            print("[Executor] 正在录音中，忽略重复触发")
            return
        self._recording = True

        # 通知 mascot 开始录音
        if hasattr(self, '_mascot_notify'):
            self._mascot_notify("recording_start")
        threading.Thread(target=self._record_and_process, daemon=True).start()

    def _execute_relay_action(self, verb, channel):
        """
        执行 BLE 继电器动作（relay:on_1 / relay_off_2 / relay_pulse_3 / relay_toggle_1）。

        注意：relay 动作本身不触发 ON_SUCCESS 反馈（开关继电器本身就是可见结果，
        且避免 relay 动作 → ON_SUCCESS 反馈 → 再发继电器帧的链式递归）。
        """
        relay = get_relay_controller(self.config)
        if relay is None:
            return  # ble_relay.enabled=False

        if not relay.is_connected:
            print(f"[Executor] BLE 继电器未连接，忽略动作 relay:{verb}_{channel}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, f"relay:{verb}_{channel}")
            return

        print(f"[Executor] 继电器动作: 通道{channel} {verb}")
        if verb == "on":
            relay.set_channel(channel, True)
        elif verb == "off":
            relay.set_channel(channel, False)
        elif verb == "toggle":
            current = relay.get_status().get(channel, False)
            relay.set_channel(channel, not current)
        elif verb == "pulse":
            relay.pulse_channel(channel, 500)

    def _activate_tool_window(self):
        """激活映射工具的窗口（如 Trae），使用 ctypes 避免线程问题"""
        try:
            import ctypes
            from ctypes import wintypes
            import time as _time

            tool = self.config.current_tool or "trae"
            title_keywords = {
                "trae": ["trae"],
                "cursor": ["cursor"],
                "vscode": ["visual studio code"],
            }
            keywords = title_keywords.get(tool, [tool])

            user32 = ctypes.windll.user32

            # 枚举窗口找目标
            found_hwnd = ctypes.c_void_p(0)

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def _enum_callback(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if any(kw in title for kw in keywords):
                    found_hwnd.value = hwnd
                    return False
                return True

            user32.EnumWindows(_enum_callback, 0)

            if found_hwnd.value:
                hwnd = found_hwnd.value

                # 已是前台窗口则直接返回：Alt 键模拟会触发 Electron 应用
                # 的菜单栏聚焦，导致聊天输入框失焦（光标消失）
                user32.GetForegroundWindow.restype = wintypes.HWND
                if user32.GetForegroundWindow() == hwnd:
                    return True

                # 只在窗口最小化时才恢复（不影响最大化的窗口）
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE

                # Windows 前台锁定：后台进程直接 SetForegroundWindow 会被系统
                # 拒绝（API 不报错但窗口不切换）。先模拟 Alt 键按下/释放，
                # 让系统认为存在用户输入，本进程即获得设置前台窗口的权限
                user32.keybd_event(0x12, 0, 0, 0)   # Alt down
                _time.sleep(0.05)
                user32.SetForegroundWindow(hwnd)
                user32.keybd_event(0x12, 0, 2, 0)   # Alt up (KEYEVENTF_KEYUP)
                _time.sleep(0.15)

                user32.GetForegroundWindow.restype = wintypes.HWND
                if user32.GetForegroundWindow() == hwnd:
                    _time.sleep(0.3)
                    print(f"[Executor] 已激活 {tool} 窗口")
                    return True

                # 备选：AttachThreadInput 附加到当前前台线程共享输入状态后再切换
                try:
                    kernel32 = ctypes.windll.kernel32
                    fg_tid = user32.GetWindowThreadProcessId(
                        user32.GetForegroundWindow(), None)
                    cur_tid = kernel32.GetCurrentThreadId()
                    user32.AttachThreadInput(cur_tid, fg_tid, True)
                    user32.SetForegroundWindow(hwnd)
                    user32.AttachThreadInput(cur_tid, fg_tid, False)
                except Exception:
                    pass
                _time.sleep(0.3)

                if user32.GetForegroundWindow() == hwnd:
                    print(f"[Executor] 已激活 {tool} 窗口")
                    return True
                print(f"[Executor] {tool} 窗口激活被系统拒绝（前台锁定），按键可能发到错误窗口")
                return False
            else:
                print(f"[Executor] 未找到 {tool} 窗口")
                return False
        except Exception as e:
            print(f"[Executor] 激活窗口失败: {e}")
            return False

    def _record_and_process(self):
        """
        录音并处理：激活工具窗口 → 录音 → 语音识别 → (大模型 or 直接粘贴)
        """
        _recording_ok = False  # 标记本次录音是否成功
        try:
            # 先激活工具窗口（Trae 等），确保粘贴时目标正确
            self._activate_tool_window()

            try:
                import sounddevice as sd
                import numpy as np
            except ImportError:
                print("[Executor] 语音依赖未安装")
                self.feedback.trigger(FeedbackTiming.ON_ERROR, "voice_input")
                return

            # VAD 智能录音：说完话 1.2 秒后自动停止（最长 10 秒）
            SAMPLE_RATE = 16000
            CHUNK = int(SAMPLE_RATE * 0.1)  # 100ms 一帧
            SILENCE_THRESHOLD = 150          # RMS 低于此值视为静音
            MAX_DURATION = 10
            SILENCE_STOP = 12                # 连续 12 帧静音 (1.2秒) 后停止

            print("[Executor] === 开始录音 ===")

            frames = []
            silence_count = 0
            has_speech = False
            total_frames = int(MAX_DURATION * 10)  # 最多 100 帧

            # 显式查找可用输入设备（防止默认设备失效报 -1 错误）
            input_dev = sd.default.device[0]
            if input_dev is None or input_dev < 0:
                for i, d in enumerate(sd.query_devices()):
                    if d['max_input_channels'] > 0:
                        input_dev = i
                        break

            with sd.InputStream(device=input_dev, samplerate=SAMPLE_RATE, channels=1, dtype='int16',
                                blocksize=CHUNK) as stream:
                for i in range(total_frames):
                    data, overflowed = stream.read(CHUNK)
                    rms = np.sqrt(np.mean(data.astype(np.float64) ** 2))
                    frames.append(data.copy())

                    if rms > SILENCE_THRESHOLD:
                        has_speech = True
                        silence_count = 0
                    else:
                        if has_speech:
                            silence_count += 1

                    # 说完后静音超过阈值 → 停止
                    if has_speech and silence_count >= SILENCE_STOP:
                        print(f"[Executor] 检测到静音，提前停止 ({(i+1)*0.1:.1f}秒)")
                        break

            audio_data = np.concatenate(frames).flatten()
            duration = len(audio_data) / SAMPLE_RATE
            rms = np.sqrt(np.mean(audio_data.astype(np.float64) ** 2))
            print(f"[Executor] 录音完成: {duration:.1f}秒, RMS={rms:.0f}")

            if rms < 1:
                print("[Executor] 未采到声音")
                self.feedback.trigger(FeedbackTiming.ON_ERROR, "voice_input")
                return

            # int16 → float32
            audio_f32 = audio_data.astype(np.float32) / 32768.0

            print("[Executor] 录音结束，识别中...")

            # 使用 FunASR 识别
            text = self._recognize_whisper(audio_f32)

            if not text:
                print("[Executor] 未识别到语音内容")
                self.feedback.trigger(FeedbackTiming.ON_ERROR, "voice_input")
                return

            print(f"[Executor] 语音文本: {text}")
            _recording_ok = True

            # ===== 分支处理 =====
            if self.voice_llm and self.voice_llm.is_ready():
                # 方式 A：Token Plan 已配置 → 大模型处理
                mode = "auto"
                if self._active_skill and self._active_skill_context.get("mode"):
                    mode = self._active_skill_context["mode"]
                self.voice_llm.process_voice_text(text, mode=mode)
            else:
                # 方式 B：Token Plan 未配置 → 直接粘贴识别文本到光标位置
                print("[Executor] Token Plan 未配置，直接粘贴语音文本")
                self.voice_llm._type_text(text)

        except Exception as e:
            print(f"[Executor] 录音/识别错误: {e}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, "voice_input")
        finally:
            # 通知 mascot 录音结果
            if hasattr(self, '_mascot_notify'):
                self._mascot_notify("recording_success" if _recording_ok else "recording_error")
            # 无论成功/失败/异常，都重置录音状态
            self._recording = False

    def _recognize_whisper(self, audio_f32):
        """通过常驻 FunASR 服务识别，返回文本"""
        import tempfile
        import wave

        # 保存为临时 WAV 文件
        tmp_wav = os.path.join(tempfile.gettempdir(), "_vibe_voice.wav")
        audio_int16 = (audio_f32 * 32768.0).astype('int16')
        with wave.open(tmp_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_int16.tobytes())

        duration = len(audio_f32) / 16000

        # 优先用常驻服务
        if self._funasr_proc and self._funasr_proc.poll() is None:
            print(f"[Executor] FunASR 识别中... ({duration:.1f}秒音频)")
            try:
                self._funasr_proc.stdin.write(tmp_wav + "\n")
                self._funasr_proc.stdin.flush()

                # 用线程做超时读取（Windows 不支持 selectors 对管道）
                result_box = [None]
                def _read_line():
                    try:
                        result_box[0] = self._funasr_proc.stdout.readline().strip()
                    except Exception:
                        result_box[0] = None

                reader = threading.Thread(target=_read_line, daemon=True)
                reader.start()
                reader.join(timeout=30)

                if reader.is_alive():
                    # 超时，服务卡住
                    print("[Executor] FunASR 服务超时(30秒)，重启服务")
                    self._funasr_proc.terminate()
                    self._funasr_proc = None
                    self._preheat_whisper()  # 自动重启常驻服务
                elif result_box[0]:
                    line = result_box[0]
                    data = json.loads(line)
                    text = data.get("text", "").strip()
                    print(f"[Executor] FunASR 识别结果: '{text}'")
                    return text
                else:
                    print("[Executor] FunASR 服务无响应，重启服务")
                    self._funasr_proc.terminate()
                    self._funasr_proc = None
                    self._preheat_whisper()  # 自动重启常驻服务
            except Exception as e:
                print(f"[Executor] FunASR 服务通信失败: {e}")
                try:
                    if self._funasr_proc:
                        self._funasr_proc.terminate()
                except Exception:
                    pass
                self._funasr_proc = None

        # 回退：启动单次模式
        import subprocess
        print(f"[Executor] FunASR 单次模式识别... ({duration:.1f}秒)")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "core.funasr_worker", tmp_wav],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip().split('\n')[-1])
                text = data.get("text", "").strip()
                print(f"[Executor] FunASR 识别结果: '{text}'")
                return text
            else:
                print(f"[Executor] FunASR 单次模式错误: {result.stderr[:300] if result.stderr else '无输出'}")
                return ""
        except Exception as e:
            print(f"[Executor] FunASR 调用失败: {e}")
            return ""
        finally:
            try:
                os.remove(tmp_wav)
            except Exception:
                pass

        # 如果常驻服务挂了，后台重启
        if self._funasr_proc is None:
            print("[Executor] 后台重启 FunASR 服务...")
            self._preheat_whisper()

    def _fallback_voice_shortcut(self):
        """回退：发送 IDE 快捷键"""
        shortcuts = self.config.get_current_shortcuts()
        keys = shortcuts.get("voice_input", [])
        if keys:
            parsed_keys = [self._get_key(k) for k in keys if self._get_key(k) is not None]
            if parsed_keys:
                for key in parsed_keys:
                    self.keyboard.press(key)
                time.sleep(0.05)
                for key in reversed(parsed_keys):
                    self.keyboard.release(key)

    def _execute_skill(self, action_name: str):
        """
        执行 Skill 动作。由 "skill:<name>" 格式的 action 触发。

        完整流程：
        1. 解析 Skill 名称
        2. 如果当前已有激活的 Skill，先退出恢复默认
        3. 执行 Skill 的 actions（execute_action → 按快捷键，set_tool → 切换工具）
        4. 应用 Skill 的配置覆盖层（shortcuts/feedback/devices）
        5. 将 Skill 设为激活状态，后续语音输入自动使用其 system_prompt
        """
        skill = self.skill_engine.resolve_skill_action(action_name)
        if not skill:
            print(f"[Executor] Skill 未找到或未启用: {action_name}")
            self.feedback.trigger(FeedbackTiming.ON_ERROR, action_name)
            return

        print(f"[Executor] ===== 激活 Skill: {skill.name} v{skill.version} =====")
        print(f"[Executor] 描述: {skill.description}")
        self.feedback.trigger(FeedbackTiming.ON_RECEIVED, f"skill:{skill.name}")

        # 如果当前已有激活的 Skill，先退出
        if self._active_skill:
            print(f"[Executor] 退出上一个 Skill: {self._active_skill.name}")
            self.deactivate_skill()

        # 解析 actions
        context = self.skill_engine.apply_actions(skill)

        # 1. 执行原生动作（如先按 inline_edit 唤起 IDE 的代码生成）
        for act_name in context.get("execute_actions", []):
            print(f"[Executor] Skill 动作: 执行 '{act_name}'")
            self._execute_raw_action(act_name)

        # 2. 切换工具
        if "tool" in context:
            self.switch_tool(context["tool"])

        # 3. 应用配置覆盖层（shortcuts / feedback / devices）
        self._apply_skill_overrides(skill)

        # 4. 将 Skill 设为激活状态
        self._active_skill = skill
        self._active_skill_context = context
        self.skill_engine.set_active(skill)

        print(f"[Executor] Skill '{skill.name}' 已激活")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, f"skill:{skill.name}")
        # 通知 mascot Skill 激活
        if hasattr(self, '_mascot_notify'):
            self._mascot_notify("skill_activated")

    def _apply_skill_overrides(self, skill):
        """应用 Skill 的配置覆盖层到 config 和 feedback manager"""
        overrides = self.skill_engine.get_overrides(skill)

        if not overrides:
            print(f"[Executor] Skill '{skill.name}' 无配置覆盖层")
            return

        # 应用到 config（会影响 get_current_shortcuts / get_current_feedback）
        self.config.apply_skill_overrides(
            shortcuts=overrides.get("shortcuts"),
            feedback=overrides.get("feedback"),
            devices=overrides.get("devices")
        )

        # 更新 FeedbackManager 的配置
        if "feedback" in overrides:
            new_feedback = self.config.get_current_feedback()
            self.feedback.update_config(new_feedback)
            print(f"[Executor] 反馈配置已更新: {overrides['feedback']}")

        # 设备激活（打印日志，实际设备管理由 device_manager 负责）
        if "devices" in overrides:
            for dev in overrides["devices"]:
                print(f"[Executor] 设备激活: {dev.get('id', 'unknown')} (enabled={dev.get('enabled', True)})")

        if "shortcuts" in overrides:
            print(f"[Executor] 快捷键覆盖已应用: {list(overrides['shortcuts'].keys())}")

    def deactivate_skill(self):
        """退出当前 Skill，恢复所有默认配置"""
        if not self._active_skill:
            return

        skill_name = self._active_skill.name
        print(f"[Executor] ===== 退出 Skill: {skill_name} =====")

        # 恢复默认配置
        self.config.clear_skill_overrides()

        # 恢复默认反馈配置
        self.feedback.update_config(self.config.get_base_feedback())

        # 清除激活状态
        self._active_skill = None
        self._active_skill_context = {}
        self.skill_engine.clear_active()

        print(f"[Executor] Skill '{skill_name}' 已退出，配置已恢复")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, f"skill_exit:{skill_name}")
        # 通知 mascot Skill 退出
        if hasattr(self, '_mascot_notify'):
            self._mascot_notify("skill_deactivated")

    def _execute_raw_action(self, action_name: str):
        """直接执行原生快捷键动作（不检查 skill: 前缀，避免递归）"""
        # relay 动作委托统一入口（使 Skill 的 execute_action 类型可触发继电器）
        relay_parsed = parse_relay_action(action_name)
        if relay_parsed:
            self._execute_relay_action(*relay_parsed)
            return

        shortcuts = self.config.get_current_shortcuts()
        if action_name not in shortcuts:
            print(f"[Executor] Raw action '{action_name}' not found in shortcuts")
            return

        keys_to_press = shortcuts[action_name]
        parsed_keys = [self._get_key(k) for k in keys_to_press if self._get_key(k) is not None]

        if not parsed_keys:
            return

        try:
            for key in parsed_keys:
                self.keyboard.press(key)
            time.sleep(0.05)
            for key in reversed(parsed_keys):
                self.keyboard.release(key)
        except Exception as e:
            print(f"[Executor] Error in raw action '{action_name}': {e}")

    @property
    def active_skill(self) -> Optional[object]:
        """返回当前激活的 Skill"""
        return self._active_skill

    @property
    def active_skill_context(self) -> dict:
        """返回当前激活 Skill 的上下文"""
        return self._active_skill_context

    def clear_active_skill(self):
        """清除当前激活的 Skill（语音使用后调用，不恢复配置）"""
        self._active_skill = None
        self._active_skill_context = {}

    def switch_tool(self, tool_name):
        self.config.current_tool = tool_name
        self.config.save_config()
        print(f"[Executor] 切换工具至: {tool_name}")
        self.feedback.trigger(FeedbackTiming.ON_SUCCESS, "switch_tool", f"已切换至: {tool_name}")
