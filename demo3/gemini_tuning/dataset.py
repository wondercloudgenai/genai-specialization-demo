import json
import re
import argparse
from pathlib import Path
from google.cloud import storage
from tools.log_utils import get_logger

logger = get_logger(__name__)


class GcsClient:
    def __init__(self):
        self.client = storage.Client()

    def upload_blob(self, bucket_name: str, source_file: str, destination_blob: str) -> str:
        try:
            bucket = self.client.bucket(bucket_name)
            destination_blob = f"tuning_job/{destination_blob}"
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(source_file)
            uri = f"gs://{bucket_name}/{destination_blob}"
            logger.info(f"文件 {source_file} 已上传到 {uri}")
            return uri
        except Exception as e:
            logger.exception(f"GCS 上传失败: {e}")
            raise

    def download_blob(self, bucket_name: str, source_blob: str, destination_file: str):
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(source_blob)
            blob.download_to_filename(destination_file)
            logger.info(f"GCS 文件 {source_blob} 已下载到 {destination_file}")
        except Exception as e:
            logger.exception(f"GCS 下载失败: {e}")
            raise


class DatasetPreparer:
    @staticmethod
    def sanitize_text(text: str) -> str:
        """对输入文本做脱敏处理"""
        # user_id （N开头10位数字）
        text = re.sub(r'\bN\d{10}\b', '[USER_ID]', text)
        # 手机号 (国内 11 位) -> 替换成 [PHONE]
        text = re.sub(r'\b1[3-9]\d{9}\b', '[PHONE]', text)
        # 邮箱 -> [EMAIL]
        text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
        # 身份证号 (15/18 位) -> [ID]
        text = re.sub(r'\b\d{15}(\d{2}[0-9Xx])?\b', '[ID]', text)
        # 固定电话（带区号，如 010-12345678 或 0755-1234567）
        text = re.sub(r'\b0\d{2,3}-?\d{7,8}\b', '[TEL]', text)
        return text

    @staticmethod
    def parse_faq_to_jsonl(input_file: str, output_file: str) -> str:
        data = []
        try:
            content = Path(input_file).read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"源文件未找到: {input_file}")
            raise

        faq_entries = re.split(r'Q\d+：', content)
        faq_entries = [entry.strip() for entry in faq_entries if entry.strip()]
        logger.info(f"解析到 {len(faq_entries)} 条 FAQ")

        for i, entry in enumerate(faq_entries, start=1):
            parts = re.split(r'\nA：', entry, maxsplit=1)
            if len(parts) != 2:
                logger.warning(f"第 {i} 条 FAQ 格式不符合，跳过: {entry[:30]}...")
                continue

            question, answer = parts[0].strip(), parts[1].strip()

            question = DatasetPreparer.sanitize_text(question)
            answer = DatasetPreparer.sanitize_text(answer)
            item = {
                "contents": [
                    {"role": "user", "parts": [{"text": question}]},
                    {"role": "model", "parts": [{"text": answer}]}
                ]
            }
            logger.debug(f"第 {i} 条 -> Q: {question[:10]}..., A 长度: {len(answer)}")
            data.append(item)

        with open(output_file, "w", encoding="utf-8") as f:
            for entry in data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(f"已生成 JSONL 文件: {output_file}, 共 {len(data)} 条")
        return output_file


def main():
    ### 如果有数据集要处理可以使用此模块
    parser = argparse.ArgumentParser(description="处理 FAQ 数据集并上传 GCS")
    parser.add_argument("--source_data", type=str, required=True, help="源数据文件路径")
    parser.add_argument("--output_file", type=str, default="faq.jsonl", help="生成的 JSONL 文件名")
    parser.add_argument("--bucket_name", type=str, required=True, help="GCS bucket 名称")

    args = parser.parse_args()
    preparer = DatasetPreparer()
    jsonl_file = preparer.parse_faq_to_jsonl(args.source_data, args.output_file)

    logger.info(f"生成的 JSONL 文件: {jsonl_file}")
    gcs = GcsClient()
    gcs_uri = gcs.upload_blob(args.bucket_name, jsonl_file, args.output_file)

    logger.info(f"上传成功，GCS 路径: {gcs_uri}")


if __name__ == "__main__":
    main()
