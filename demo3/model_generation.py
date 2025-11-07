from google import genai
import yaml
from google.genai import types
from tools.log_utils import get_logger

logger = get_logger(__name__)
# 读取配置

def build_prompt_template(user_question: str) -> str:
    return f"""
    你是一个专业的游戏客服，请根据以下规则回答玩家问题：
    1. 回答必须简洁清晰。
    2. 对玩家要时刻保持友好。
    3. 如果无法确定答案，需要给出基本思路然后建议转人工客服。
    4. 要保证你回答的语言是玩家提问所用的语言。
    玩家问题: {user_question}
    """

def start_chats(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 初始化模型
    client = genai.Client(
        vertexai=True,
        project=config["project_id"],
        location=config["location"]
    )
    # 开启一个对话
    chat = client.chats.create(
        model= "xxxxxxxxx",
        config=types.GenerateContentConfig(
            # 模型不需要每次回答都随机相反很多问题的回答应该保持一致
            seed=1,
            max_output_tokens=1024,
            # 关闭thinking，改项目中不需要思考，并且思考会影响响应时间
            thinking_config=types.ThinkingConfig(
                thinking_budget=0
            )
        ),
        history=[]
    )

    logger.info("开启一轮新对话")

    while True:
        user_input = input("你: ")
        if user_input.lower() in ["exit", "quit", "退出"]:
            print("👋 再见！")
            break

        response = chat.send_message(
            message=build_prompt_template(user_input),
        )
        print("AI:", response.text)

start_chats("config/config.yaml")