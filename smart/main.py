import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import field
import requests
from prompt import *
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage
from volcenginesdkarkruntime import Ark


class DialogHistory:
    def __init__(self, max_length: int = 3):
        self.history: List[Dict] = []
        self.max_length = max_length
        self.current_scene: Optional[str] = None  # 明确标注可为None
        self.scene_persist_counter = 0  # 场景持续计数器

    def add(self, user_input: str, response: list) -> None:
        self.history.append({
            "user": user_input,
            "system": response,
            "timestamp": time.time()
        })
        if len(self.history) > self.max_length:
            self.history.pop(0)

    def get_context(self) -> str:
        return "\n======\n".join(
            f"用户:{item['user']}\n系统:{item['system']}"
            for item in self.history
        )

    def detect_scene(self, user_input: str) -> Optional[str]:
        """实时场景检测（单条触发机制）"""
        if self.current_scene is not None:
            self.scene_persist_counter -= 1  # 每轮无匹配递减
            return self.current_scene

        # 清空场景的条件（计数器归零或没有设备匹配）
        if self.scene_persist_counter <= 0:
            self.current_scene = None

        # 实时关键词检测
        detected_scene = None
        for scene, keywords in SCENE_KEYWORDS.items():
            if any(keyword in user_input for keyword in keywords):
                detected_scene = scene
                break

        # 更新场景状态
        if detected_scene:
            self.current_scene = detected_scene
            self.scene_persist_counter = self.max_length  # 设置几轮对话的持续期

        return self.current_scene

    def force_exit_scene(self):
        self.current_scene = None


history = DialogHistory()


class UserProfile:
    # 基础信息
    age: Optional[int]
    gender: Optional[str]
    region: Optional[str]
    # 家庭信息
    family_members: int
    has_children: bool
    has_elderly: bool
    has_pet: bool
    #生活习惯
    work_schedule: str  # "regular", "night_shift", "flexible"
    cooking_habits: str  # "rare", "medium", "frequent"
    device_usage: Dict[str, int] = field(default_factory=dict)  # 设备使用次数统计

    def __init__(self, age: Optional[int] = 20, gender: Optional[str] = "male",
                 region: Optional[str] = "south", family_members: Optional[int] = 1,
                 has_children: Optional[bool] = False, has_elderly: Optional[bool] = False,
                 has_pet: Optional[bool] = False, work_schedule: Optional[str] = "regular",
                 cooking_habits: Optional[str] = "medium", device_usage: Dict[str, int] = None):
        self.age = age
        self.gender = gender
        self.region = region
        self.family_members = family_members
        self.has_children = has_children
        self.has_elderly = has_elderly
        self.has_pet = has_pet
        self.work_schedule = work_schedule
        self.cooking_habits = cooking_habits
        self.device_usage = device_usage

    def record_device_usage(self, device_name: str):
        """记录设备使用次数"""
        self.device_usage[device_name] = self.device_usage.get(device_name, 0) + 1

    def save_to_file(self, filepath: str):
        """保存完整用户数据"""
        data = {
            "basic_info": {
                "age": self.age,
                "gender": self.gender,
                "region": self.region,
            },
            "family_info": {
                "family_members": self.family_members,
                "has_children": self.has_children,
                "has_elderly": self.has_elderly,
                "has_pet": self.has_pet,
            },
            "device_data": {
                "usage": self.device_usage,
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str):
        """从文件加载完整数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return cls(
                    age=data["basic_info"].get("age"),
                    gender=data["basic_info"].get("gender"),
                    region=data["basic_info"].get("region"),
                    family_members=data["family_info"].get("family_members", 1),
                    has_children=data["family_info"].get("has_children", False),
                    has_elderly=data["family_info"].get("has_elderly", False),
                    has_pet=data["family_info"].get("has_pet", False),
                    device_usage=data["device_data"].get("usage", {})
                )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return cls()  # 返回默认配置


def get_seasonal_context() -> Dict[str, str]:
    """Get current season and time of day"""
    now = datetime.now()
    month = now.month
    hour = now.hour
    weekday_num = now.weekday()  # 返回0-6的数字，0代表周一，6代表周日
    # 转换为中文星期
    weekdays = "weekday" if 0 <= weekday_num <= 4 else "weekend"

    season = (
        "spring" if 3 <= month <= 5 else
        "summer" if 6 <= month <= 8 else
        "autumn" if 9 <= month <= 11 else
        "winter"
    )

    time_of_day = (
        "morning" if 5 <= hour < 11 else
        "daytime" if 11 <= hour < 17 else
        "evening" if 17 <= hour < 23 else
        "night"
    )

    return {"season": f"{season}",
            "weekday": f"{weekdays}",
            "time": f"{time_of_day}"}


def recommend_devices(user: UserProfile, match_devices: List[Union[str, List[str]]]) -> List[str]:
    """综合推荐设备，同组设备只选评分最高的"""
    # 1. 获取当前上下文
    time_dict = get_seasonal_context()
    season = time_dict["season"]
    weekday = time_dict["weekday"]
    time = time_dict["time"]

    # 2. 计算设备评分
    device_scores = {}

    # 评分规则
    def calculate_score(device: str) -> float:
        score = 0.0
        # 地域特征
        if device in REGION_DEVICE_MAP[user.region].get(season, []):
            score += 3.0
        # 家庭特征
        for feature, devices in FAMILY_FEATURE_MAP.items():
            if getattr(user, feature) and device in devices:
                score += 2.5
        # 生活习惯
        if device in LIFESTYLE_FEATURES_MAP["cooking"][user.cooking_habits]:
            score += 2.0
        if user.work_schedule != "regular" and device in LIFESTYLE_FEATURES_MAP["work_schedule"][user.work_schedule]:
            score += 1.5
        # 时间相关
        if device in SEASON_DEVICE_MAP[season]:
            score += 1.0
        if device in TIME_DEVICE_MAP[weekday][time]:
            score += 1.0
        # 使用频率
        score += user.device_usage.get(device, 0) * 0.2
        return score

    # 3. 处理设备组
    result = []
    processed_groups = set()

    for group in match_devices:
        if isinstance(group, str):
            # 单个设备直接评分
            score = calculate_score(group)
            device_scores[group] = score
            result.append(group)
        else:
            # 设备组转换为元组作为key
            group_key = tuple(sorted(group))
            if group_key not in processed_groups:
                # 找出组内最高分设备
                best_device = max(group, key=lambda d: calculate_score(d))
                device_scores[best_device] = calculate_score(best_device)
                result.append(best_device)
                processed_groups.add(group_key)

    # 4. 按评分排序
    result.sort(key=lambda d: -device_scores.get(d, 0))

    return result if result else None


def match_keyword(text: str) -> Optional[list[str]]:
    """返回匹配到的设备列表，未匹配返回None"""
    text = text.lower()
    result = list()
    for keyword, devices in KEYWORD_MAP.items():
        if keyword in text:
            if len(devices) == 1:
                result.append(devices[0])
            else:
                result.append(devices)
    return result


def get_access_token() -> str:
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
    payload = json.dumps({
        "messages": content,
        "temperature": 0.5
    })

    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={get_access_token()}"
    response = requests.post(url, headers={'Content-Type': "application/json"}, data=payload)
    return response.json()['result']


def chat_spark(content: str) -> str:
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


def chat_doubao(content: str) -> str:
    """与豆包AI聊天并获取响应"""
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
            {"role": "user", "content": f"{content}"},
        ],
        extra_headers={'x-is-encrypted': 'true'},
    )
    return completion.choices[0].message.content


def chat_deepseek(content: str) -> str:
    """与Deepseek AI聊天并获取响应"""
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
            {"role": "user", "content": f"{content}"},
        ],
        extra_headers={'x-is-encrypted': 'true'},
    )
    return completion.choices[0].message.content


def check_device(matched_devices: list) -> bool:
    if all(isinstance(item, str) for item in matched_devices) is True:
        return True
    else:
        return False


def get_device(user_input: str, user_profile: UserProfile) -> list[str] | str:
    # 实时场景检测
    current_scene = history.detect_scene(user_input)
    if current_scene:
        print("处于"+current_scene+"（输入结束场景来停止）")
    # 先尝试关键词匹配
    matched_devices = match_keyword(user_input)
    # print(matched_devices)
    # 场景敏感的设备过滤
    if matched_devices and current_scene:
        current_scene_devices = SCENE_DEVICE_MAP.get(current_scene, [])
        filtered_devices = []
        for device in matched_devices:
            if isinstance(device, str):
                if device in current_scene_devices:
                    filtered_devices.append(device)
            elif isinstance(device, list):
                for dev in device:
                    if dev in current_scene_devices:
                        filtered_devices.append(dev)
        matched_devices = filtered_devices
        if matched_devices:
            return matched_devices
        if not matched_devices:  # 关键修改：无匹配立即退出场景
            history.force_exit_scene()

    # print(matched_devices)
    if not matched_devices:
        matched_devices = match_keyword(user_input)
        # 根据时间和用户画像选择最匹配的电器
        matched_devices = recommend_devices(user_profile, matched_devices)
        # print(matched_devices)
        # if check_device(matched_devices):
        #     return matched_devices

    # 无匹配则走AI流程
    prompt = PROMPT.format(
        user_input=user_input,
    )

    response = chat_spark(prompt)
    return response


def main():
    # Initialize services
    user_profile = UserProfile(
        age=20,
        gender="male",
        family_members=3,
        has_children=True,
        work_schedule="regular",
        cooking_habits="frequent",
        device_usage={"空调": 5, "智能门锁": 1, "摄像头": 1, "扫地机器人": 3, }
    )

    while True:
        # print("当前用户画像:", ContextService.get_user_context(user_profile))
        # print(user_profile.get_sorted_devices())
        user_input = input("用户输入（输入退出来结束）: ").strip()

        if user_input.lower() in ("退出", "exit"):
            break
        elif user_input.lower() in "结束场景":
            history.force_exit_scene()
            print("场景已结束")
            continue

        device = get_device(user_input, user_profile)
        print(f"需要操作的设备: {device}")
        history.add(user_input, device)
        for dev in device:
            user_profile.record_device_usage(dev)

    user_profile.save_to_file("user_profile.json")

if __name__ == "__main__":
    main()
