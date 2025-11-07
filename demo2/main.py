"""
多Agent智能聊天系统主入口文件

此文件是整个应用的入口点，负责初始化FastAPI应用并启动服务器。
"""

import os
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
import dotenv

# 配置日志记录
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# 抑制 aiohttp 和 asyncio 的资源警告
import logging
import warnings

# 抑制 aiohttp 和 asyncio 的资源警告
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", message=".*Unclosed.*")


# 从.env文件加载环境变量
dotenv.load_dotenv()

# 项目根目录路径
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 从环境变量读取服务URI配置，设置默认值
SESSION_SERVICE_URI = os.getenv("SESSION_SERVICE_URI", "agentengine://1613489333296168960")  # 会话服务URI
RAG_MEMORY_SERVICE_URI = os.getenv("RAG_MEMORY_SERVICE_URI", "rag://5044031582654955520")    # RAG内存服务URI
BANK_MEMORY_SERVICE_URI = os.getenv("BANK_MEMORY_SERVICE_URI", "agentengine://1613489333296168960")  # 银行内存服务URI

# 解析允许的跨域来源
ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost,http://localhost:8080,*").split(",") if origin.strip()
]

# 其他配置项
TRACE_TO_CLOUD = os.getenv("TRACE_TO_CLOUD", "true").lower() == "true"  # 是否追踪到云端
ENABLE_WEB = os.getenv("ENABLE_WEB", "true").lower() == "true"          # 是否启用Web界面

# 初始化FastAPI应用
# 使用Google ADK提供的get_fast_api_app函数创建应用实例
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,                    # Agent目录
    session_service_uri=SESSION_SERVICE_URI, # 会话服务URI
    memory_service_uri=BANK_MEMORY_SERVICE_URI,  # 内存服务URI
    allow_origins=ALLOWED_ORIGINS,           # 允许的跨域来源
    web=ENABLE_WEB,                          # 是否启用Web界面
    trace_to_cloud=TRACE_TO_CLOUD,           # 是否追踪到云端
)


# 主程序入口
if __name__ == "__main__":
    import uvicorn
    # 从环境变量获取主机和端口配置，默认为0.0.0.0:8080
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    #logger.info(f"正在启动服务器 {host}:{port}")
    # 启动uvicorn服务器
    uvicorn.run(app, host=host, port=port)