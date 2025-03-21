import requests
import json
import re
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    content: str


def get_access_token():
    url = ("https://aip.baidubce.com/oauth/2.0/token"
           "?client_id=jC0epDHTtFr1CyUjwwg1fxrl"
           "&client_secret=Uin2fK6r0MklQheJA9Gxgyk6uJ79f7Rz"
           "&grant_type=client_credentials")

    payload = json.dumps("", ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
    returnjson = response.json()
    access_token = returnjson['access_token']
    return access_token


def chat(content):
    access_token = get_access_token()
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token=" + access_token

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = json.dumps({
        "messages": [{"role": "user", "content": content}]
    })

    response = requests.post(url, headers=headers, data=payload.encode("utf-8"))
    responsejson = response.json()
    responsetext = responsejson['result']
    return responsetext


@app.post("/generate_html")
async def generate_html(request: ChatRequest):
    content = request.content
    text = chat(content)
    pattern = r"```.*?```"
    matches = re.findall(pattern, text, re.DOTALL)

    hf = []
    for match in matches:
        hf.append(match.strip())

    if hf:
        cleaned_code = hf[0].replace("```html", "").replace("```", "")
        try:
            with open('output.html', 'w', encoding='utf-8') as file:
                file.write(cleaned_code)
            return PlainTextResponse("HTML 文件已成功生成。")
        except Exception as e:
            return PlainTextResponse(f"生成 HTML 文件时出错: {str(e)}")
    else:
        return PlainTextResponse("未找到代码块。")