import re

import requests
import json
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup

app = FastAPI()

class ChatRequest(BaseModel):
    content: str

# 存储对话历史和HTML片段
conversation_history = []
html_parts = {}  # 存储解析后的HTML部分

# 增强版关键词映射
KEYWORD_MAPPING = {
    '头部': 'head'，
    '页面标题': 'title'，
    '内容标题': 'h1'，  # 默认映射到h1
    '主标题': 'h1'，
    '二级标题': 'h2'，
    '三级标题': 'h3'，
    '主体': 'body'，
    '导航栏': 'nav'，
    '导航': 'nav'，
    '菜单': 'nav'，
    '页脚': 'footer'，
    '底部': 'footer'，
    '脚本': 'scripts'，
    '样式': 'styles'，
    '段落': 'paragraphs'，
    '链接': 'links'，
    '图片': 'images'，
    '产品标题': '.product h3'，  # 特定类下的标题
    '全部': '全部'
}

def parse_html(html_content):
    """解析HTML并提取关键部分（增强版）"""
    soup = BeautifulSoup(html_content, 'html.parser')

    parts = {
        'head': str(soup.head) if soup.head else ""，
        'title': soup.title。string if soup.title else "无页面标题"，
        'h1': [str(h) for h in soup.find_all('h1')]，
        'h2': [str(h) for h in soup.find_all('h2')]，
        'h3': [str(h) for h in soup.find_all('h3')]，
        'nav': [str(nav) for nav in soup.find_all('nav')]，
        'footer': str(soup.footer) if soup.footer else ""，
        'body': str(soup.body) if soup.body else ""，
        'scripts': [str(script) for script in soup.find_all('script')]，
        'styles': [str(style) for style in soup.find_all('style')]，
        'paragraphs': [str(p) for p in soup.find_all('p')]，
        'links': [str(a) for a in soup.find_all('a')]，
        'images': [str(img) for img in soup.find_all('img')]，
        '.product h3': [str(h3) for h3 in soup.select('.product h3')]
    }

    # 智能识别导航和页脚
    if not parts['nav']:
        parts['nav'] = [str(div) for div in soup.find_all(class_=['nav'， 'navbar'， 'navigation'])]
    if not parts['footer']:
        footer_div = soup.find(class_=['footer'， 'bottom'])
        if footer_div:
            parts['footer'] = str(footer_div)

    return parts

def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token?client_id=jC0epDHTtFr1CyUjwwg1fxrl&client_secret=Uin2fK6r0MklQheJA9Gxgyk6uJ79f7Rz&grant_type=client_credentials"
    payload = json.dumps("")
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=payload)
    return response.json()['access_token']

def chat(content):
    global conversation_history
    conversation_history.append({"role": "user"， "content": content})

    payload = json.dumps({
        "messages": conversation_history,
        "temperature": 0.5
    })

    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={get_access_token()}"
    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=payload)
    return response.json()['result']

def extract_content_keywords(text, html_content):
    """增强版文本内容关键词提取"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # 获取所有包含文本的元素
    text_elements = []
    for element in soup.find_all(text=True):
        if element.parent。name not in ['script'， 'style'] 和 element.strip():
            text_elements.append({
                'text': element.strip()，
                'element': element.parent，
                'full_text': str(element.parent)
            })

    # 找出用户请求中匹配的文本内容
    matched_texts = []
    for item in text_elements:
        # 检查用户请求是否包含这段文本(部分匹配)
        if item['text'] in text 或 text in item['text']:
            matched_texts.append({
                'text': item['text']，
                'element': item['element'],
                'full_text': item['full_text']
            })

    return matched_texts

def extract_chinese_keywords(text, html_content=None):
    """增强版关键词提取，现在支持文本内容作为关键词"""
    # 首先尝试匹配HTML中的具体文本内容
    if html_content:
        content_keywords = extract_content_keywords(text, html_content)
        if content_keywords:
            return content_keywords

    # 原有逻辑保持不变
    if '全部' in text or '完整' in text or '整个' in text:
        return ['全部']

    # 特殊处理"内容标题"请求
    if '内容标题' in text or ('标题' in text and '内容' in text):
        return ['h1', 'header h1']  # 同时匹配普通h1和header中的h1

    level_mapping = {
        '一级标题': 'h1',
        '二级标题': 'h2',
        '三级标题': 'h3',
        '产品标题': '.product h3'
    }

    for phrase, tag in level_mapping.items():
        if phrase in text:
            return [tag]

    if ('产品' in text and ('标题' in text or '名称' in text)) or '产品标题' in text:
        return ['.product h3']

    found_keywords = []
    for chinese_key, english_key in KEYWORD_MAPPING.items():
        if chinese_key in text:
            found_keywords.append(english_key)

    return found_keywords if found_keywords else ['h1']

# 增强版文本定位
def find_text_positions(html, target_text):
    soup = BeautifulSoup(html, 'html.parser')
    matches = []

    for element in soup.find_all(text=lambda t: target_text in str(t)):
        parent = element.parent
        full_text = str(parent)
        start_pos = html.find(full_text)

        if start_pos != -1:
            matches.append({
                'start': start_pos,
                'end': start_pos + len(full_text),
                'full_text': full_text,
                'element': element
            })

    return matches

#增强版指令解析
def parse_modification_command(cmd):
    # 支持多种指令格式
    patterns = [
        r"将['\"](.*?)['\"]改为['\"](.*?)['\"]",  # 将"x"改为"y"
        r"将(.*?)修改为(.*?)$",  # 将x修改为y
        r"将(.*?)改为(.*?)$",  # 将x改为y
        r"把(.*?)改成(.*?)$"  # 把x改成y
    ]

    for pattern in patterns:
        match = re.search(pattern, cmd)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    # 默认处理（最后兜底）
    if "改为" in cmd:
        parts = cmd.split("改为")
        return parts[0].replace("将", "").strip(), parts[1].strip()
    elif "修改为" in cmd:
        parts = cmd.split("修改为")
        return parts[0].replace("将", "").strip(), parts[1].strip()

    return None, None

def extract_modification_params(request_content):
    """正确解析修改指令，返回 (查找文本, 替换文本)"""
    # 支持多种指令格式
    patterns = [
        r"将['\"](.*?)['\"]改为['\"](.*?)['\"]",  # 将"x"改为"y"
        r"将(.*?)修改为(.*?)$",  # 将x修改为y
        r"将(.*?)改为(.*?)$",  # 将x改为y
        r"把(.*?)改成(.*?)$"  # 把x改成y
    ]

    for pattern in patterns:
        match = re.search(pattern, request_content)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    # 如果都不匹配，尝试简单分割
    if "改为" in request_content:
        parts = request_content.split("改为")
        return parts[0]。replace("将"， "")。strip(), parts[1]。strip()
    elif "修改为" in request_content:
        parts = request_content.split("修改为")
        return parts[0]。replace("将"， "")。strip(), parts[1]。strip()

    return None， None

@app.post("/generate_html")
async def generate_html(request: ChatRequest):
    global html_parts
    #清空历史记录
    conversation_history.clear()
    html_parts.clear()

    content = request.content + "，请返回一个完整的html文件"
    text = chat(content)

    if "```" in text:
        html_code = text.split("```")[1]。strip()
        if html_code.startswith("html"):
            html_code = html_code[4:]。strip()

        # 解析HTML并存储各部分
        html_parts = parse_html(html_code)

        # 保存完整HTML文件
        with open('output.html'， 'w', encoding='utf-8') as f:
            f.write(html_code)

        return PlainTextResponse("HTML文件已生成并解析完成。")
    else:
        return PlainTextResponse("未检测到有效的HTML代码块。")


@app.post("/modify_html_part")
async def modify_html_part(request: ChatRequest):
    global html_parts

    print(f"收到修改请求: {request.content}")  # 调试日志

    try:
        with open('output.html'， 'r', encoding='utf-8') as f:
            current_html = f.read()
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return PlainTextResponse(f"读取HTML文件失败: {str(e)}")

    # 首先尝试解析为"将X改为Y"的文本修改指令
    target_text, new_text = parse_modification_command(request.content)

    if target_text 和 new_text:
        print(f"解析为文本修改指令: 查找'{target_text}' 替换为'{new_text}'")
        # 执行文本内容修改逻辑
        matches = find_text_positions(current_html, target_text)

        if not matches:
            print("尝试模糊匹配...")
            soup = BeautifulSoup(current_html, 'html.parser')
            for element in soup.find_all(text=True):
                if target_text in str(element):
                    parent = element.parent
                    full_text = str(parent)
                    start_pos = current_html.find(full_text)
                    if start_pos != -1:
                        matches.append({
                            'start': start_pos,
                            'end': start_pos + len(full_text)，
                            'full_text': full_text,
                            'element': element,
                            'parent': parent
                        })
                        break

        if not matches:
            # 如果文本匹配失败，回退到HTML部分修改
            print("文本匹配失败，尝试HTML部分修改")
        else:
            print(f"找到{len(matches)}处文本匹配")

            # 构造文本修改提示
            modification_prompt = f"""
            请严格根据以下要求修改HTML内容：
            需要修改的部分（保持外层标签不变）:
            {matches[0]['full_text']}

            修改要求：
            将以下文本：
            "{target_text}"
            替换为：
            "{new_text}"

            重要说明：
            1. 只需返回修改后的完整HTML元素
            2. 必须保持原有的HTML标签结构
            3. 只修改指定文本，不要改动其他内容
            4. 用```html包裹返回内容

            示例：
            ```html
            {matches[0]['parent'].prettify().split('\n')[0].strip()}
            {new_text}
            {matches[0]['parent'].prettify().split('\n')[-1].strip()}
            ```
            """

            print("发送给AI的提示:\n", modification_prompt)

            try:
                modified_part = chat(modification_prompt)
                print("AI返回:\n", modified_part)

                # 处理AI返回结果
                if "```html" in modified_part:
                    new_part = modified_part.split("```html")[1].split("```")[0].strip()
                elif "```" in modified_part:
                    new_part = modified_part.split("```")[1].strip()
                    if new_part.lower().startswith("html"):
                        new_part = new_part[4:].strip()
                else:
                    return PlainTextResponse("AI返回格式不正确")

                # 验证标签是否匹配
                original_tag = matches[0]['parent'].name
                if f"<{original_tag}" not in new_part.lower():
                    return PlainTextResponse(f"错误：AI没有保持原标签结构，期望<{original_tag}>标签")

                # 执行替换
                updated_html = current_html[:matches[0]['start']] + new_part + current_html[matches[0]['end']:]

                # 保存文件
                with open('output.html', 'w', encoding='utf-8') as f:
                    f.write(updated_html)

                html_parts = parse_html(updated_html)
                return PlainTextResponse("文本内容修改成功！")

            except Exception as e:
                print(f"AI处理失败: {str(e)}")

    # HTML部分修改逻辑（文本修改失败或不是文本修改指令时执行）
    print("尝试HTML部分修改逻辑")
    soup = BeautifulSoup(current_html, 'html.parser')
    keywords = extract_chinese_keywords(request.content)

    if "全部" in keywords:
        modification_prompt = f"""
        请根据以下要求修改整个HTML文档：
        修改要求：
        {request.content}

        请返回完整的HTML代码，用```html包裹。
        """
    else:
        elements_to_modify = []
        for keyword in keywords:
            if keyword == 'header h1':
                header = soup.find('header')
                if header:
                    elements_to_modify.extend(header.find_all('h1'))
            elif keyword.startswith('.'):
                elements_to_modify.extend(soup.select(keyword))
            elif keyword in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                main = soup.find('main')
                if main:
                    elements_to_modify.extend(main.find_all(keyword))
                else:
                    elements_to_modify.extend(soup.find_all(keyword))
            elif keyword in html_parts:
                if keyword == 'title':
                    elements_to_modify.append(soup.title)
                elif keyword == 'head':
                    elements_to_modify.append(soup.head)
                elif keyword == 'body':
                    elements_to_modify.append(soup.body)
                elif keyword == 'footer':
                    footer = soup.find('footer') or soup.find(class_=['footer', 'bottom'])
                    if footer:
                        elements_to_modify.append(footer)
                elif keyword == 'nav':
                    nav = soup.find('nav') or soup.find(class_=['nav', 'navbar'])
                    if nav:
                        elements_to_modify.append(nav)

        if not elements_to_modify:
            return PlainTextResponse("未找到与关键词对应的HTML部分。")

        # 构造HTML部分修改提示
        parts_info = []
        for element in elements_to_modify:
            parent = element.find_parent()
            parent_name = parent.name if parent else '根'
            parts_info.append(f"""
            位于{parent_name}中的{element.name}元素:
            {str(element)}
            """)

        parts_text = "\n".join(parts_info)
        modification_prompt = f"""
        请根据以下要求修改HTML部分内容：
        需要修改的元素:
        {parts_text}

        修改要求:
        {request.content}

        重要说明：
        1。 保持元素的基本HTML结构不变
        2。 只需返回修改后的完整HTML代码
        3。 用```html包裹返回内容

        示例：
        ```html
        <h2>修改后的内容</h2>
        ```
        """

    print("发送给AI的提示:\n", modification_prompt)

    try:
        modified_part = chat(modification_prompt)
        print("AI返回:\n", modified_part)

        if "```html" in modified_part:
            new_part = modified_part.split("```html")[1].split("```")[0].strip()
        elif "```" in modified_part:
            new_part = modified_part.split("```")[1].strip()
            if new_part.lower().startswith("html"):
                new_part = new_part[4:].strip()
        else:
            return PlainTextResponse("AI返回格式不正确")

        if "全部" in keywords:
            updated_html = new_part
        else:
            # 精确替换HTML部分
            updated_html = current_html
            for element in elements_to_modify:
                if element and str(element) in updated_html:
                    updated_html = updated_html.replace(str(element), new_part, 1)
                    break

        # 保存文件
        with open('output.html', 'w', encoding='utf-8') as f:
            f.write(updated_html)

        html_parts = parse_html(updated_html)
        return PlainTextResponse("HTML部分修改成功！")

    except Exception as e:
        print(f"AI处理失败: {str(e)}")
        return PlainTextResponse(f"处理请求时出错: {str(e)}")


@app.post("/clear_conversation_history")
async def clear_history():
    global conversation_history, html_parts
    conversation_history = []
    html_parts = {}
    return PlainTextResponse("对话历史和HTML解析结果已清空。")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
