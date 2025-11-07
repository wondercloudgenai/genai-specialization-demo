"""
VertexAI搜索代理模块

此模块定义了一个专门用于VertexAI搜索的代理。
"""

import os
from google.adk import Agent
from google.adk.tools import VertexAiSearchTool

# 创建VertexAI搜索代理实例
# 该代理专门处理VertexAI搜索任务
vertexai_search_agent = Agent(
    model=os.getenv("MODEL_ID"),   # 使用环境变量中配置的模型ID
    name="vertexai_google_search_agent",  # 代理名称
    description="专门用于VertexAI搜索的代理",  # 代理描述
    tools=[VertexAiSearchTool(data_store_id=os.getenv("DATASTORE_ID"))]  # 代理使用的工具列表，这里只包含VertexAI搜索工具
)