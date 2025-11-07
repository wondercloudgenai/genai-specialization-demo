from google.oauth2 import service_account
import os
from dotenv import load_dotenv


def GetCredentials():
    load_dotenv()
    service_account_key_path=os.getenv("SERVICE_ACCOUNT_KEY_PATH")
    credentials = service_account.Credentials.from_service_account_file(
    service_account_key_path,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
    return credentials

if __name__ == "__main__":
    # CreateImportDataset(bqclient,os.getenv("PROJECT_ID"), os.getenv("DATASET_ID"), os.getenv("TABLE_ID"))
   GetCredentials()     