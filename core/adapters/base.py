"""
适配器基类 / Base Adapter

所有外设适配器必须继承此类并实现 start/stop 方法。
All device adapters must inherit this class and implement start/stop methods.
"""

import threading
import abc
from typing import Callable, Optional
from ..event import Event


class BaseAdapter(abc.ABC):
    """
    外设适配器基类
    Base class for all device adapters

    子类需要实现：
    Subclasses must implement:
    - start() — 启动监听
    - stop() — 停止监听
    """

    def __init__(self, device_id: str, config: dict, on_event: Callable[[Event], None]):
        """
        Args:
            device_id: 设备唯一标识 / Unique device identifier
            config: 该外设的配置字典 / Device-specific configuration dict
            on_event: 事件回调函数 / Event callback function
        """
        self.device_id = device_id
        self.config = config
        self.on_event = on_event
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        """启动适配器（在独立线程中运行）"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[{self.__class__.__name__}] Started / 已启动: {self.device_id}")

    def stop(self):
        """停止适配器"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        print(f"[{self.__class__.__name__}] Stopped / 已停止: {self.device_id}")

    @abc.abstractmethod
    def _run(self):
        """
        子类实现：实际监听逻辑
        Subclass implementation: actual listening logic

        注意：此方法在独立线程中运行，需要通过检查 self._running 来判断是否退出。
        Note: This runs in a separate thread. Check self._running for exit condition.
        """
        pass

    def _emit(self, event: Event):
        """上报事件到管理器 / Report event to manager"""
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                print(f"[{self.__class__.__name__}] Event callback error: {e}")
