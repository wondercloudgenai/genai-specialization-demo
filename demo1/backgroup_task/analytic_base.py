import vertexai
from vertexai.generative_models import SafetySetting
from google.oauth2.service_account import Credentials


class AnalyticBase:
    def __init__(self):
        self.model_name = "gemini-1.5-pro-002"
        cren = Credentials.from_service_account_info({...})
        self.project_id = "wonder-ai1"
        self.region = "us-central1"
        self.embedding_model_id = "text-multilingual-embedding-002"
        vertexai.init(project=self.project_id, location=self.region, credentials=cren)
        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.5,
            "top_p": 0.05,
            # "top_p": 0.95,
        }
        self.safety_settings = [
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
        ]


class AnalyticSessionChatManager:
    SESSION = {}

    @staticmethod
    def register_session(session_id, session, owner: str, **kwargs):
        AnalyticSessionChatManager.SESSION[session_id] = {
            "instance": session,
            "owner": owner
        }

    @staticmethod
    def get_session(session_id):
        s = AnalyticSessionChatManager.SESSION
        if session_id in s:
            return AnalyticSessionChatManager.SESSION[session_id]["instance"]
        return None

    @staticmethod
    def delete_session(session_id, owner: str):
        s = AnalyticSessionChatManager.SESSION
        if session_id in s and s[session_id]["owner"] == owner:
            s.pop(session_id)


class AnalyticSessionChatException(Exception):
    def __init__(self, message):
        super().__init__(message)
