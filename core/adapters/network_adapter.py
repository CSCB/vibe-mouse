"""
网络/IoT 适配器 / Network & IoT Adapter

支持网络外设、智能家居设备、手机 App 虚拟手柄等。
通过 MQTT、WebSocket、HTTP API 接收远程事件。

依赖：
  pip install paho-mqtt  # MQTT
  pip install websockets # WebSocket

架构：
  外设/网关 -> 网络协议 -> 本地监听端口/Topic -> Event
"""

import json
import time
import importlib
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class NetworkAdapter(BaseAdapter):
    """
    网络/IoT 适配器
    支持 MQTT、WebSocket、HTTP 三种接收模式。
    """

    def _run(self):
        """根据配置选择协议启动"""
        protocol = self.config.get("protocol", "mqtt")  # "mqtt" / "websocket" / "http"

        if protocol == "mqtt":
            self._run_mqtt()
        elif protocol == "websocket":
            self._run_websocket()
        elif protocol == "http":
            self._run_http()
        else:
            print(f"[NetworkAdapter] Unknown protocol / 未知协议: {protocol}")

    def _run_mqtt(self):
        """MQTT 订阅模式"""
        try:
            mqtt = importlib.import_module("paho.mqtt.client")
        except ImportError:
            print(f"[NetworkAdapter] paho-mqtt not installed. Run: pip install paho-mqtt")
            return

        broker = self.config.get("broker", "localhost")
        port = self.config.get("port", 1883)
        topic = self.config.get("topic", "vibemouse/input")
        username = self.config.get("username")
        password = self.config.get("password")

        client = mqtt.Client()
        if username:
            client.username_pw_set(username, password)

        def _on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[NetworkAdapter] MQTT connected / 已连接: {broker}:{port}")
                client.subscribe(topic)
                print(f"[NetworkAdapter] MQTT subscribed / 已订阅: {topic}")
            else:
                print(f"[NetworkAdapter] MQTT connect failed / 连接失败: {rc}")

        def _on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
                # 期望格式: {"input_id": "button_a", "value": 1}
                input_id = payload.get("input_id", "unknown")
                value = payload.get("value", 1)
                input_type_str = payload.get("input_type", "button")

                input_type = InputType.BUTTON
                if input_type_str == "axis":
                    input_type = InputType.AXIS
                elif input_type_str == "dial":
                    input_type = InputType.DIAL

                self._emit(Event(
                    device_type=DeviceType.NETWORK,
                    device_id=self.device_id,
                    input_type=input_type,
                    input_id=input_id,
                    value=value,
                    raw_data=payload
                ))
            except Exception as e:
                print(f"[NetworkAdapter] MQTT message parse error: {e}")

        client.on_connect = _on_connect
        client.on_message = _on_message

        try:
            client.connect(broker, port, 60)
            client.loop_start()

            while self._running:
                time.sleep(0.5)

            client.loop_stop()
            client.disconnect()
        except Exception as e:
            print(f"[NetworkAdapter] MQTT error: {e}")

    def _run_websocket(self):
        """WebSocket 服务器模式"""
        try:
            websockets = importlib.import_module("websockets")
            asyncio = importlib.import_module("asyncio")
        except ImportError:
            print(f"[NetworkAdapter] websockets not installed. Run: pip install websockets")
            return

        host = self.config.get("host", "0.0.0.0")
        port = self.config.get("port", 8765)

        async def _handler(websocket, path):
            print(f"[NetworkAdapter] WebSocket client connected / 客户端已连接: {websocket.remote_address}")
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    input_id = payload.get("input_id", "unknown")
                    value = payload.get("value", 1)

                    self._emit(Event(
                        device_type=DeviceType.NETWORK,
                        device_id=self.device_id,
                        input_type=InputType.BUTTON,
                        input_id=input_id,
                        value=value,
                        raw_data=payload
                    ))
                except Exception as e:
                    print(f"[NetworkAdapter] WebSocket message error: {e}")

        async def _server():
            server = await websockets.serve(_handler, host, port)
            print(f"[NetworkAdapter] WebSocket server started / 服务已启动: ws://{host}:{port}")
            while self._running:
                await asyncio.sleep(0.5)
            server.close()
            await server.wait_closed()

        try:
            asyncio.run(_server())
        except Exception as e:
            print(f"[NetworkAdapter] WebSocket error: {e}")

    def _run_http(self):
        """HTTP API 模式（Flask 轻量服务器）"""
        try:
            flask = importlib.import_module("flask")
        except ImportError:
            print(f"[NetworkAdapter] flask not installed. Run: pip install flask")
            return

        host = self.config.get("host", "0.0.0.0")
        port = self.config.get("port", 5000)
        endpoint = self.config.get("endpoint", "/vibemouse/input")

        app = flask.Flask(__name__)

        @app.route(endpoint, methods=["POST"])
        def _handle_input():
            try:
                payload = flask.request.get_json()
                input_id = payload.get("input_id", "unknown")
                value = payload.get("value", 1)

                self._emit(Event(
                    device_type=DeviceType.NETWORK,
                    device_id=self.device_id,
                    input_type=InputType.BUTTON,
                    input_id=input_id,
                    value=value,
                    raw_data=payload
                ))
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}, 400

        print(f"[NetworkAdapter] HTTP server starting / HTTP 服务启动: http://{host}:{port}{endpoint}")
        # 使用非阻塞方式启动
        import threading
        server_thread = threading.Thread(
            target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
            daemon=True
        )
        server_thread.start()

        while self._running:
            time.sleep(0.5)
