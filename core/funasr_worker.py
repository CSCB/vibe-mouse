"""
FunASR 语音识别常驻服务
启动后加载模型一次，通过文件通信，避免管道缓冲死锁。

协议:
  输入: 监听 input 目录下的 .task 文件
  输出: 写入对应的 .result 文件
  退出: input/quit.signal 文件

也可命令行单次模式: python funasr_worker.py <audio_file.wav>
"""
import sys
import os
import json
import re
import time
import tempfile


def recognize(model, audio_path):
    """识别单个音频文件"""
    try:
        result = model.generate(
            input=audio_path,
            cache={},
            language="zh",
            use_itn=True,
            batch_size_s=60,
        )
        text = result[0]["text"] if result else ""
        # 清理前缀标签: <|zh|><|NEUTRAL|><|Speech|><|withitn|>实际文本
        text = re.sub(r'<\|[^|]+\|>', '', text).strip()
        return text
    except Exception as e:
        sys.stderr.write(f"[Worker] 识别异常: {e}\n")
        return None


def main():
    # 单次模式
    if len(sys.argv) >= 2:
        audio_path = sys.argv[1]
        if not os.path.exists(audio_path):
            print(json.dumps({"error": f"文件不存在: {audio_path}"}, ensure_ascii=False))
            return

        from funasr import AutoModel
        model = AutoModel(
            model="iic/SenseVoiceSmall",
            trust_remote_code=True,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="cpu",
        )
        text = recognize(model, audio_path)
        if text is not None:
            print(json.dumps({"text": text}, ensure_ascii=False))
        else:
            print(json.dumps({"error": "识别失败"}, ensure_ascii=False))
        return

    # 常驻服务模式 - 先加载模型，再发就绪信号
    from funasr import AutoModel
    model = AutoModel(
        model="iic/SenseVoiceSmall",
        trust_remote_code=True,
        vad_model="fsmn-vad",
        vad_kwargs={"max_single_segment_time": 30000},
        device="cpu",
    )

    sys.stdout.write(json.dumps({"status": "ready"}, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    # 用 readline 循环，不写 stderr
    while True:
        try:
            line = sys.stdin.readline()
        except Exception:
            break

        if not line:
            break  # EOF

        line = line.strip()
        if not line:
            continue
        if line == "quit":
            break

        audio_path = line
        if not os.path.exists(audio_path):
            sys.stdout.write(json.dumps({"error": f"文件不存在: {audio_path}"}, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        text = recognize(model, audio_path)

        if text is not None:
            sys.stdout.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(json.dumps({"error": "识别失败"}, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
