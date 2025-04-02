import os
import json
import time
from prompt import PROMPT
from sparkai.llm.llm import ChatSparkLLM
from sparkai.core.messages import ChatMessage
from volcenginesdkarkruntime import Ark
import requests
from typing import Dict, List

class DialogHistory:
    def __init__(self, max_length=3):
        self.history = []
        self.max_length = max_length

    def add(self, user_input: str, response: str):
        self.history.append({
            "user": user_input,
            "system": response,
            "timestamp": time.time()
        })
        if len(self.history) > self.max_length:
            self.history.pop(0)

    def get_context(self):
        return "\n======\n".join(
            f"用户:{item['user']}\n系统:{item['system']}"
            for item in self.history
        )


history = DialogHistory()
conversation_history_doubao: List[Dict[str, str]] = []
conversation_history_qianfan: List[Dict[str, str]] = []
conversation_history_deepseek: List[Dict[str, str]] = []

def chat_spark(content: str) -> str:
    """完全由Spark大模型识别需要操作的设备"""
    spark = ChatSparkLLM(
        spark_api_url='wss://spark-api.xf-yun.com/v1.1/chat',
        spark_app_id='54f0b31e',
        spark_api_key=os.environ.get("SPARK_API_KEY"),
        spark_api_secret=os.environ.get("SPARK_SECRET_KEY"),
        spark_llm_domain='lite',
        streaming=False,
    )

    messages = [ChatMessage(role="user", content=content)]
    response = spark.generate([messages]).generations[0][0].message.content
    return response.strip()

def get_access_token_qianfan() -> str:
    """获取百度千帆API的访问令牌"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "client_id": os.environ.get("QIANFAN_API_KEY"),
        "client_secret": os.environ.get("QIANFAN_SECRET_KEY"),
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    return response.json()['access_token']

def chat_qianfan(content: str) -> str:
    """与百度千帆AI聊天并获取响应"""
    conversation_history_qianfan.append({"role": "user", "content": content})

    payload = json.dumps({
        "messages": conversation_history_qianfan,
        "temperature": 0.5
    })

    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={get_access_token_qianfan()}"
    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=payload)
    return response.json()['result']

def chat_doubao(content: str) -> str:
    """与豆包AI聊天并获取响应"""
    conversation_history_doubao.append({"role": "user", "content": content})

    client = Ark(
        # 此为默认路径，您可根据业务所在地域进行配置
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
        api_key=os.environ.get("ARK_API_KEY"),
    )

    completion = client.chat.completions.create(
        # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
        model="ep-20250329165324-l8vxt",
        messages=[
            {"role": "system", "content": "你是前端UI生成师."},
            {"role": "user", "content": f"{content}"},
        ],
        extra_headers={'x-is-encrypted': 'true'},
    )
    return completion.choices[0].message.content

def chat_deepseek(self, content: str) -> str:
    """与豆包AI聊天并获取响应"""
    self.conversation_history_deepseek.append({"role": "user", "content": content})

    client = Ark(
        # 此为默认路径，您可根据业务所在地域进行配置
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
        api_key=os.environ.get("DS_API_KEY"),
    )

    completion = client.chat.completions.create(
        # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
        model="ep-20250329165324-l8vxt",
        messages=[
            {"role": "system", "content": "你是前端UI生成师."},
            {"role": "user", "content": f"{content}"},
        ],
        extra_headers={'x-is-encrypted': 'true'},
    )
    return completion.choices[0].message.content

def get_device(user_input: str) -> str:
    prompt = PROMPT.format(
        user_input=user_input,
        history=history.get_context()
    )

    response = chat_qianfan(prompt)
    return response


# 测试示例
if __name__ == "__main__":
    while True:
        user_input = input("用户输入（输入退出来结束）: ")
        if user_input.lower() in ("退出", "exit"):
            break

        device = get_device(user_input)
        print(f"需要操作的设备: {device}")

        history.add(user_input, device)

