import time
import threading
from pynput import keyboard, mouse

class KeyListener:
    """
    全局键盘监听器
    用于激光笔/翻页笔、脚踏键盘等模拟标准键盘的设备。
    log_keys=True 时把所有按键打印到日志（调试阶段用，
    用于确定设备的键值后再配置映射）。
    """

    def __init__(self, config, executor, log_keys=True):
        self.config = config
        self.executor = executor
        self.log_keys = log_keys
        self.listener = None
        self.action_callback = None

    def set_action_callback(self, callback):
        self.action_callback = callback

    def _on_press(self, key):
        try:
            name = key.char
        except AttributeError:
            name = key.name if hasattr(key, "name") else str(key)

        if self.log_keys:
            print(f"[KeyListener] key press: {name}")

        mapping = getattr(self.config, "keyboard_mappings", None) or {}
        action = mapping.get(name)
        if action:
            threading.Thread(
                target=self.executor.execute_action, args=(action,), daemon=True
            ).start()
            if self.action_callback:
                self.action_callback(action)

    def start(self):
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

class MouseListener:
    # 双击检测时间窗口（秒）
    DOUBLE_CLICK_WINDOW = 0.35

    def __init__(self, config, executor):
        self.config = config
        self.executor = executor
        self.listener = None
        self.action_callback = None

        # 中键双击检测状态
        self._middle_click_count = 0
        self._last_middle_press = 0.0
        self._double_click_timer = None

        # pynput mouse.Button 映射为配置文件的字符串
        self.button_map = {
            mouse.Button.left: "left",
            mouse.Button.right: "right",
            mouse.Button.middle: "middle",
            mouse.Button.x1: "button8",
            mouse.Button.x2: "button9"
        }

    def set_action_callback(self, callback):
        self.action_callback = callback

    def on_click(self, x, y, button, pressed):
        if not pressed:
            return

        # 中键：支持双击检测
        if button == mouse.Button.middle:
            mapping = self.config.mouse_mapping
            has_double = "middle_double" in mapping
            has_single = "middle" in mapping

            if has_double:
                # 配置了 middle_double，走双击检测
                self._handle_middle_click(has_single)
                return
            # 未配置 middle_double，走普通单击

        button_name = self.button_map.get(button, str(button))
        action = self.config.get_action_for_button(button_name)

        if action:
            # 使用独立线程执行，避免阻塞鼠标事件流
            threading.Thread(target=self.executor.execute_action, args=(action,)).start()

            if self.action_callback:
                self.action_callback(action)

    def _handle_middle_click(self, has_single_fallback):
        """
        中键双击检测逻辑。
        has_single_fallback: 是否同时配置了 middle（单击），超时后触发单击。
        """
        now = time.time()
        self._middle_click_count += 1

        if self._middle_click_count == 1:
            self._last_middle_press = now
            # 启动超时定时器
            self._double_click_timer = threading.Timer(
                self.DOUBLE_CLICK_WINDOW,
                self._on_middle_timeout,
                args=[has_single_fallback]
            )
            self._double_click_timer.daemon = True
            self._double_click_timer.start()

        elif self._middle_click_count == 2:
            if now - self._last_middle_press <= self.DOUBLE_CLICK_WINDOW:
                # 双击确认！取消超时定时器
                if self._double_click_timer:
                    self._double_click_timer.cancel()
                    self._double_click_timer = None
                self._middle_click_count = 0
                self._trigger_button("middle_double")
            else:
                # 超时，重置为第一次点击
                self._middle_click_count = 1
                self._last_middle_press = now
                self._double_click_timer = threading.Timer(
                    self.DOUBLE_CLICK_WINDOW,
                    self._on_middle_timeout,
                    args=[has_single_fallback]
                )
                self._double_click_timer.daemon = True
                self._double_click_timer.start()

    def _on_middle_timeout(self, has_single_fallback):
        """单击超时：如果有 middle 映射则触发单击，否则丢弃"""
        if self._middle_click_count == 1 and has_single_fallback:
            self._trigger_button("middle")
        self._middle_click_count = 0

    def _trigger_button(self, button_name):
        """查找映射并触发动作"""
        action = self.config.get_action_for_button(button_name)
        if action:
            threading.Thread(target=self.executor.execute_action, args=(action,)).start()
            if self.action_callback:
                self.action_callback(action)

    def on_scroll(self, x, y, dx, dy):
        # 调试：激光笔/翻页笔常用滚轮事件翻页，打印到日志确认事件值
        print(f"[MouseListener] scroll: dx={dx} dy={dy}")

    def start(self):
        print("Starting Vibe Mouse Listener / 启动 Vibe 鼠标监听器...")
        print(f"Current Tool / 当前工具: {self.config.current_tool}")
        self.listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener.start()

    def stop(self):
        if self._double_click_timer:
            self._double_click_timer.cancel()
        if self.listener:
            self.listener.stop()
            print("Vibe Mouse Listener stopped / 停止 Vibe 鼠标监听器.")

    def join(self):
        if self.listener:
            self.listener.join()
