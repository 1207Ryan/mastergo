import re
import json
from typing import Dict, List, Optional, Tuple, Any
import requests
from bs4 import BeautifulSoup, Tag
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage
from prompts import HTML_GENERATION, HTML_MODIFICATION, HTML_EXAMPLE, get_example_content
import os
from volcenginesdkarkruntime import Ark
import httpx
import jieba
import jieba.posseg as pseg


class HTMLModifier:
    """处理HTML生成和修改的核心类"""

    def __init__(self):
        self.conversation_history_qianfan: List[Dict[str, str]] = []
        self.conversation_history_spark: List[Dict[str, str]] = []
        self.conversation_history_doubao: List[Dict[str, str]] = []
        self.conversation_history_deepseek: List[Dict[str, str]] = []
        self.html_parts: Dict[str, Any] = {}
        self.keyword_mapping = {
            # 中文关键词到HTML元素的映射
            '头部': 'head',
            '标题': 'title',
            '主标题': 'h1',
            '二级标题': 'h2',
            '主体': 'body',
            '导航': 'nav',
            '页脚': 'footer',
            '脚本': 'script',
            '样式': 'style',
            '段落': 'p',
            '链接': 'a',
            '图片': 'img',
            '全部': 'all'
        }

    def clear_history_qianfan(self):
        """清空对话历史和HTML解析结果"""
        self.conversation_history_qianfan = []
        self.html_parts = {}

    def clear_history_spark(self):
        """清空对话历史和HTML解析结果"""
        self.conversation_history_spark = []
        self.html_parts = {}

    def clear_history_doubao(self):
        """清空对话历史和HTML解析结果"""
        self.conversation_history_doubao = []
        self.html_parts = {}

    def clear_history_deepseek(self):
        """清空对话历史和HTML解析结果"""
        self.conversation_history_deepseek = []
        self.html_parts = {}

    def _get_access_token_qianfan(self) -> str:
        """获取百度千帆API的访问令牌"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "client_id": os.environ.get("QIANFAN_API_KEY"),
            "client_secret": os.environ.get("QIANFAN_SECRET_KEY"),
            "grant_type": "client_credentials"
        }
        response = requests.post(url, params=params)
        return response.json()['access_token']

    def _chat_spark(self, content: str) -> str:
        """与讯飞星火AI聊天并获取响应"""
        spark = ChatSparkLLM(
            spark_api_url='wss://spark-api.xf-yun.com/v1.1/chat',
            spark_app_id='54f0b31e',
            spark_api_key=os.environ.get("SPARK_API_KEY"),
            spark_api_secret=os.environ.get("SPARK_SECRET_KEY"),
            spark_llm_domain='lite',
            streaming=False,
        )
        messages = [ChatMessage(
            role="user",
            content=content
        )]
        handler = ChunkPrintHandler()
        a = spark.generate([messages], callbacks=[handler])
        return a.generations[0][0].message.content

    def _chat_qianfan(self, content: str) -> str:
        """与百度千帆AI聊天并获取响应"""
        self.conversation_history_qianfan.append({"role": "user", "content": content})

        payload = json.dumps({
            "messages": self.conversation_history_qianfan,
            "temperature": 0.5
        })

        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={self._get_access_token_qianfan()}"
        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=payload)
        return response.json()['result']

    def _chat_doubao(self, content: str) -> str:
        """与豆包AI聊天并获取响应"""
        self.conversation_history_doubao.append({"role": "user", "content": content})

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

    def _chat_deepseek(self, content: str) -> str:
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

    def _parse_html(self, html_content: str) -> Dict[str, Any]:
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

    def _extract_content_keywords(self, text: str, html_content: str) -> List[Dict[str, Any]]:
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

    def _extract_chinese_keywords(self, text: str, html_content: Optional[str] = None) -> list[dict[str, Any]] | list[str] | list[str | Any]:
        """提取中文关键词,如果没有提取到任何关键词，默认返回['全部']"""
        if html_content:
            content_keywords = self._extract_content_keywords(text, html_content)
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

    def _find_text_positions(self, html: str, target_text: str) -> List[Dict[str, Any]]:
        """查找文本位置
        Args:
            html: 要搜索的HTML字符串
            target_text: 要查找的目标文本
        Returns:
            包含匹配位置信息的字典列表，每个字典包含:
            - start: 匹配文本在原始HTML中的起始位置
            - end: 匹配文本在原始HTML中的结束位置
            - full_text: 包含目标文本的完整父元素文本
            - element: BeautifulSoup元素对象
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        matches = []

        # 使用 string 替代已弃用的 text 参数
        for text_node in soup.find_all(string=lambda t: target_text in str(t)):
            parent = text_node.parent
            full_text = str(parent)
            start_pos = html.find(full_text)

            if start_pos != -1:
                matches.append({
                    'start': start_pos,
                    'end': start_pos + len(full_text),
                    'full_text': full_text,
                    'element': text_node
                })

        return matches

    def _parse_modification_command(self, cmd: str) -> Tuple[Optional[str], Optional[str]]:
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

    def generate_html_qianfan(self, request_content: str) -> str:
        """生成HTML文件"""
        self.clear_history_qianfan()
        #prompt = HTML_GENERATION.format(request=request_content) + get_example_content()
        prompt = f"""
                请根据以下要求修改下面的HTML文件：
                {request_content}
                HTML文件：
                {get_example_content()}
                """
        text = self._chat_qianfan(prompt)

        if "```" not in text:
            raise ValueError("未检测到有效的HTML代码块")

        html_code = text.split("```")[1].strip()
        if html_code.startswith("html"):
            html_code = html_code[4:].strip()

        self.html_parts = self._parse_html(html_code)

        with open('output.html', 'w', encoding='utf-8') as f:
            f.write(html_code)

        return "HTML文件已生成并解析完成。"

    def generate_html_spark(self, request_content: str) -> str:
        """生成HTML文件"""
        self.clear_history_spark()
        #prompt = HTML_GENERATION.format(request=request_content) + get_example_content()
        prompt = f"""
        将以下代码按照{request_content}的要求修改：
        {get_example_content()}
        """
        text = self._chat_spark(prompt)

        if "```" not in text:
            raise ValueError("未检测到有效的HTML代码块")

        html_code = text.split("```")[1].strip()
        if html_code.startswith("html"):
            html_code = html_code[4:].strip()

        self.html_parts = self._parse_html(html_code)

        with open('output_spark.html', 'w', encoding='utf-8') as f:
            f.write(html_code)

        return "HTML文件已生成并解析完成。"

    def generate_html_doubao(self, request_content: str) -> str:
        """生成HTML文件（增强版）"""
        self.clear_history_doubao()
        #prompt = HTML_GENERATION.format(request=request_content) + HTML_EXAMPLE
        prompt = f"""
                将以下代码按照{request_content}的要求修改：
                {get_example_content()}
                """
        text = self._chat_doubao(prompt)

        # 更健壮的代码块提取
        if "```html" in text:
            html_code = text.split("```html")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            # 取第二个代码块（通常第一个是语言标记）
            html_code = parts[1].strip() if len(parts) > 2 else parts[1].strip()
            if html_code.lower().startswith("html"):
                html_code = html_code[4:].strip()
        else:
            raise ValueError("未检测到有效的HTML代码块")

        # CSS验证
        if "<style>" in html_code:
            style_content = html_code.split("<style>")[1].split("</style>")[0]
            if "font-family" in style_content and not style_content.strip().endswith(";"):
                # 自动修复缺少分号的情况
                html_code = html_code.replace("font-family", "font-family;")

        # 保存前验证基本结构
        if not all(tag in html_code for tag in ["<!DOCTYPE", "<html", "<head", "<body"]):
            raise ValueError("生成的HTML缺少基本结构")

        self.html_parts = self._parse_html(html_code)

        try:
            with open('output_doubao.html', 'w', encoding='utf-8') as f:
                f.write(html_code)
            return "HTML文件已生成并解析完成。"
        except IOError as e:
            raise ValueError(f"文件保存失败: {str(e)}")

    def generate_html_deepseek(self, request_content: str) -> str:
        """生成HTML文件"""
        self.clear_history_deepseek()
        #prompt = HTML_GENERATION.format(request=request_content) + get_example_content()
        prompt = f"""
        将以下代码按照{request_content}的要求修改：
        {get_example_content()}
        """
        text = self._chat_deepseek(prompt)

        if "```" not in text:
            raise ValueError("未检测到有效的HTML代码块")

        html_code = text.split("```")[1].strip()
        if html_code.startswith("html"):
            html_code = html_code[4:].strip()

        self.html_parts = self._parse_html(html_code)

        with open('output_deepseek.html', 'w', encoding='utf-8') as f:
            f.write(html_code)

        return "HTML文件已生成并解析完成。"

    def modify_html(self, request_content: str) -> str:
        """智能修改HTML内容，只将需要修改的部分发送给AI

        Args:
            request_content: 用户修改指令，如"将A改为B"

        Returns:
            操作结果消息
        """
        try:
            # 1. 读取HTML文件
            with open('output.html', 'r', encoding='utf-8') as f:
                current_html = f.read()
        except Exception as e:
            raise IOError(f"读取HTML文件失败: {str(e)}")

        # 2. 尝试解析用户指令
        target_text, new_text = self._parse_modification_command(request_content)

        # 3. 如果指令明确，尝试精准修改
        if target_text and new_text:
            # print(target_text)
            # print(new_text)
            try:
                # 3.1 查找所有需要修改的上下文片段
                contexts = self._extract_modification_contexts(current_html, target_text)
                print(contexts)
                if contexts:
                    modifications = []
                    for ctx in contexts:
                        # 3.2 只将相关片段发送给AI处理
                        prompt = f"根据指令'{request_content}'修改以下HTML片段:\n{ctx['context']}"
                        #print(prompt)
                        ai_response = self._chat_spark(prompt)
                        #print(ai_response)
                        modified_context = self._parse_ai_response(ai_response)

                        # 3.3验证修改后的HTML结构
                        if not self._validate_html_structure(modified_context):
                            raise ValueError("AI返回的HTML结构无效")

                        modifications.append({
                            'modified_context': modified_context,
                            'position': ctx['position'],
                            'original_text': ctx['original_text']
                        })
                        print(modifications)
                    # 3.4 应用所有修改
                    updated_html = self._apply_modifications(current_html, modifications)
                    self._save_updated_html(updated_html)
                    return f"成功完成{len(modifications)}处精准修改"

                # 如果没有找到目标文本，继续尝试其他方式
                print(f"未找到文本'{target_text}'，尝试其他修改方式")
            except Exception as e:
                print(f"精准修改失败: {str(e)}，尝试其他方式")

        # 4. 尝试HTML结构修改
        try:
            modify_result = self._modify_html_structure(current_html, request_content)
            if modify_result == "HTML部分修改成功！":
                return modify_result
        except Exception as e:
            print(f"结构修改失败: {str(e)}，尝试完整修改")

        # 5. 最后尝试：完整HTML修改
        try:
            prompt = HTML_MODIFICATION.format(
                elements=f"HTML文档部分内容:\n{current_html[:5000]}...",  # 限制长度
                request=request_content,
            )
            modify_result = self._chat_spark(prompt)
            updated_html = self._parse_ai_response(modify_result)
            self._save_updated_html(updated_html)
            return "HTML修改成功！"
        except Exception as e:
            return f"修改HTML时出错: {str(e)}"

    def _extract_modification_contexts(self, html: str, target_text: str) -> list:
        """提取包含目标文本的HTML片段及其位置"""
        soup = BeautifulSoup(html, 'html.parser')
        contexts = []

        for text_node in soup.find_all(string=lambda t: target_text in str(t)):
            parent = text_node.parent
            full_text = str(parent)
            start_pos = html.find(full_text)

            if start_pos != -1:
                contexts.append({
                    'context': full_text,
                    'position': (start_pos, start_pos + len(full_text))
                })

        return contexts

    def _validate_html_structure(self, html_fragment: str) -> bool:
        """验证HTML片段结构是否合法"""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html_fragment, 'html.parser')
            # 检查是否存在未闭合标签
            if len(list(soup.descendants)) > 50:  # 限制片段大小
                return False
            return True
        except:
            return False

    def _apply_modifications(self, original_html: str, modifications: list) -> str:
        """将修改应用到原始HTML，处理结构化修改片段"""
        from bs4 import BeautifulSoup

        updated_html = original_html
        soup = BeautifulSoup(updated_html, 'html.parser')

        for mod in modifications:
            # 解析AI返回的修改片段
            modified_soup = BeautifulSoup(mod['modified_context'], 'html.parser')

            # 查找原始位置对应的元素
            original_fragment = soup.find(string=lambda t: mod['original_text'] in str(t))
            if not original_fragment:
                continue

            original_parent = original_fragment.parent

            # 处理不同类型的修改片段
            if modified_soup.find(class_='modified-section'):
                # 如果是带有特定class的div，替换整个父元素
                new_content = modified_soup.find(class_='modified-section')
                original_parent.replace_with(new_content)
            else:
                # 普通文本修改
                original_fragment.replace_with(modified_soup.get_text())

        return str(soup)

    def _parse_ai_response(self, ai_response: str) -> str:
        """解析AI返回的HTML内容"""
        if "```html" in ai_response:
            return ai_response.split("```html")[1].split("```")[0].strip()
        elif "```" in ai_response:
            html = ai_response.split("```")[1].strip()
            return html[4:].strip() if html.lower().startswith("html") else html
        return ai_response


    def _modify_text_content(self, html: str, target_text: str, new_text: str) -> str:
        """修改文本内容"""
        matches = self._find_text_positions(html, target_text)

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
            print("未找到匹配的文本内容")
            return "未找到匹配的文本内容"

        modified_part = self._chat_qianfan(HTML_MODIFICATION.format(
            element=matches[0]['full_text'],
            request=f'将"{target_text}"替换为："{new_text}"'
        ))

        if "```html" in modified_part:
            new_part = modified_part.split("```html")[1].split("```")[0].strip()
        elif "```" in modified_part:
            new_part = modified_part.split("```")[1].strip()
            if new_part.lower().startswith("html"):
                new_part = new_part[4:].strip()
        else:
            print("AI返回格式不正确")
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
        keywords = self._extract_chinese_keywords(request_content, html)

        if "全部" in keywords:
            modified_part = self._chat_qianfan(HTML_MODIFICATION.format(
                element=html,
                request=request_content
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

            modified_part = self._chat_qianfan(HTML_MODIFICATION.format(
                element=parts_text,
                request=request_content
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
                    footer = soup.find('footer') or soup.find(class_=['footer', 'bottom'])
                    if footer:
                        elements_to_modify.append(footer)
                elif keyword == 'nav':
                    nav = soup.find('nav') or soup.find(class_=['nav', 'navbar'])
                    if nav:
                        elements_to_modify.append(nav)

        return elements_to_modify

    def _save_updated_html(self, html: str):
        """保存更新后的HTML"""
        with open('output.html', 'w', encoding='utf-8') as f:
            f.write(html)
        self.html_parts = self._parse_html(html)
