import csv, json
import random

import vertexai
from google.cloud import storage
from google.oauth2.service_account import Credentials
import re

from google.cloud.aiplatform import initializer as aiplatform_init
from vertexai.language_models import TextEmbeddingModel

google_sa_json = {
        ...
    }

required_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
credentials = Credentials.from_service_account_info(google_sa_json, scopes=required_scopes)

project_id = "wonder-ai1"
region = "us-central1"
vertexai.init(project=project_id, location=region, credentials=credentials)
embedding_model = "text-multilingual-embedding-002"


def convert_jsonl_to_tsv(jsonl_file, output_filename):
    with open(jsonl_file, 'r', encoding="utf8") as f:
        all_data = json.load(f)
        # 从第一条数据中自动获取表头字段
        headers = list(all_data[0].keys())

        # 3. 写入TSV文件
        try:
            with open(output_filename, 'w', newline='', encoding='utf-8') as tsvfile:
                # 创建一个写入器，并指定分隔符为制表符（\t）
                writer = csv.writer(tsvfile, delimiter='\t')

                # 写入表头
                writer.writerow(headers)

                # 遍历所有数据并写入每一行
                for row_dict in all_data:
                    # 按照表头的顺序提取字典中的值
                    row_to_write = [row_dict[h] for h in headers]
                    writer.writerow(row_to_write)

            print(f"数据成功写入到文件: {output_filename}")

        except IOError:
            print(f"写入文件 {output_filename} 时发生错误。")
        except Exception as e:
            print(f"发生未知错误: {e}")


class GCSClient:
    def __init__(self):
        self.bucket_name = "cvinfo"
        storage_client = storage.Client.from_service_account_info(google_sa_json)
        self.storage_client = storage_client
        self.bucket = storage_client.bucket(self.bucket_name)

    def upload(self, source_file_name, destination_blob_name):
        generation_match_precondition = 0
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name, if_generation_match=generation_match_precondition)
        print(
            f"File {source_file_name} uploaded to {destination_blob_name}."
        )

    def list_blobs(self, prefix):
        blobs = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
        print(f"{self.bucket_name}/{prefix} blobs >>>>>>>>>>>>>>:")
        for blob in blobs:
            print(blob.name)


def upload_training_dataset():
    client = GCSClient()
    client.upload("embedding_docs_corpus0819.jsonl", "training/embedding_docs_corpus0819.jsonl")
    client.upload("embedding_queries0819.jsonl", "training/embedding_queries0819.jsonl")
    client.upload("embedding_docs_queries_label0819_train.tsv", "training/embedding_docs_queries_label0819_train.tsv")
    client.upload("embedding_docs_queries_label0819_test.tsv", "training/embedding_docs_queries_label0819_test.tsv")
    client.upload("embedding_docs_queries_label0819_validation.tsv", "training/embedding_docs_queries_label0819_validation.tsv")


def upload_gemini_training_dataset():
    client = GCSClient()
    client.upload("gemini/finetune_data_train1.jsonl", "training/gemini/finetune_data_train1.jsonl")
    client.upload("gemini/finetune_data_validation1.jsonl", "training/gemini/finetune_data_validation1.jsonl")
    client.upload("gemini/finetune_data_test.jsonl", "training/gemini/finetune_data_test.jsonl")


def tune_embedding_model(
    corpus_path: str = "gs://cvinfo/training/embedding_docs_corpus0819.jsonl",
    queries_path: str = "gs://cvinfo/training/embedding_queries0819.jsonl",
    train_label_path: str = "gs://cvinfo/training/embedding_docs_queries_label0819_train.tsv",
    test_label_path: str = "gs://cvinfo/training/embedding_docs_queries_label0819_test.tsv",
    validation_label_path: str = "gs://cvinfo/training/embedding_docs_queries_label0819_validation.tsv",
):  # noqa: ANN201
    """Tune an embedding model using the specified parameters."""
    base_model = TextEmbeddingModel.from_pretrained(embedding_model)
    tuning_job = base_model.tune_model(
        task_type="DEFAULT",
        corpus_data=corpus_path,
        queries_data=queries_path,
        training_data=train_label_path,
        test_data=test_label_path,
        validation_data=validation_label_path,
        batch_size=64,  # The batch size to use for training.
        train_steps=72,  # The number of training steps.
        tuned_model_location=region,
        output_dimensionality=768,  # The dimensionality of the output embeddings.
        learning_rate_multiplier=0.4,  # The multiplier for the learning rate.
    )
    return tuning_job


if __name__ == '__main__':
    client = GCSClient()
    # upload_gemini_training_dataset()
    client.list_blobs("training/gemini/")
    # upload_training_dataset()
    # client.list_blobs("training/")
    # tune_embedding_model()
    # with open("docs_queries_label.jsonl", 'r', encoding="utf8") as f:
    #     train_label_list = json.load(f)
    #     print(train_label_list)
