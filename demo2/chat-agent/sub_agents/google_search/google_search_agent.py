"""
Google搜索代理模块

此模块定义了一个专门用于Google搜索的代理。
"""

import os
from google.adk import Agent
from google.adk.tools import google_search

# 创建Google搜索代理实例
# 该代理专门处理Google搜索任务
google_search_agent = Agent(
    model=os.getenv("MODEL_ID"),  # 使用环境变量中配置的模型ID
    name="google_search_agent",   # 代理名称
    description="专门用于Google搜索的代理",  # 代理描述
    tools=[google_search],        # 代理使用的工具列表，这里只包含Google搜索工具
)