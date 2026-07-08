import threading
from pynput import mouse

class MouseListener:
    def __init__(self, config, executor):
        self.config = config
        self.executor = executor
        self.listener = None
        
        # pynput mouse.Button 映射为配置文件的字符串
        # Mapping pynput mouse.Button to config string
        self.button_map = {
            mouse.Button.left: "left",
            mouse.Button.right: "right",
            mouse.Button.middle: "middle",
            mouse.Button.x1: "button8", # 通常对应侧键 1 / Usually corresponds to side button 1
            mouse.Button.x2: "button9"  # 通常对应侧键 2 / Usually corresponds to side button 2
        }

    def on_click(self, x, y, button, pressed):
        if pressed:
            button_name = self.button_map.get(button, str(button))
            action = self.config.get_action_for_button(button_name)
            
            if action:
                # print(f"Mouse button '{button_name}' pressed. Triggering action: {action}")
                # 使用独立线程执行，避免阻塞鼠标事件流
                # Execute in a separate thread to avoid blocking the mouse event stream
                threading.Thread(target=self.executor.execute_action, args=(action,)).start()

    def start(self):
        print("Starting Vibe Mouse Listener / 启动 Vibe 鼠标监听器...")
        print(f"Current Tool / 当前工具: {self.config.current_tool}")
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            print("Vibe Mouse Listener stopped / 停止 Vibe 鼠标监听器.")

    def join(self):
        if self.listener:
            self.listener.join()
