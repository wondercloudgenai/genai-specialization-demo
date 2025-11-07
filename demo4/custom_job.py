from google.cloud import aiplatform
from dotenv import load_dotenv
import os
from datetime import datetime
# service_account_key_path="xxxxxxx.json"
# credentials = service_account.Credentials.from_service_account_file(
#     service_account_key_path,
#     scopes=['https://www.googleapis.com/auth/cloud-platform']
# )
def CustomJobHyperparameterTuningJob():
    load_dotenv()
    aiplatform.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION"),staging_bucket=os.getenv("BUCKET_URI"))

    job = aiplatform.CustomJob.from_local_script(
        display_name="kade-taxi-fare-pre-training-job",
        script_path="custom_job_HyperparameterTuningJob.py",         # 本地训练脚本
        # staging_bucket="gs://your-bucket-name",  # 中间文件存储桶
        # requirements=["pandas", "scikit-learn", "google-cloud-storage"],
        machine_type="n1-standard-4",   # VM 类型
        # https://cloud.google.com/vertex-ai/docs/training/pre-built-containers?hl=zh-cn#scikit-learn
        container_uri = "us-docker.pkg.dev/vertex-ai/training/sklearn-cpu.1-6:latest",
        # container_uri = "us-docker.pkg.dev/vertex-ai/training/tf-cpu.2-2:latest",
        requirements=["pandas", "seaborn", "matplotlib", "python-dotenv", "google-cloud-storage","scikit-learn","db-dtypes"], # 依赖库
        args = [
            "--PROJECT_ID", os.getenv("PROJECT_ID"),
            "--LOCATION_BQ", os.getenv("LOCATION_BQ"),
            "--BUCKET_URI", os.getenv("BUCKET_URI"),
            "--LOCATION", os.getenv("LOCATION"),
        ]
    )

    job.run(sync=True)
    # job = aiplatform.CustomJob.get(
    #     "projects/xxxxxxxx/locations/us-central1/customJobs/xxxxxxxx"
    # )
    # 定义超参数调优配置

    hpt_job = aiplatform.HyperparameterTuningJob(
        display_name="kade-taxi-Hyperparameter-Tuning-job",
        custom_job=job,
        metric_spec={"rmse": "minimize"},  # 要优化的指标
        parameter_spec={
            "alpha": aiplatform.hyperparameter_tuning.DoubleParameterSpec(min=0.01, max=10, scale="log")
        },
        max_trial_count=2,   # 最大尝试次数
        parallel_trial_count=2, # 并行尝试数
    )
    hpt_job.run(sync=True)

    values = []

    for trial in hpt_job.trials:
        print("Trial ID:", trial)
        for p in trial.parameters:
            value = p.value if isinstance(p.value, float) else p.value.number_value
            values.append(value)

    min_value = min(values)
    print("最小的超参数值:", min_value)
    return min_value   # <-- 返回值


def CustomJob(alpha_value: float):
    load_dotenv()
    aiplatform.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION"),staging_bucket=os.getenv("BUCKET_URI"))

    job = aiplatform.CustomJob.from_local_script(
        display_name="kade-taxi-fare-train-job",
        script_path="custom_job_training.py",         # 本地训练脚本
        # staging_bucket="gs://your-bucket-name",  # 中间文件存储桶
        machine_type="n1-standard-4",   # VM 类型
        # https://cloud.google.com/vertex-ai/docs/training/pre-built-containers?hl=zh-cn#scikit-learn
        container_uri = "us-docker.pkg.dev/vertex-ai/training/sklearn-cpu.1-6:latest",
        # container_uri = "us-docker.pkg.dev/vertex-ai/training/tf-cpu.2-2:latest",
        requirements=["pandas", "seaborn", "matplotlib", "python-dotenv", "google-cloud-storage","scikit-learn","db-dtypes"], # 依赖库
        args=[
            "--alpha",  str(alpha_value),
            "--PROJECT_ID", os.getenv("PROJECT_ID"),
            "--LOCATION_BQ", os.getenv("LOCATION_BQ"),
            "--BUCKET_URI", os.getenv("BUCKET_URI"),
            "--LOCATION", os.getenv("LOCATION"),
        ],   # <-- 传入最优 alpha
    )
    job.run(sync=True)


def CustomEvaluationJob():   
    load_dotenv()
    aiplatform.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION"),staging_bucket=os.getenv("BUCKET_URI"))  
    model = aiplatform.Model(os.getenv("EVALUATION_MODEL_NAME"))
    evaluation_job=model.evaluate(
        prediction_type="regression",
        target_field_name="trip_pricing_total",
        bigquery_source_uri=os.getenv("EVALUATION_BIGQUERY_SOURCE_URI"),
        bigquery_destination_output_uri=os.getenv("EVALUATION_BIGQUERY_DESTINATION_OUTPUT_URI"),
        staging_bucket=os.getenv("BUCKET_URI"),
        # service_account="xxxxx-compute@developer.gserviceaccount.com",
        evaluation_pipeline_display_name=os.getenv("EVALUATION_PIPELINE_DISPLAY_NAME"),
        evaluation_metrics_display_name=os.getenv("EVALUATION_METRICS_DISPLAY_NAME"),
        enable_caching=False,
    )
    # 等待评估任务完成（阻塞）
    evaluation_job.wait() 
    print("Evaluation job started:", evaluation_job)


def CustomEvaluationMetricsJob():       
    load_dotenv()
    evaluation = aiplatform.ModelEvaluation(os.getenv("EVALUATION_NAME"))
    # 转换为 dict，方便查看
    metrics = dict(evaluation.metrics)
    print(metrics)


if __name__ == "__main__":
    CustomEvaluationJob()
    # CustomEvaluationMetricsJob()
    # CustomJobHyperparameterTuningJob()
    # CustomJob() 