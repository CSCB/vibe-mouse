"""
语音输入适配器 / Voice Input Adapter

支持语音唤醒词和语音命令触发动作。
通过麦克风实时监听，识别到关键词后触发对应 Event。

支持两种模式：
A. 唤醒词模式 (Wake Word) — 使用 Porcupine 本地离线唤醒词检测，零延迟
B. 语音命令模式 (Voice Command) — 使用 SpeechRecognition 在线/离线语音识别

依赖：
  唤醒词模式: pip install pvporcupine
  命令模式: pip install SpeechRecognition pyaudio

用法示例 (config.json):
{
    "id": "voice_mic",
    "type": "voice",
    "config": {
        "mode": "wake_word",
        "keywords": {
            "accept": "accept",      // Porcupine 内置关键词
            "reject": "reject",
            "generate": "generate"
        },
        "access_key": "YOUR_PORCUPINE_KEY"
    },
    "enabled": true
}

或者命令模式:
{
    "id": "voice_cmd",
    "type": "voice",
    "config": {
        "mode": "command",
        "language": "zh-CN",
        "keyword_actions": {
            "接受": "accept_diff",
            "拒绝": "reject_diff",
            "生成": "inline_edit",
            "面板": "toggle_chat"
        },
        "command_phrases": {
            "accept_diff": ["接受", "采纳", "同意", "yes", "accept", "ok"],
            "reject_diff": ["拒绝", "取消", "不要", "no", "reject", "cancel"],
            "inline_edit": ["生成", "编辑", "写入", "generate", "edit", "write"],
            "toggle_chat": ["面板", "聊天", "对话", "chat", "panel", "talk"]
        }
    },
    "enabled": true
}
"""

import time
import importlib
import threading
from .base import BaseAdapter
from ..event import Event, DeviceType, InputType


class VoiceAdapter(BaseAdapter):
    """
    语音输入适配器
    支持离线唤醒词 (Porcupine) 和语音命令 (SpeechRecognition) 两种模式。
    """

    def _run(self):
        mode = self.config.get("mode", "command")
        if mode == "wake_word":
            self._run_wake_word()
        else:
            self._run_command()

    def _run_wake_word(self):
        """Porcupine 离线唤醒词模式"""
        try:
            pvporcupine = importlib.import_module("pvporcupine")
        except ImportError:
            print("[VoiceAdapter] pvporcupine not installed. Run: pip install pvporcupine")
            print("[VoiceAdapter] Fallback to command mode / 回退到命令模式")
            self._run_command()
            return

        access_key = self.config.get("access_key", "")
        if not access_key:
            print("[VoiceAdapter] Porcupine access_key required / 需要配置 access_key")
            print("[VoiceAdapter] Get free key at: https://console.picovoice.ai/")
            return

        # 解析关键词配置
        keywords_config = self.config.get("keywords", {})
        # Porcupine 内置关键词列表 (常用)
        builtin_keywords = ["picovoice", "porcupine", "terminator", "grasshopper",
                            "grapefruit", "americano", "bumblebee", "blueberry",
                            "pico clock", "hey siri", "hey google", "alexa",
                            "jarvis", "computer"]

        # 构建 Porcupine 关键词列表
        keyword_paths = []
        keyword_map = []  # index -> action
        for action, keyword in keywords_config.items():
            kw_lower = keyword.lower()
            if kw_lower in builtin_keywords:
                keyword_paths.append(kw_lower)
            else:
                # 自定义关键词需要 .ppn 文件路径
                keyword_paths.append(keyword)
            keyword_map.append(action)

        if not keyword_paths:
            print("[VoiceAdapter] No keywords configured / 未配置关键词")
            return

        try:
            porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=keyword_paths
            )
        except Exception as e:
            print(f"[VoiceAdapter] Porcupine init error: {e}")
            return

        print(f"[VoiceAdapter] Wake word mode started / 唤醒词模式已启动")
        print(f"[VoiceAdapter] Listening for: {list(keywords_config.values())}")

        # 音频输入
        try:
            pyaudio_module = importlib.import_module("pyaudio")
        except ImportError:
            print("[VoiceAdapter] pyaudio not installed. Run: pip install pyaudio")
            porcupine.delete()
            return

        pa = pyaudio_module.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio_module.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        try:
            while self._running:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm_data = pcm  # bytes already

                import struct
                # 转为 int16 numpy-like array
                samples = struct.unpack(f"<{porcupine.frame_length}h", pcm_data)

                result = porcupine.process(samples)
                if result >= 0 and result < len(keyword_map):
                    action = keyword_map[result]
                    keyword = list(keywords_config.values())[result]
                    self._emit(Event(
                        device_type=DeviceType.VOICE,
                        device_id=self.device_id,
                        input_type=InputType.VOICE,
                        input_id=action,
                        value=1,
                        raw_data={"keyword": keyword, "mode": "wake_word"}
                    ))
                    print(f"[VoiceAdapter] Wake word detected / 检测到唤醒词: {keyword} -> {action}")
        except Exception as e:
            print(f"[VoiceAdapter] Wake word error: {e}")
        finally:
            audio_stream.stop_stream()
            audio_stream.close()
            pa.terminate()
            porcupine.delete()

    def _run_command(self):
        """SpeechRecognition 语音命令模式"""
        try:
            sr = importlib.import_module("speech_recognition")
        except ImportError:
            print("[VoiceAdapter] SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")
            return

        recognizer = sr.Recognizer()
        language = self.config.get("language", "zh-CN")
        command_phrases = self.config.get("command_phrases", {})
        keyword_actions = self.config.get("keyword_actions", {})

        # 如果只配了 keyword_actions，自动生成 command_phrases
        if not command_phrases and keyword_actions:
            for action, keywords in keyword_actions.items():
                if isinstance(keywords, str):
                    keywords = [keywords]
                command_phrases[action] = keywords

        # 合并默认命令短语
        default_phrases = {
            "accept_diff": ["接受", "采纳", "同意", "yes", "accept", "ok", "确认"],
            "reject_diff": ["拒绝", "取消", "不要", "no", "reject", "cancel"],
            "inline_edit": ["生成", "编辑", "写入", "generate", "edit", "write"],
            "toggle_chat": ["面板", "聊天", "对话", "chat", "panel", "talk"],
        }
        for action, phrases in default_phrases.items():
            if action not in command_phrases:
                command_phrases[action] = phrases

        print(f"[VoiceAdapter] Command mode started / 命令模式已启动")
        print(f"[VoiceAdapter] Language: {language}")

        # 列出所有监听短语
        all_phrases = set()
        for phrases in command_phrases.values():
            all_phrases.update([p.lower() for p in phrases])
        print(f"[VoiceAdapter] Listening for phrases / 监听短语: {', '.join(list(all_phrases)[:10])}...")

        try:
            mic_module = importlib.import_module("speech_recognition")
            mic = mic_module.Microphone()
        except Exception as e:
            print(f"[VoiceAdapter] Microphone init error: {e}")
            return

        # 在后台线程中调整环境噪音
        def _adjust_noise():
            try:
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("[VoiceAdapter] Noise calibration done / 噪音校准完成")
            except Exception as e:
                print(f"[VoiceAdapter] Noise calibration error: {e}")

        noise_thread = threading.Thread(target=_adjust_noise, daemon=True)
        noise_thread.start()
        noise_thread.join(timeout=3)

        # 持续监听循环
        while self._running:
            try:
                with mic as source:
                    audio = recognizer.listen(source, timeout=2, phrase_time_limit=5)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                if self._running:
                    print(f"[VoiceAdapter] Mic read error: {e}")
                    time.sleep(1)
                continue

            # 识别语音
            text = ""
            for engine in ["sphinx", "google"]:
                try:
                    if engine == "sphinx":
                        # 离线识别 (需要 pocketsphinx)
                        text = recognizer.recognize_sphinx(audio, language=language).lower()
                    else:
                        # 在线识别 (Google)
                        text = recognizer.recognize_google(audio, language=language).lower()
                    break
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    if engine == "sphinx":
                        continue
                    print(f"[VoiceAdapter] Google API error: {e}")
                    continue
                except ImportError:
                    continue

            if not text:
                continue

            print(f"[VoiceAdapter] Heard / 听到: \"{text}\"")

            # 匹配命令
            matched_action = self._match_command(text, command_phrases)
            if matched_action:
                self._emit(Event(
                    device_type=DeviceType.VOICE,
                    device_id=self.device_id,
                    input_type=InputType.VOICE,
                    input_id=matched_action,
                    value=1,
                    raw_data={"text": text, "mode": "command"}
                ))
                print(f"[VoiceAdapter] Matched / 匹配: \"{text}\" -> {matched_action}")

    def _match_command(self, text: str, command_phrases: dict) -> str:
        """
        将识别文本与命令短语匹配。
        支持部分匹配（文本中包含关键词即触发）。
        """
        text_lower = text.lower().strip()

        # 精确匹配
        for action, phrases in command_phrases.items():
            for phrase in phrases:
                if phrase.lower() == text_lower:
                    return action

        # 部分匹配（文本包含关键词）
        for action, phrases in command_phrases.items():
            for phrase in phrases:
                if phrase.lower() in text_lower:
                    return action

        return ""