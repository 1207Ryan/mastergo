# 智能家居设备识别系统

本系统通过自然语言处理识别用户指令对应的智能家居设备，支持多AI模型后端（讯飞星火、百度千帆、豆包、DeepSeek）。

## 功能特性

- 从自然语言指令中精准识别家居设备
- 支持多AI模型后端：
  - 讯飞星火（Spark AI）
  - 百度千帆（Qianfan）
  - 字节豆包（Volcengine Ark）
  - DeepSeek
- 智能维护对话历史上下文
- 易于扩展新的AI服务提供商

## 安装指南

1. 克隆本仓库
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
配置环境变量（见配置说明）

## 配置说明
创建 .env 文件并配置以下API密钥：

SPARK_API_KEY=您的星火API密钥
SPARK_SECRET_KEY=您的星火密钥
QIANFAN_API_KEY=您的千帆API密钥
QIANFAN_SECRET_KEY=您的千帆密钥
ARK_API_KEY=您的豆包API密钥
DS_API_KEY=您的DeepSeek密钥

## 使用方式
运行主程序：
python main.py
示例交互：

用户输入（输入退出来结束）: 房间太热了
需要操作的设备: 空调 电风扇

## 支持设备列表
系统可识别以下设备：

空调、灯光、窗帘、电视、热水器、加湿器、除湿机、扫地机器人、洗衣机

烘干机、冰箱、烤箱、微波炉、电饭煲、净水器、空气净化器、新风系统

智能门锁、摄像头、插座、电风扇、暖气、浴霸、智能马桶、投影仪、电热毯




---
