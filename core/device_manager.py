"""
外设管理器 / Device Manager

统一管理所有外设适配器的生命周期：
- 根据配置动态注册/启动适配器
- 接收统一 Event 事件
- 根据 device_mappings 路由到对应的 action
- 调用执行器完成快捷键发送

Replaces the original listener.py with a pluggable multi-device architecture.
"""

import threading
from typing import Dict, List, Optional, Callable
from .event import Event, DeviceType, InputType
from .adapters import ADAPTER_REGISTRY, get_adapter_class
from .adapters.base import BaseAdapter


class DeviceManager:
    """
    外设管理器
    负责注册、启动、停止所有外设适配器，并将事件路由到执行器。
    """

    def __init__(self, config, executor):
        self.config = config
        self.executor = executor
        self.adapters: Dict[str, BaseAdapter] = {}
        self._lock = threading.Lock()

    def register_device(self, device_type: str, device_id: str, device_config: dict):
        """
        注册一个外设
        Register a device

        Args:
            device_type: 外设类型 (如 "mouse", "gamepad", "ir_remote")
            device_id: 设备唯一标识
            device_config: 该设备的配置字典
        """
        adapter_cls = get_adapter_class(device_type)
        if not adapter_cls:
            print(f"[DeviceManager] Unknown device type / 未知外设类型: {device_type}")
            return

        with self._lock:
            if device_id in self.adapters:
                print(f"[DeviceManager] Device already registered / 设备已注册: {device_id}")
                return

            adapter = adapter_cls(
                device_id=device_id,
                config=device_config,
                on_event=self._on_event
            )
            self.adapters[device_id] = adapter
            print(f"[DeviceManager] Registered / 已注册: {device_id} ({device_type})")

    def unregister_device(self, device_id: str):
        """注销并停止一个外设"""
        with self._lock:
            adapter = self.adapters.pop(device_id, None)
            if adapter:
                adapter.stop()
                print(f"[DeviceManager] Unregistered / 已注销: {device_id}")

    def start_all(self):
        """启动所有已注册的外设"""
        print("[DeviceManager] Starting all devices / 启动所有外设...")
        for device_id, adapter in self.adapters.items():
            adapter.start()

    def stop_all(self):
        """停止所有外设"""
        print("[DeviceManager] Stopping all devices / 停止所有外设...")
        for device_id, adapter in list(self.adapters.items()):
            adapter.stop()
        self.adapters.clear()

    def load_from_config(self):
        """
        从配置文件中加载所有设备并注册。
        这是启动时的入口方法。
        """
        devices = self.config.get_devices()
        for device in devices:
            self.register_device(
                device_type=device["type"],
                device_id=device["id"],
                device_config=device.get("config", {})
            )

    def _on_event(self, event: Event):
        """
        统一事件回调
        根据 device_id 查找对应的 input_id -> action 映射，调用执行器。
        特殊处理：语音 LLM 模式的事件直接交给 VoiceLLMBridge。
        """
        # 特殊事件：语音文本 -> 大模型
        if event.input_id == "__voice_text__" and isinstance(event.value, str):
            text = event.value
            if hasattr(self.executor, 'voice_llm'):
                threading.Thread(
                    target=self.executor.voice_llm.process_voice_text,
                    args=(text, "auto"),
                    daemon=True
                ).start()
            return

        # 获取该设备类型的映射配置
        mapping = self.config.get_device_mapping(event.device_id)
        if not mapping:
            return

        action = mapping.get(event.input_id)
        if not action:
            return

        # 调用执行器
        # 使用独立线程执行，避免阻塞事件流
        threading.Thread(
            target=self.executor.execute_action,
            args=(action,),
            daemon=True
        ).start()
