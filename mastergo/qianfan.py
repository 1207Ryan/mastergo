import re
import json
from typing import Dict, List, Optional, Tuple, Any
import requests
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup, Tag

app = FastAPI()

class ChatRequest(BaseModel):
    content: str

class HTMLModifier:
    """处理HTML生成和修改的核心类"""

    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self.html_parts: Dict[str, Any] = {}
        self.keyword_mapping = {
            '头部': 'head',
            '页面标题': 'title',
            '内容标题': 'h1',
            '主标题': 'h1',
            '二级标题': 'h2',
            '三级标题': 'h3',
            '主体': 'body',
            '导航栏': 'nav',
            '导航': 'nav',
            '菜单': 'nav',
            '页脚': 'footer',
            '底部': 'footer',
            '脚本': 'scripts',
            '样式': 'styles',
            '段落': 'paragraphs',
            '链接': 'links',
            '图片': 'images',
            '产品标题': '.product h3',
            '全部': '全部'
        }

    PROMPT_TEMPLATE = """
        请根据以下要求修改HTML内容：
        需要修改的内容:
        {elements}

        修改要求:
        {request}

        重要说明：
        1. 保持元素的基本HTML结构不变
        2. 只需返回修改后的完整HTML代码
        3. 用```html...```包裹返回内容

        示例：
        ```html
        {example}
        ```
        """

    DEFAULT_EXAMPLE = """<div class="modified-example">
      <h2>修改后的内容示例</h2>
      <p>这是一个修改后的HTML示例</p>
    </div>"""

    def clear_history(self):
        """清空对话历史和HTML解析结果"""
        self.conversation_history = []
        self.html_parts = {}

    def get_access_token(self) -> str:
        """获取百度API的访问令牌"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "client_id": "jC0epDHTtFr1CyUjwwg1fxrl",
            "client_secret": "Uin2fK6r0MklQheJA9Gxgyk6uJ79f7Rz",
            "grant_type": "client_credentials"
        }
        response = requests.post(url, params=params)
        return response.json()['access_token']

    def chat(self, content: str) -> str:
        """与AI聊天并获取响应"""
        self.conversation_history.append({"role": "user", "content": content})

        payload = json.dumps({
            "messages": self.conversation_history,
            "temperature": 0.5
        })

        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={self.get_access_token()}"
        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=payload)
        return response.json()['result']

    def parse_html(self, html_content: str) -> Dict[str, Any]:
        """解析HTML并提取关键部分"""
        soup = BeautifulSoup(html_content, 'html.parser')

        parts = {
            'head': str(soup.head) if soup.head else "",
            'title': soup.title.string if soup.title else "无页面标题",
            'h1': [str(h) for h in soup.find_all('h1')],
            'h2': [str(h) for h in soup.find_all('h2')],
            'h3': [str(h) for h in soup.find_all('h3')],
            'nav': [str(nav) for nav in soup.find_all('nav')],
            'footer': str(soup.footer) if soup.footer else "",
            'body': str(soup.body) if soup.body else "",
            'scripts': [str(script) for script in soup.find_all('script')],
            'styles': [str(style) for style in soup.find_all('style')],
            'paragraphs': [str(p) for p in soup.find_all('p')],
            'links': [str(a) for a in soup.find_all('a')],
            'images': [str(img) for img in soup.find_all('img')],
            '.product h3': [str(h3) for h3 in soup.select('.product h3')]
        }

        # 智能识别导航和页脚
        if not parts['nav']:
            parts['nav'] = [str(div) for div in soup.find_all(class_=['nav', 'navbar', 'navigation'])]
        if not parts['footer']:
            footer_div = soup.find(class_=['footer', 'bottom'])
            if footer_div:
                parts['footer'] = str(footer_div)

        return parts

    def extract_content_keywords(self, text: str, html_content: str) -> List[Dict[str, Any]]:
        """从HTML内容中提取与用户输入文本相匹配的关键词及其相关信息"""
        soup = BeautifulSoup(html_content, 'html.parser')
        text_elements = []

        for element in soup.find_all(text=True):
            if element.parent.name not in ['script', 'style'] and element.strip():
                text_elements.append({
                    'text': element.strip(),
                    'element': element.parent,
                    'full_text': str(element.parent)
                })

        matched_texts = []
        for item in text_elements:
            if item['text'] in text or text in item['text']:
                matched_texts.append({
                    'text': item['text'],
                    'element': item['element'],
                    'full_text': item['full_text']
                })

        return matched_texts

    def extract_chinese_keywords(self, text: str, html_content: Optional[str] = None) -> List[str]:
        """提取中文关键词,如果没有提取到任何关键词，默认返回['全部']"""
        if html_content:
            content_keywords = self.extract_content_keywords(text, html_content)
            if content_keywords:
                return content_keywords

        if '全部' in text or '完整' in text or '整个' in text:
            return ['全部']

        if '内容标题' in text or ('标题' in text and '内容' in text):
            return ['h1', 'header h1']

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
        for chinese_key, english_key in self.keyword_mapping.items():
            if chinese_key in text:
                found_keywords.append(english_key)

        return found_keywords if found_keywords else ['全部']

    def find_text_positions(self, html: str, target_text: str) -> List[Dict[str, Any]]:
        """查找文本位置"""
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

    def parse_modification_command(self, cmd: str) -> Tuple[Optional[str], Optional[str]]:
        """解析修改指令"""
        patterns = [
            r"将['\"](.*?)['\"]改为['\"](.*?)['\"]",
            r"将(.*?)修改为(.*?)$",
            r"将(.*?)改为(.*?)$",
            r"把(.*?)改成(.*?)$"
        ]

        for pattern in patterns:
            match = re.search(pattern, cmd)
            if match:
                return match.group(1).strip(), match.group(2).strip()

        if "改为" in cmd:
            parts = cmd.split("改为")
            return parts[0].replace("将", "").strip(), parts[1].strip()
        elif "修改为" in cmd:
            parts = cmd.split("修改为")
            return parts[0].replace("将", "").strip(), parts[1].strip()

        return None, None

    def generate_html(self, request_content: str) -> str:
        """生成HTML文件"""
        self.clear_history()
        content = f"{request_content}，请返回一个完整的html文件"
        text = self.chat(content)

        if "```" not in text:
            raise ValueError("未检测到有效的HTML代码块")

        html_code = text.split("```")[1].strip()
        if html_code.startswith("html"):
            html_code = html_code[4:].strip()

        self.html_parts = self.parse_html(html_code)

        with open('output.html', 'w', encoding='utf-8') as f:
            f.write(html_code)

        return "HTML文件已生成并解析完成。"

    def modify_html_part(self, request_content: str) -> str:
        """修改HTML部分内容"""
        try:
            with open('output.html', 'r', encoding='utf-8') as f:
                current_html = f.read()
        except Exception as e:
            raise IOError(f"读取HTML文件失败: {str(e)}")

        # 尝试解析为文本修改指令
        target_text, new_text = self.parse_modification_command(request_content)

        if target_text and new_text:
            try:
                modify_result = self._modify_text_content(current_html, target_text, new_text)
                if modify_result == "文本内容修改成功！":
                    return modify_result
            except Exception as e:
                # 文本修改失败，继续尝试其他方式
                pass

        # 尝试HTML结构修改
        try:
            modify_result = self._modify_html_structure(current_html, request_content)
            if modify_result == "HTML部分修改成功！":
                return modify_result
        except Exception as e:
            # 结构修改失败，继续尝试最后的方式
            pass

        # 最后尝试：直接传入整个html内容与要求
        try:
            prompt = self.PROMPT_TEMPLATE.format(
                elements=f"整个HTML文档内容:\n{current_html[:1000]}...",  # 限制长度防止过长
                request=request_content,
                example=self.DEFAULT_EXAMPLE
            )

            modify_result = self.chat(prompt)

            # 统一响应解析逻辑
            if "```html" in modify_result:
                updated_html = modify_result.split("```html")[1].split("```")[0].strip()
            elif "```" in modify_result:
                updated_html = modify_result.split("```")[1].strip()
                if updated_html.lower().startswith("html"):
                    updated_html = updated_html[4:].strip()
            else:
                updated_html = modify_result  # 假设整个响应就是HTML

            self._save_updated_html(updated_html)
            return "HTML修改成功！"

        except Exception as e:
            return f"修改HTML时出错: {str(e)}"

    def _modify_text_content(self, html: str, target_text: str, new_text: str) -> str:
        """修改文本内容"""
        matches = self.find_text_positions(html, target_text)

        if not matches:
            # 尝试模糊匹配
            soup = BeautifulSoup(html, 'html.parser')
            for element in soup.find_all(text=True):
                if target_text in str(element):
                    parent = element.parent
                    full_text = str(parent)
                    start_pos = html.find(full_text)
                    if start_pos != -1:
                        matches.append({
                            'start': start_pos,
                            'end': start_pos + len(full_text),
                            'full_text': full_text,
                            'element': element,
                            'parent': parent
                        })
                        break

        if not matches:
            return "未找到匹配的文本内容"

        modified_part = self.chat(self.PROMPT_TEMPLATE.format(
            element=matches[0]['full_text'],
            request='将"{target_text}"替换为："{new_text}"',
            example=f"""```html
                    {matches[0]['parent'].prettify().split('\n')[0].strip()}
                    {new_text}
                    {matches[0]['parent'].prettify().split('\n')[-1].strip()}
                    ```"""
        ))

        if "```html" in modified_part:
            new_part = modified_part.split("```html")[1].split("```")[0].strip()
        elif "```" in modified_part:
            new_part = modified_part.split("```")[1].strip()
            if new_part.lower().startswith("html"):
                new_part = new_part[4:].strip()
        else:
            return "AI返回格式不正确"

        # 验证标签是否匹配
        original_tag = matches[0]['parent'].name
        if f"<{original_tag}" not in new_part.lower():
            raise ValueError(f"AI没有保持原标签结构，期望<{original_tag}>标签")

        # 执行替换
        updated_html = html[:matches[0]['start']] + new_part + html[matches[0]['end']:]

        self._save_updated_html(updated_html)
        return "文本内容修改成功！"

    def _modify_html_structure(self, html: str, request_content: str) -> str:
        """修改HTML结构"""
        soup = BeautifulSoup(html, 'html.parser')
        keywords = self.extract_chinese_keywords(request_content, html)

        if "全部" in keywords:
            modified_part = self.chat(self.PROMPT_TEMPLATE.format(
            element=html,
            request=request_content,
            example="""````html<h2>修改后的内容</h2>```"""
            ))

            if "```html" in modified_part:
                updated_html = modified_part.split("```html")[1].split("```")[0].strip()
            elif "```" in modified_part:
                updated_html = modified_part.split("```")[1].strip()
                if updated_html.lower().startswith("html"):
                    updated_html = updated_html[4:].strip()
            else:
                return "AI返回格式不正确"
        else:
            elements_to_modify = self._find_elements_to_modify(soup, keywords)

            if not elements_to_modify:
                return "未找到与关键词对应的HTML部分"

            parts_info = []
            for element in elements_to_modify:
                parent = element.find_parent()
                parent_name = parent.name if parent else '根'
                parts_info.append(f"""
                位于{parent_name}中的{element.name}元素:
                {str(element)}
                """)

            parts_text = "\n".join(parts_info)

            modified_part = self.chat(self.PROMPT_TEMPLATE.format(
            element=parts_text,
            request=request_content,
            example="""````html<h2>修改后的内容</h2>```"""
            ))

            if "```html" in modified_part:
                new_part = modified_part.split("```html")[1].split("```")[0].strip()
            elif "```" in modified_part:
                new_part = modified_part.split("```")[1].strip()
                if new_part.lower().startswith("html"):
                    new_part = new_part[4:].strip()
            else:
                return "AI返回格式不正确"

            # 精确替换HTML部分
            updated_html = html
            for element in elements_to_modify:
                if element and str(element) in updated_html:
                    updated_html = updated_html.replace(str(element), new_part, 1)
                    break

        self._save_updated_html(updated_html)
        return "HTML部分修改成功！"

    def _find_elements_to_modify(self, soup: BeautifulSoup, keywords: List[str]) -> List[Tag]:
        """查找需要修改的元素"""
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
            elif keyword in self.html_parts:
                if keyword == 'title':
                    elements_to_modify.append(soup.title)
                elif keyword == 'head':
                    elements_to_modify.append(soup.head)
                elif keyword == 'body':
                    elements_to_modify.append(soup.body)
                elif keyword == 'footer':
                    footer = soup.find('footer') 或 soup.find(class_=['footer'， 'bottom'])
                    if footer:
                        elements_to_modify.append(footer)
                elif keyword == 'nav':
                    nav = soup.find('nav') 或 soup.find(class_=['nav'， 'navbar'])
                    if nav:
                        elements_to_modify.append(nav)

        return elements_to_modify

    def _save_updated_html(self, html: str):
        """保存更新后的HTML"""
        with open('output.html'， 'w', encoding='utf-8') as f:
            f.write(html)
        self.html_parts = self.parse_html(html)


# 创建全局HTML修改器实例
html_modifier = HTMLModifier()


@app.post("/generate_html")
async def generate_html(request: ChatRequest):
    """生成HTML文件的API端点"""
    try:
        result = html_modifier.generate_html(request.content)
        return PlainTextResponse(result)
    except Exception as e:
        return PlainTextResponse(f"生成HTML时出错: {str(e)}", status_code=500)


@app.post("/modify_html_part")
async def modify_html_part(request: ChatRequest):
    """修改HTML部分的API端点"""
    try:
        result = html_modifier.modify_html_part(request.content)
        return PlainTextResponse(result)
    except Exception as e:
        return PlainTextResponse(f"修改HTML时出错: {str(e)}", status_code=500)


@app.post("/clear_conversation_history")
async def clear_history():
    """清空对话历史的API端点"""
    html_modifier.clear_history()
    return PlainTextResponse("对话历史和HTML解析结果已清空。")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
