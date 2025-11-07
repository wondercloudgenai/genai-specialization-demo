from google.cloud import aiplatform
from dotenv import load_dotenv
import os
import credentials as cred
import modelupload as mu
import createEndpoint as ce
def DeployEndpoint(
    modelName: str, endpoint_id: str
):
    load_dotenv()
    aiplatform.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION"),credentials=cred.GetCredentials(),)  
    DEPLOYED_MODEL_NAME = "[your-deployed-model-name]"  
    # 定义部署模型的名称，未设置则用默认

    if DEPLOYED_MODEL_NAME == "[your-deployed-model-name]":
        DEPLOYED_MODEL_NAME = "taxi_fare_prediction_deployment"  
    # 赋默认部署名

    MACHINE_TYPE = "n1-standard-4"  
    # 设定部署模型的机器类型（虚拟机规格）
    # 获取 endpoint 对象
    model = aiplatform.Model(modelName)
    endpoint = aiplatform.Endpoint(endpoint_id)
    model.deploy(
        endpoint=endpoint,                                     # 部署到指定端点
        deployed_model_display_name=DEPLOYED_MODEL_NAME,      # 部署模型名称
        machine_type=MACHINE_TYPE,         
        deploy_request_timeout=7200,  # 设置超时为1800秒（30分钟）                    # 使用的机器类型
        traffic_split={"0": 100},
        # disable_container_logging=True,
    )  
    model.wait()  
    # 等待模型部署完成

    print(model.display_name)  
    print(model.resource_name)  
    # 再次打印模型名称和资源名

    endpoint.list_models()  
# 列出端点上已部署的模型列表

if __name__ == "__main__":
    # model_resource_name = mu.ModelUpLoad()
    # endpoint_resource_name = ce.CreateEndpoint()
    model_resource_name= "projects/xxxxxxx/locations/us-central1/models/xxxxxxx"
    endpoint_resource_name = "projects/xxxxxxx/locations/us-central1/endpoints/xxxxxxx"
    DeployEndpoint(model_resource_name,endpoint_resource_name)
    # DeployEndpoint("projects/xxxxxxx/locations/us-central1/models/xxxxxxx","projects/xxxxxxx/locations/us-central1/endpoints/xxxxxxx")