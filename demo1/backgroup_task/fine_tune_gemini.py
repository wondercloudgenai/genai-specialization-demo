import json
import traceback
import warnings
from json import JSONDecodeError

import vertexai
from google.oauth2.service_account import Credentials
from vertexai.generative_models import GenerativeModel, SafetySetting, Part


warnings.filterwarnings("ignore", category=UserWarning)
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.5,
    "top_p": 0.9,
    # "top_p": 0.95,
}
safety_settings = [
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

prompt = """角色：招聘专员，
    # 任务： 根据招聘的岗位信息，对即将输入的候选人的简历（主要有工作经历，项目经验、学校专业等）进行专业的评估，输出一个json的评估报告
    # 评估内容：
    重要前提： 评估简历存在大量的乱码、或者没有完整语句、或者无法获取到候选人的名称，则该候选人的匹配度为0
    候选人和岗位的匹配度， 输出百分数, 对应的key为suitability，范围为0-100
    获选人适配岗位的理由： 输出字符串, 对应的key为reason
    候选人在岗位上优势： 输出列表，对应的key为advantages
    候选人在岗位的劣势： 输出列表， 对应的key为disadvantages
    如果简历内容出现大量缺失(名字等个人信息、工作过的公司、工作经历、项目经验、等)， 则该候选人的匹配度为0
    如果简历内容无法识别出候选人名字， 则该候选人的匹配度为0
    简历提供的信息不完整信息（如名称、公司名称、岗位名称、工作内容等）， 则该候选人的匹配度为0
    返回结果的数据格式为列表，子项内容为：{"key"：简历id, "result": 评估结果}
    # 输出示例：
    {"key": "", "result": {"suitability": 50, "reason": "", "advantages": [], "disadvantages": []}}
    """


class TuneGeminiGenerator(object):

    def __init__(self, **kwargs):
        self.credentials_info = kwargs.get("credentials_info")
        self.project_id = kwargs.get("project_id")
        self.region = kwargs.get("region")
        self.tune_model_endpoint = f"projects/{self.project_id}/locations/{self.region}/endpoints/{kwargs.get('endpoint_id')}"
        credentials = Credentials.from_service_account_info(self.credentials_info)
        vertexai.init(project=self.project_id, location=self.region, credentials=credentials)

    def demo_show(self, city_name):
        prompt = f"你是一个导游。"
        generative_model = GenerativeModel(
            self.tune_model_endpoint,
            system_instruction=[prompt]
        )
        print("=" * 30 + "Test" + "=" * 30)
        content = [f"请告诉我{city_name}有哪些著名的名胜古迹。"]
        responses = generative_model.generate_content(
            content,
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=False,
        )
        data = responses.candidates[0].content.parts[0].text
        print(data)
        print("=" * 30 + "Test" + "=" * 30)

    def analyze_cv(self, job_info, cvs):
        generative_model = GenerativeModel(
            self.tune_model_endpoint,
            system_instruction=[prompt]
        )
        result = []
        content = ["岗位信息\n{}".format(job_info)]
        for item in cvs:
            content.append("\nID: {}, 简历:".format(item["cv_id"]))
            content.append(Part.from_uri(mime_type="application/pdf", uri=item["save_path"]))
        content.append("""\n请输出评估结果""")

        try:
            print(f"Model name: {self.tune_model_endpoint}，开始分析简历匹配度，共分析简历{len(cvs)}份")
            responses = generative_model.generate_content(
                content,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )
            data = responses.candidates[0].content.parts[0].text
            print(f"Response Text:", data)
            try:
                analytic_result = json.loads(data.replace("```json", "").replace("```", "").strip())
                result.append(analytic_result)
            except JSONDecodeError:
                print("json数据结果解析异常")
                return False
            for i in result:
                print(f">>>>>: {i}")
            return result
        except Exception as e:
            print(traceback.format_exc())
            print(f"分析异常：{e}")
            return result


if __name__ == "__main__":
    ...