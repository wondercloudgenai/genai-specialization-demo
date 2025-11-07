"""
统一智能助手主代理模块

此模块定义了多Agent系统的主代理，集成搜索、记忆和自定义功能，
并实现智能路由和自动保存功能。
"""

"""
统一智能助手主代理模块

此模块定义了多Agent系统的主代理，集成搜索、记忆和自定义功能，
并实现智能路由和自动保存功能。
"""

import os
# 移除 logging 导入
# import logging
from google.adk.agents import Agent
from google.adk.memory import VertexAiMemoryBankService
from google.adk.planners import BuiltInPlanner
from google.adk.sessions import VertexAiSessionService
from google.adk.tools import google_search
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types
from google.adk.tools import VertexAiSearchTool
from .prompt import instructions_prompt

from dotenv import load_dotenv

# 替换 logging 配置为简单的 print 函数
def log_info(message):
    print(f"INFO: {message}")

def log_warning(message):
    print(f"WARNING: {message}")

def log_error(message):
    print(f"ERROR: {message}")

# 加载当前目录下的 .env 文件
load_dotenv()

# ===================== 服务工厂 =====================

def _get_project_location_engine():
    """
    获取项目配置信息

    Returns:
        tuple: (project, location, agent_engine_id) 项目ID、位置和Agent引擎ID
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION")
    agent_engine_id = os.getenv("AGENT_ENGINE_ID")
    return project, location, agent_engine_id


def _get_memory_service() -> VertexAiMemoryBankService | None:
    """
    创建并返回内存服务实例

    Returns:
        VertexAiMemoryBankService | None: 内存服务实例或None（如果配置缺失）
    """
    try:
        project, location, agent_engine_id = _get_project_location_engine()
        # 检查必要配置是否存在
        if not (project and location and agent_engine_id):
            log_warning(f"[memory] 缺少必要配置: project={bool(project)} location={bool(location)} agent_engine_id={bool(agent_engine_id)}")
            return None
        # 创建并返回内存服务实例
        return VertexAiMemoryBankService(
            project=project,
            location=location,
            agent_engine_id=agent_engine_id,
        )
    except Exception as e:
        log_error(f"[memory] 创建VertexAiMemoryBankService失败: {e}")
        return None


def _get_session_service() -> VertexAiSessionService | None:
    """
    创建并返回会话服务实例

    Returns:
        VertexAiSessionService | None: 会话服务实例或None（如果配置缺失）
    """
    try:
        project, location, agent_engine_id = _get_project_location_engine()
        # 检查必要配置是否存在
        if not (project and location and agent_engine_id):
            log_warning(f"[memory] 会话服务缺少必要配置: project={bool(project)} location={bool(location)} agent_engine_id={bool(agent_engine_id)}")
            return None
        # 创建并返回会话服务实例
        return VertexAiSessionService(
            project=project,
            location=location,
            agent_engine_id=agent_engine_id,
        )
    except Exception as e:
        log_error(f"[memory] 创建VertexAiSessionService失败: {e}")
        return None


# ===================== 会话结束后自动保存回调 =====================

async def auto_save_to_memory_callback(callback_context):
    """
    会话结束后自动保存到内存的回调函数

    Args:
        callback_context: 回调上下文对象，包含会话相关信息
    """
    try:
        log_info("[memory] 触发自动保存到内存回调函数")
        # 获取调用上下文
        inv_ctx = getattr(callback_context, "_invocation_context", None)
        if inv_ctx is None:
            log_warning("[memory] 回调上下文中没有_invocation_context属性，跳过保存")
            return

        # 从上下文中提取会话信息
        session = getattr(inv_ctx, "session", None)
        user_id = getattr(inv_ctx, "user_id", None)
        app_name = getattr(getattr(inv_ctx, "session", None), "app_name", None)
        session_id = getattr(getattr(inv_ctx, "session", None), "id", None)
        log_info(f"[memory] 提取到的信息: app_name={app_name} user_id={user_id} session_id={session_id}")

        # 检查会话ID是否存在
        if session_id is None:
            log_warning("[memory] 没有会话ID，跳过保存")
            return

        # 获取内存服务实例
        memory_service = _get_memory_service()
        if memory_service is None:
            log_warning("[memory] 内存服务不可用，跳过保存")
            return

        # 1) 优先获取权威会话（兼容不同 ADK 版本的 get_session 签名）
        fetched_session = None
        sess_service = _get_session_service()
        if sess_service:
            # 尝试使用关键字参数形式获取会话
            if app_name and user_id and session_id:
                try:
                    fetched_session = await sess_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
                    log_info(f"[memory] 通过get_session(app_name={app_name}, user_id={user_id}, session_id={session_id})获取会话成功")
                except TypeError as e:
                    log_warning(f"[memory] get_session关键字参数形式失败: {e}")
                except Exception as e:
                    log_error(f"[memory] get_session关键字参数形式出错: {e}")

        # 确定目标会话对象
        target_session = fetched_session or session
        if target_session is None:
            log_warning("[memory] 没有目标会话，跳过保存")
            return

        # 2) 统计内容数量（尽量从权威会话统计）
        content_count = 0
        has_events = hasattr(target_session, "events") and target_session.events
        has_contents = hasattr(target_session, "contents") and target_session.contents
        # 根据会话对象类型统计内容数量
        if has_events:
            try:
                content_count = len(target_session.events)
            except Exception:
                content_count = 0
        elif has_contents:
            try:
                content_count = len(target_session.contents)
            except Exception:
                content_count = 0
        log_info(f"[memory] 内容统计: content_count={content_count} has_events={bool(has_events)} has_contents={bool(has_contents)}")
        # 如果内容太少则跳过保存
        if content_count < 1:
            log_info("[memory] 内容太少，跳过保存")
            return

        # 3) 优先保存整个会话
        try:
            # 尝试使用add_session_to_memory方法保存整个会话
            if hasattr(memory_service, "add_session_to_memory"):
                await memory_service.add_session_to_memory(target_session)
                log_info(f"[memory] 使用add_session_to_memory成功保存会话 {session_id}")
                return
            else:
                log_info("[memory] memory_service不支持add_session_to_memory方法，将回退到add_text方法")
        except Exception as e:
            log_error(f"[memory] add_session_to_memory方法执行失败: {e}，将回退到add_text方法")

    except Exception as e:
        log_error(f"[memory] 回调函数执行异常: {e}")
        return



# ===================== 主代理定义 =====================

# 创建主代理实例
root_agent=Agent(
    name=os.getenv("AGENT_NAME", "unified_agent"),  # 代理名称，默认为unified_agent
    model=os.getenv("MODEL_ID"),  # 使用的模型ID
    description="统一智能助手，集成搜索、记忆、自定义功能，自动选择最合适的工具",  # 代理描述
    instruction=instructions_prompt(),  # 指令提示词
    include_contents="default",  # 包含内容设置
    planner=BuiltInPlanner(  # 使用内置规划器
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,  # 不包含思考过程
            thinking_budget=0,  # 思考预算为0
        )
    ),
    output_key=os.getenv("OUTPUT_KEY"),  # 输出键设置
    # 由于Google API限制，我们只能使用搜索工具
    # 其他功能通过智能指令和内部逻辑来实现
    tools=[
        VertexAiSearchTool(data_store_id=os.getenv("DATASTORE_ID")),  # VertexAI搜索工具
        google_search,  # Google搜索工具
        PreloadMemoryTool()  # 预加载内存工具
        # AgentTool(agent=google_search_agent),  # Google搜索代理工具（已注释）
        # AgentTool(agent=vertexai_search_agent),  # VertexAI搜索代理工具（已注释）
    ],
    after_agent_callback=auto_save_to_memory_callback,  # 代理执行后的回调函数
)