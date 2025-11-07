import time
from typing import Any, Dict, Optional
from dataclasses import dataclass
from tools.log_utils import get_logger
from google import genai
from google.genai import types
from google.genai.types import AdapterSize

logger = get_logger(__name__)

# 模型适配器大小映射
adapter_size_map = {
    1: AdapterSize.ADAPTER_SIZE_ONE,
    2: AdapterSize.ADAPTER_SIZE_TWO,
    4: AdapterSize.ADAPTER_SIZE_FOUR,
    8: AdapterSize.ADAPTER_SIZE_EIGHT,
    16: AdapterSize.ADAPTER_SIZE_SIXTEEN,
    32: AdapterSize.ADAPTER_SIZE_THIRTY_TWO,
}

@dataclass
class TuningResult:
    success: bool
    model_endpoint: Optional[str] = None
    checkpoints: Optional[list[types.TunedModelCheckpoint]] = None
    error_message: Optional[str] = None


class Tuning:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Trainer
        Args:
            config: 配置字典，包含模型、数据集、超参等
        """
        self.client = genai.Client(
            vertexai=True,
            project=config["project_id"],
            location=config["location"]
        )
        self.base_model = config["tuning"]["base_model"]
        self.model_name = config["tuning"]["tuned_model_display_name"]
        self.epochs = config["tuning"].get("epochs", 1)
        self.learning_rate_multiplier = config["tuning"].get("learning_rate_multiplier", 1.0)
        self.adapter_size = adapter_size_map[config["tuning"].get("adapter_size", 4)]
        self.export_last_checkpoint_only = config["tuning"].get("export_last_checkpoint_only", True)

        self.timeout_hours = config["tuning"].get("timeout_hours", 6)

        self.train_dataset_url = config["dataset"]["train_url"]
        self.val_dataset_url = config["dataset"]["val_url"]

        logger.info(f"Trainer 初始化完成 base_model={self.base_model}, "
                    f"tuned_model={self.model_name}, timeout={self.timeout_hours}h")

    def start_tuning(self) -> TuningResult:
        """
        执行模型微调任务
        Returns:
            TuningResult: 包含 success 状态、endpoint、checkpoints、错误信息
        """
        training_dataset = types.TuningDataset(
            gcs_uri=self.train_dataset_url,
        )
        validation_dataset = types.TuningValidationDataset(
            gcs_uri=self.val_dataset_url,
        )
        try:
            # 配置微调任务
            tuning_job = self.client.tunings.tune(
                base_model= self.base_model,
                training_dataset = training_dataset,
                config= types.CreateTuningJobConfig(
                    validation_dataset=validation_dataset,
                    tuned_model_display_name=self.model_name,
                    epoch_count=self.epochs,
                    # learning_rate_multiplier=self.learning_rate_multiplier,
                    export_last_checkpoint_only=self.export_last_checkpoint_only,
                    # adapter_size=self.adapter_size,
                )
            )
            logger.info(f"微调任务已创建: {tuning_job.name}")

            running_states = {"JOB_STATE_PENDING", "JOB_STATE_RUNNING"}
            start_time = time.time()

            while tuning_job.state in running_states:
                elapsed = (time.time() - start_time) / 3600
                if elapsed > self.timeout_hours:
                    msg = f"任务 {tuning_job.name} 超时（超过 {self.timeout_hours} 小时）"
                    logger.error(msg)
                    return TuningResult(success=False, error_message=msg, model_endpoint=None)

                logger.info(f"当前作业状态: {tuning_job.state}")
                time.sleep(60)
                tuning_job = self.client.tunings.get(name=tuning_job.name)
            # 最终状态
            if tuning_job.state == "JOB_STATE_SUCCEEDED":
                model_endpoint = tuning_job.tuned_model.endpoint
                logger.info(f"微调任务完成，模型端点: {model_endpoint}")
                if self.export_last_checkpoint_only is True:
                    checkpoints = tuning_job.tuned_model.checkpoints
                else:
                    checkpoints = None
                return TuningResult(
                    success=True,
                    model_endpoint=model_endpoint,
                    checkpoints= checkpoints
                )
            else:
                msg = f"微调任务失败，最终状态: {tuning_job.state}"
                logger.error(msg)
                return TuningResult(success=False, error_message=msg)

        except Exception as e:
            msg = f"创建微调任务时出错: {e}"
            logger.exception(msg)
            return TuningResult(success=False, error_message=msg)
