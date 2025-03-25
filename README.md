# 文心大模型 HTML 代码生成服务

这是一个使用 FastAPI 构建的 Web 服务，用于调用百度文心大模型根据用户输入生成 HTML 代码，并将生成的代码保存到 `output.html` 文件中。

## 功能概述
- 用户通过向 `/generate_html` 接口发送 POST 请求，携带需要生成 HTML 代码的描述信息。
- 服务会调用百度文心大模型获取生成的代码，并从中提取 HTML 代码块。
- 最后将提取的 HTML 代码保存到 `output.html` 文件中。

## 安装依赖
在项目根目录下执行以下命令安装所需依赖：pip install -r requirements.txt
## 配置信息
在代码中需要配置百度 API 的客户端 ID 和客户端密钥：# 在 get_access_token 函数中
url = ("https://aip.baidubce.com/oauth/2.0/token"
       "?client_id=jC0epDHTtFr1CyUjwwg1fxrl"  # 替换为你的客户端 ID
       "&client_secret=Uin2fK6r0MklQheJA9Gxgyk6uJ79f7Rz"  # 替换为你的客户端密钥
       "&grant_type=client_credentials")
## 运行服务
在项目根目录下执行以下命令启动 FastAPI 服务：uvicorn qianfan:app --reload

## 使用方法
向 `http://127.0.0.1:8000/generate_html` 发送 POST 请求，请求体为 JSON 格式，包含 `content` 字段，示例如下：{
    "content": "生成一个简单的 HTML 页面，包含一个标题和一个段落。"
}
## 响应结果
- 如果成功生成 HTML 文件，响应为 `HTML 文件已成功生成。`
- 如果调用文心大模型失败，响应为相应的错误信息。
- 如果未找到 HTML 代码块，响应为 `未找到 HTML 代码块。`    
