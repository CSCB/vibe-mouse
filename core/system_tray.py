import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item
from core.config import VibeTool

class SystemTray:
    def __init__(self, config, executor, device_manager, on_exit_callback):
        self.config = config
        self.executor = executor
        self.device_manager = device_manager
        self.on_exit_callback = on_exit_callback
        self.icon = None

    def create_image(self):
        # 创建一个简单的图标 (蓝底白字 V)
        # Create a simple icon (V with blue background and white text)
        width = 64
        height = 64
        color1 = (41, 128, 185) # 蓝色 / Blue
        color2 = (255, 255, 255) # 白色 / White
        
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        # 简单画一个 V
        # Draw a simple V
        dc.line([(16, 16), (32, 48), (48, 16)], fill=color2, width=8)
        
        return image

    def set_tool(self, tool_name):
        def _set(icon, item):
            self.executor.switch_tool(tool_name)
            # 重新生成菜单以更新选中状态
            # Regenerate the menu to update the checked status
            icon.menu = self.create_menu()
        return _set

    def is_checked(self, tool_name):
        def _checked(item):
            return self.config.current_tool == tool_name
        return _checked

    def create_menu(self):
        # 动态生成工具列表菜单
        # Dynamically generate the tool list menu
        tool_items = []
        for tool in VibeTool:
            tool_name = tool.value
            tool_items.append(
                item(
                    tool_name.capitalize(),
                    self.set_tool(tool_name),
                    checked=self.is_checked(tool_name),
                    radio=True
                )
            )
            
        return pystray.Menu(
            item('Vibe Mouse', None, enabled=False),
            pystray.Menu.SEPARATOR,
            *tool_items,
            pystray.Menu.SEPARATOR,
            item('Exit / 退出', self.exit_app)
        )

    def exit_app(self, icon, item):
        self.device_manager.stop_all()
        icon.stop()
        if self.on_exit_callback:
            self.on_exit_callback()

    def run(self):
        self.icon = pystray.Icon(
            "VibeMouse",
            self.create_image(),
            "Vibe Mouse",
            menu=self.create_menu()
        )
        self.icon.run()
