from google.cloud import storage
from dotenv import load_dotenv
# import dataset as ds
import credentials as cred
import os


def UploadGCS():
    # 1. 加载 .env 文件
    load_dotenv()

    FILE_NAME = os.getenv("FILE_NAME")        # 模型文件名
    BLOB_PATH = os.getenv("BLOB_PATH")                      # 云存储路径前缀
    BLOB_NAME = BLOB_PATH + FILE_NAME   
    # 云存储完整文件路径

    bucket = storage.Client(
        project=os.getenv("PROJECT_ID"),
        credentials=cred.GetCredentials(),
    ).bucket(os.getenv("BUCKET_URI_NAME"))            # 连接云存储桶（去除 "gs://"）
    blob = bucket.blob(BLOB_NAME)                               # 创建存储对象
    blob.upload_from_filename(FILE_NAME)                        # 上传本地模型文件到云存储
    print("模型上传成功！")


if __name__ == "__main__": 
    UploadGCS()