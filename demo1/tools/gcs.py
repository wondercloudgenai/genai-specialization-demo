import mimetypes

from google.cloud import storage
from settings import setting
import io


class GCSClient:
    def __init__(self):
        storage_client = storage.Client(project=setting.google_sa_json["project_id"])
        storage_client = storage_client.from_service_account_info(setting.google_sa_json)
        self.bucket = storage_client.bucket(setting.bucket_name)

    async def upload_cvinfo(self, file_obj, destination_blob_name):
        content = await file_obj.read()
        file_obj = io.BytesIO()
        file_obj.write(content)
        file_obj.seek(0)
        blob = self.bucket.blob(destination_blob_name)
        try:
            blob.upload_from_file(file_obj, content_type="application/pdf")
        except Exception as e:
            print(e)
            return False, "".format(e)

        return True, "upload"

    async def upload(self, file_obj, destination_blob_name):
        content = await file_obj.read()
        file_obj = io.BytesIO()
        file_obj.write(content)
        file_obj.seek(0)
        blob = self.bucket.blob(destination_blob_name)
        try:
            blob.upload_from_file(file_obj, content_type=self.get_mime_type(destination_blob_name))
        except Exception as e:
            print(e)
            return False, "".format(e)

        return True, "upload"

    def download(self, file_name):
        blob = self.bucket.blob(file_name)
        contents = blob.download_as_bytes()
        file_obj = io.BytesIO()
        file_obj.write(contents)
        file_obj.seek(0)
        return file_obj

    def get_filename_from_gcs_path(self, gcs_path):
        "gs://cvinfo/002e2e3286174c9dbbc63b00524654ac/fd5a666e0dd74e579174d2153515d6f3.pdf"
        return gcs_path.replace(f"gs://{self.bucket.name}/", "")

    @staticmethod
    def get_mime_type(file_name):
        # 使用 guess_type 方法根据文件名获取 MIME 类型
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or 'application/octet-stream'  # 默认返回 binary 数据类型
