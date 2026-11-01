import os
import winsound
from PyQt5.QtWidgets import QMainWindow, QLabel, QSystemTrayIcon, QMenu, QAction, qApp
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QMovie, QIcon, QPixmap
from core.config import VibeTool
from core.settings_ui import SettingsDialog

class PetSignals(QObject):
    action_triggered = pyqtSignal(str)
    state_changed = pyqtSignal(str)  # 新增状态切换信号 (idle, working, done)

class DesktopPet(QMainWindow):
    def __init__(self, config, executor, listener):
        super().__init__()
        self.config = config
        self.executor = executor
        self.listener = listener
        self.movie = None
        self.detector = None  # 由 main.py 注入
        
        # 信号用于在监听到鼠标按键时跨线程更新 UI
        # Signals for cross-thread UI updates when mouse buttons are pressed
        self.signals = PetSignals()
        self.signals.action_triggered.connect(self.play_action_animation)
        self.signals.state_changed.connect(self.change_state)
        
        # 定时器用于恢复待机动画
        # Timer to restore idle animation
        self.reset_timer = QTimer(self)
        self.reset_timer.timeout.connect(self.play_idle_animation)
        self.reset_timer.setSingleShot(True)
        
        # 记录当前状态
        self.current_state = "idle"
        
        self.init_ui()
        self.init_tray()
        
    def init_ui(self):
        # 设置无边框和永远置顶 / Set frameless and always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # 设置背景透明 / Set transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.label = QLabel(self)
        self.label.setScaledContents(True)  # 让自定义静态图随窗口缩放
        self.setCentralWidget(self.label)
        
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
        
        self.play_idle_animation()
        self.resize(100, 100)
        self.show()

    def play_idle_animation(self):
        self.current_state = "idle"
        self.reset_timer.stop()
        custom = os.path.join(self.assets_dir, 'custom_idle.png')
        if os.path.exists(custom):
            self.label.setPixmap(QPixmap(custom))
        else:
            movie = QMovie(os.path.join(self.assets_dir, 'idle.gif'))
            self.label.setMovie(movie)
            movie.start()

    def change_state(self, state_name):
        self.current_state = state_name
        self.reset_timer.stop()
        
        if state_name == "working":
            # 播放持续生成的动画
            gif_path = os.path.join(self.assets_dir, 'working.gif')
            movie = QMovie(gif_path)
            self.label.setMovie(movie)
            movie.start()
        elif state_name == "done":
            # 播放完成动画（音效由 executor 的 _notify_trae_done 单独处理）
            gif_path = os.path.join(self.assets_dir, 'done.gif')
            movie = QMovie(gif_path)
            self.label.setMovie(movie)
            movie.start()
            
            # 3秒后恢复待机
            self.reset_timer.start(3000)
        elif state_name == "idle":
            self.play_idle_animation()

    def play_action_animation(self, action_name):
        # 兼容旧逻辑，如果是触发生成代码，直接进入 working 状态
        if "inline_edit" in action_name:
            self.change_state("working")
            return
            
        # 其他动作 (如 toggle_chat, accept_diff)
        gif_path = os.path.join(self.assets_dir, 'action.gif')
        if "accept" in action_name:
            gif_path = os.path.join(self.assets_dir, 'accept.gif')
            
        movie = QMovie(gif_path)
        self.label.setMovie(movie)
        movie.start()
        
        # 如果不是正在 working 状态，才恢复 idle
        if self.current_state != "working":
            self.reset_timer.start(2000)

    # 拖拽窗口和双击设置的实现 / Implementation of draggable window and double-click settings
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 打开设置面板 / Open settings panel
            self.settings_dialog = SettingsDialog(self.config, self)
            self.settings_dialog.show()
            event.accept()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(self.assets_dir, 'icon.png')))
        
        tray_menu = QMenu()
        
        # 添加工具切换菜单 / Add tool switching menu
        self.tool_actions = {}
        for tool in VibeTool:
            tool_name = tool.value
            action = QAction(tool_name.capitalize(), self, checkable=True)
            if tool_name == self.config.current_tool:
                action.setChecked(True)
            action.triggered.connect(lambda checked, t=tool_name: self.switch_tool(t))
            tray_menu.addAction(action)
            self.tool_actions[tool_name] = action
            
        tray_menu.addSeparator()
        
        quit_action = QAction("Exit / 退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def switch_tool(self, tool_name):
        self.executor.switch_tool(tool_name)
        # 重置完成检测器状态，避免旧工具的 IO 基线干扰
        if self.detector:
            self.detector.reset_state()
        # 更新菜单选中状态
        for t_name, action in self.tool_actions.items():
            action.setChecked(t_name == tool_name)

    def quit_app(self):
        self.listener.stop()
        self.tray_icon.hide()
        qApp.quit()
