from google.cloud import aiplatform
from dotenv import load_dotenv
import os
import credentials as cred

def CreateEndpoint():

    load_dotenv()
    ENDPOINT_DISPLAY_NAME = "[your-endpoint-display-name]"  
    # 定义端点显示名称，未设置则用默认值

    if ENDPOINT_DISPLAY_NAME == "[your-endpoint-display-name]":
        ENDPOINT_DISPLAY_NAME = "kade_taxi_fare_prediction_endpoint"  
    # 赋默认端点名称

    aiplatform.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION"),credentials=cred.GetCredentials(),)  
    endpoint = aiplatform.Endpoint.create(
        display_name=ENDPOINT_DISPLAY_NAME, project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION")
    )  
    # 创建 Vertex AI 端点用于模型部署

    # kade_taxi_fare_prediction_endpoint
    print(endpoint.display_name)  
    # projects/xxxxxxx/locations/us-central1/endpoints/xxxxxxx
    print(endpoint.resource_name)  
    # 打印端点名称和资源名
    return endpoint.resource_name
