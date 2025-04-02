from vosk import Model, KaldiRecognizer
import pyaudio
import json
import keyboard

# 加载模型
model = Model('vosk-model-small-cn-0.22')
# 麦克风
microphone = pyaudio.PyAudio()

a2 = microphone.open(
    format=pyaudio.paInt16,  # 16位深度音频设置
    channels=1,  # 声道,单声道
    rate=16000,  # 采样率
    input=True,  # 从麦克风获取数据
    frames_per_buffer=4000  # 每次读取数据块大小
)
# 语音识别器
wavRec = KaldiRecognizer(model, 16000)  # 模型，采样率

print("开始实时识别")
while True:
    # 从麦克风读取数据
    a4 = a2.read(4000)
    if wavRec.AcceptWaveform(a4):
        # 实时输出结果
        result = json.loads(wavRec.Result())['text'].replace(' ', '')
        print(result)
    if keyboard.is_pressed('q'):  # 按 'q' 键退出
        print("退出实时识别")
        break

# 关闭麦克风和pyaudio实例
a2.stop_stream()
a2.close()
microphone.terminate()