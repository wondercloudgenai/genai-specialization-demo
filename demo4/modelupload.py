from google.cloud import aiplatform
from google.cloud.aiplatform_v1.types import SampledShapleyAttribution
from google.cloud.aiplatform_v1.types.explanation import ExplanationParameters
import credentials as cred
from dotenv import load_dotenv
import os
from google.cloud.aiplatform_v1.types import explanation_metadata as exp_meta
def ModelUpLoad():
    
    load_dotenv()
    BUCKET_URI=os.getenv("BUCKET_URI")
    BLOB_PATH=os.getenv("BLOB_PATH")
    PROJECT_ID=os.getenv("PROJECT_ID")
    LOCATION=os.getenv("LOCATION")

    MODEL_DISPLAY_NAME = "[your-model-display-name]"  
    # 定义模型显示名称，如果未设置，则用默认名称

    if MODEL_DISPLAY_NAME == "[your-model-display-name]":
        MODEL_DISPLAY_NAME = "kade_taxi_fare_prediction_model"  
    # 默认名称赋值
    ARTIFACT_GCS_PATH = f"{BUCKET_URI}/{BLOB_PATH}"  
    # 模型文件在 Google Cloud Storage 中的路径
    print(ARTIFACT_GCS_PATH)

    exp_metadata = {"inputs": {"Input_feature": {}}, "outputs": {"Predicted_taxi_fare": {}}}  
    # 解释器元数据，定义输入和输出的名称（可任意命名）

    aiplatform.init(project=PROJECT_ID, location=LOCATION,credentials=cred.GetCredentials(),)  
    # 初始化 Vertex AI 客户端，指定项目和区域
    model = aiplatform.Model.upload(
        display_name=MODEL_DISPLAY_NAME,                      # 模型显示名称
        artifact_uri=ARTIFACT_GCS_PATH,                        # 模型文件路径
        # https://cloud.google.com/vertex-ai/docs/supported-frameworks-list#scikit-learn_2
        # us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-0:latest
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-5:latest",  # 使用的预测容器镜像（sklearn CPU版）
        explanation_metadata=exp_metadata,                     # 解释元数据,请求和响应参数
        explanation_parameters=ExplanationParameters(          # 解释参数，使用Sampled Shapley值解释
            sampled_shapley_attribution=SampledShapleyAttribution(path_count=25)
        ),
        upload_request_timeout=7200,  # 设置超时为1800秒（30分钟）
        # serving_container_deployment_timeout=7200,  # 设置容器部署超时为1800秒（30分钟）
        # serving_container_startup_probe_timeout_seconds=7200,  # 设置容器启动探针超时为1800秒（30分钟）
        # serving_container_health_probe_timeout_seconds=7200,  # 设置容器健康探针超时为1800秒（30分钟）
    )
    model.wait()  
    # 等待模型上传完成

    # kade_taxi_fare_prediction_model
    print(model.display_name)  
    # projects/xxxxxx/locations/us-central1/models/xxxxxx
    print(model.resource_name)  
    return model.resource_name
    # 打印模型显示名和资源名

if __name__ == "__main__":
    ModelUpLoad() 