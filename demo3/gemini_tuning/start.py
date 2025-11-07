import logging
import yaml
from gemini_tuning.evaluator import Evaluator
from gemini_tuning.tuning import Tuning
def load_prompts(file_path: str) -> list[str]:
    """读取 prompts 文件，每行一个 prompt"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def main(config_path: str):
    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    logging.info("配置文件加载完成")
    # 初始化tuning
    tuning = Tuning(config)

    # 创建并执行微调任务
    logging.info(f"开始创建微调任务...")
    tuning_result = tuning.start_tuning()

    if not tuning_result.success:
        logging.error(f"微调任务创建失败: {tuning_result.error_message}")
        return

    logging.info(f"微调任务完成，模型 endpoint: {tuning_result.model_endpoint}")

    # 读取 prompts
    prompts = load_prompts(config["evaluation"]["prompts_file"])
    logging.info(f"加载 {len(prompts)} 条评估 prompts 完成")

    # 初始化 Evaluator 并执行评估
    evaluator = Evaluator(config)
    eval_result = evaluator.evaluate(
        model_endpoint="projects/601797833546/locations/us-central1/endpoints/2125297702374735872",
        prompts=prompts,
    )
    if eval_result.success:
        logging.info(f"评估完成，总分: {eval_result.score}")
    else:
        logging.error(f"评估失败: {eval_result.error_message}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="启动微调和评估任务（配置文件方式）")
    parser.add_argument("--config", type=str, required=True, help="配置文件路径（YAML）")
    args = parser.parse_args()

    main(args.config)
