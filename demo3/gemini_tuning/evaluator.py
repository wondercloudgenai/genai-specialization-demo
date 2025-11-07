import os
import pandas as pd
from typing import Any, Dict, Optional
from dataclasses import dataclass

from vertexai import init, generative_models
from vertexai.evaluation import EvalTask, PointwiseMetric, PointwiseMetricPromptTemplate
from tools.log_utils import get_logger

logger = get_logger(__name__)


def build_prompt_template(user_question: str) -> str:
    return f"""
    你是一个专业的游戏客服，请根据以下规则回答玩家问题：
    1. 回答必须简洁清晰。
    2. 对玩家要时刻保持友好。
    3. 如果无法确定答案，需要给出基本思路然后建议转人工客服。
    4. 回答的语言必须与玩家问题的语言一致。
    玩家问题: {user_question}
    """

@dataclass
class EvalResult:
    success: bool
    score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class Evaluator:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Evaluator
        Args:
            config: 配置字典
        """
        self.config = config
        self.project_id = config["project_id"]
        self.location = config["location"]
        self.experiment = config["evaluation"]["experiment_name"]

        init(project=self.project_id, location=self.location)
        logger.info("Evaluator 初始化完成")


    def evaluate(self, model_endpoint: str, prompts: list[str]) -> EvalResult:
        """
        执行模型评估（BYOR 模式）
        Args:
            model_endpoint: 已微调模型的 endpoint
            prompts: 要测试的 prompt 列表
        Returns:
            EvalResult: 评估结果
        """

        try:
            logger.info(f"开始评估模型: {model_endpoint}")

            # 加载 endpoint model
            endpoint_model = generative_models.GenerativeModel(model_endpoint)

            # 生成模型回复
            responses = []
            for i, p in enumerate(prompts):
                logger.info(f"正在生成第 {i+1}/{len(prompts)} 条回复...")
                r = endpoint_model.generate_content(build_prompt_template(p))
                responses.append(r.text)
            logger.info("所有回复生成完毕")

            # 构建 DataFrame
            eval_dataset = pd.DataFrame({
                "prompt": prompts,
                "response": responses,
            })

            # 定义自定义指标
            custom_metric = PointwiseMetric(
                metric="game-customer-support-quality",
                metric_prompt_template=PointwiseMetricPromptTemplate(
                    criteria={
                        "关键步骤完整性": "回复是否包含关键步骤和指令。例如忘记密码场景必须包含“验证码”和“联系客服”等关键字眼。",
                        "回答条理性": "回复是否逻辑清晰、条理分明，步骤清楚，便于用户操作。",
                        "语气和风格": "语气是否友好、耐心，符合游戏客服风格，并且要用敬语。",
                        "内容相关性": "回答是否紧扣游戏问题，不提供游戏外通用操作或其他领域信息。",
                    },
                    rating_rubric={
                        "1": "完全符合标准，关键步骤完整，条理清晰，语气友好，内容相关。",
                        "0": "部分符合标准，有少量缺失或稍微不清晰。",
                        "-1": "不符合标准，缺少关键步骤或回答不清楚或无关。",
                    },
                ),
            )

            # 构建并执行评估任务
            eval_task = EvalTask(
                dataset=eval_dataset,
                metrics=[custom_metric],
                experiment=self.experiment,
            )
            logger.info("开始执行评估...")
            eval_result = eval_task.evaluate()

            # 提取指标
            total_score = eval_result.summary_metrics["game-customer-support-quality/mean"]
            logger.info("=== 总体评估指标 ===")
            logger.info(eval_result.metrics_table)
            logger.info("=== 评估结果分析 ===")
            logger.info(eval_result.summary_metrics)

            if total_score == 1.0:
                logger.info("微调效果显著，符合微调目标")
            elif total_score > 0.8:
                logger.warning("评估结果及格，基本符合微调目标")
            elif total_score < 0.8:
                logger.warning("评估结果不及格，微调效果不佳，需要进一步优化")
            else:
                logger.error("评估结果未知，请重新评估")

            return EvalResult(success=True, score=total_score, details=eval_result.summary_metrics)

        except Exception as e:
            msg = f"模型评估出错: {e}"
            logger.exception(msg)
            return EvalResult(success=False, error_message=msg)
