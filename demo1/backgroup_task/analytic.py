import mimetypes
import re
import traceback
from json import JSONDecodeError
from vertexai.generative_models import GenerativeModel, Part
import json

from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from backgroup_task.analytic_base import AnalyticBase


class Analytic(AnalyticBase):
    jd_model_prompt = """
    #角色：您是专门负责招聘的专员，公司会提供岗位名称、岗位要求、岗位工作内容、岗位职责给您，您需要将为岗位做对应的总结信息并且对岗位信息总结成一句话，以便于进行embedding分析, 下方会有一则招聘内容，请帮忙进行总结招聘信息、一句话总结（体现出岗位的技能要求、职责要求等关键字）
    #前提：
        如果提供的岗位内容、岗位要求等不全，需要根据岗位名称自动补全;
        ---split---不允许删除，我需要用它做分割使用
    总结模版为：
    岗位信息总结
    岗位名称: [自动填充]
    岗位类型: [自动填充]（如全职、兼职、实习等）
    工作内容: [自动填充]（描述该岗位的主要工作任务和职责）
    岗位要求: [自动填充]（应聘者需要具备的技能、经验和学历等）
    优先考虑: [自动填充]（对某些特定技能或经验的优先考虑）
    总结: [自动填充]（对岗位的简要描述或总结）
    
    ---split---
    [结尾]总结信息模板（以json格式显示）：
    keyword_summary:岗位总结，体现出岗位的技能要求、职责要求等关键字
    """

    cv_model_prompt = """角色：招聘专员，
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

    jd_resolve_prompt_1 = """角色：你是一名招聘专员，负责整理公司的招聘信息，汇总成统一格式的招聘信息
    需求：各个部门会按自己的喜好提供各种招聘信息，根据公司信息等、解读招聘信息，并根据输出格式要求输出
    步骤:
    1. 解析出岗位名称
    2. 解析出岗位区域
    3. 解析出岗位职责
    4. 解析出工作内容
    5. 解析出工作要求

    注意：
    1. 不要修改岗位名称、岗位区域
    2. 为了更精准招聘到人才、需要丰富和纠正岗位职责、工作内容、工作要求
    3.岗位职责、工作内容和工作要求、 描述的内容不是一样；职责： 岗位需要人员担负的责任；工作内容：岗位需要人员做什么事情；工作要求：企业对这个岗位的工作要求

    输入：
    岗位信息
    输出信息及格式：
    {
    	"name": "",
    	"location": "",
    	"work_response": "",
    	"work_content: "",
    	"work_request": "",
    	"reason": ""
    }
    输入字段解释：
    name： 岗位名称
    location： 岗位区域
    work_response： 岗位职责
    work_content: 工作内容
    work_request: 工作要求
    reason: 解读过程说明

    注意： 输出必须是Json"""

    jd_resolve_prompt_2 = """角色：你是一名招聘专员，负责整理公司的招聘信息，汇总成统一格式的招聘信息
        需求：用人部门会提供招聘岗位描述信息或招聘岗位关键字，根据提供的信息解读招聘信息，并根据输出格式要求输出
        步骤:
        1. 解析出岗位名称
        2. 解析出岗位关键词
        3. 解析出岗位职责
        4. 解析出工作要求

        注意：
        1. 如果输入只有简单的关键字，只需要解析出岗位名称和关键词即可
        2. 为了更精准招聘到人才、需要丰富和纠正岗位职责、工作内容、工作要求
        3. 职责： 岗位需要人员担负的责任；工作要求：企业对这个岗位的工作要求

        输入：
        岗位信息或者岗位关键字
        输出信息及格式：
        {
        	"name": "",
        	"keywords: "",
        	"work_response": "",
        	"work_request": "",
        	"reason": ""
        }
        输入字段解释：
        name： 岗位名称
        keywords： 岗位关键词
        work_response： 岗位职责
        work_request: 工作要求
        reason: 解读过程说明

        注意： 输出必须是Json"""

    cv_abstract_prompt = """
    你是一名智能简历分析助手。请根据我上传的简历文件进行以下操作：
    
    1. **归纳总结**：提炼简历中的关键信息，包括如下信息：
        - 年龄（可选）,对应key为age
        - 工作年限（可选，可根据毕业时间或其他信息推断）,对应key为work_years
        - 简历所在省市,不用精确到区镇（可选）,对应key为zone
        - 毕业院校（可选，以最后一段教育经历为准）,对应key为graduation
        - 学历（可选，专科、全日制本科、研究生等）,对应key为educational
        - 手机联系方式（可选）,对应key为phone
        - 邮箱联系方式（可选）,对应key为email
    2. **提取关键字**：从简历中提取3-5个最具代表性的关键字，反映候选人的核心能力和专业领域。
    
    请以JSON格式输出结果，包含以下字段：
    返回一个列表
    - `key`: 简历的id。
    - `info`: 提炼简历中的关键信息。
    - `keywords`: 一个包含3-5个关键字的数组，代表候选人的主要技能和相关行业背景
    
    **示例**：
    [{"key": "xxxxxx", "info": {"age": 18, "work_years": 3.5, "educational": "全日制本科", "graduation": "xx大学", 
    "phone": "17712373267", "email": "aaa@163.com"}, "keywords": ["xx1", "xx2", "xx3"]}, ...]
    """

    sentence_abstract_prompt = """
    # 角色：你是一名智能助手。我将给你提供一段话，请将这段话的关键字提取出来，提取成可以供embedding模型使用的一句话总结
    # 输出格式：
    请以JSON格式输出结果，包含以下字段：
    {"summary": "xxxxxxxxxxxx"}
    """

    split_pdf_prompt = """
    你是一个文档阅读助手，我将给你提供一份简历，你的任务是将简历中的内容进行切分，切分后的句子我将用embedding模型进行向量计算。
    输出为json格式，输出结果为列表。
    结果中去掉声明版权相关的句子
    """

    interview_eva_prompt = """
    你是一名专业的面试官，我将给你一个面试评价模板，你的任务是根据面试者的面试内容和简历面试模板，生成一份面试评价报告，并以markdown格式输出
    """

    def __init__(self):
        super().__init__()
        self.jd_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.jd_model_prompt]
        )
        self.cv_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.cv_model_prompt]
        )
        self.jd_resolve_model1 = GenerativeModel(
            self.model_name,
            system_instruction=[self.jd_resolve_prompt_1]
        )
        self.jd_resolve_model2 = GenerativeModel(
            self.model_name,
            system_instruction=[self.jd_resolve_prompt_2]
        )
        self.cv_abstract_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.cv_abstract_prompt]
        )

        self.sentence_summary_abstract_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.sentence_abstract_prompt]
        )

        self.split_pdf_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.split_pdf_prompt]
        )

        self.interview_eva_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.interview_eva_prompt]
        )

    @staticmethod
    def get_mime_type(file_name):
        # 使用 guess_type 方法根据文件名获取 MIME 类型
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or 'application/octet-stream'  # 默认返回 binary 数据类型

    def analytic_jd(self, jd_info):
        print("start")
        loop = 3
        for retry in range(loop):
            try:
                responses = self.jd_model.generate_content(
                    [jd_info],
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                    stream=False,
                )
                result = responses.candidates[0].content.parts[0].text
                print(result)
                t = result.split("---split---")
                job_summary = t[0]
                keyword_summary = t[1].split("```json")[1].split("```")[0]
                keyword_summary = json.loads(keyword_summary)["keyword_summary"]
                return {
                    "keyword_summary": keyword_summary,
                    "job_summary": job_summary,
                }
            except Exception as e:
                print(f"分析JD异常，即将重试，{e}")

    def analytic_cv(self, job_info, cvs):
        content = ["岗位信息\n{}".format(job_info)]
        for item in cvs:
            origin = item["origin"]
            if origin == "boss":
                content.append("\nID: {}, 简历:".format(item["cv_id"]))
                content.append(Part.from_text(item["meta_json"]))
            else:
                content.append("\nID: {}, 简历:".format(item["cv_id"]))
                content.append(Part.from_uri(
                    mime_type="application/pdf",
                    uri=item["gcs_path"]))

        content.append("""\n请输出评估结果""")
        print(f"获取到cvs数量：{len(cvs)}")

        try:
            responses = self.cv_model.generate_content(
                content,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=False,
            )
            # print(responses)
            data = responses.candidates[0].content.parts[0].text
            try:
                analytic_result = json.loads(data.replace("```json", "").replace("```", "").strip())
            # 有可能超出max_token，导致responses.candidates[0].content.parts[0].text不是一个完整的json字符串，此时使用正则来获取有效的结果
            except JSONDecodeError:
                analytic_result = []
                for i in re.findall(r"\{\s+\"key\".*?\"result\":\s+\{.*?}\s+}", data, re.DOTALL):
                    analytic_result.append(json.loads(i))
            # print(analytic_result)
            print(f"解析分析结果成功，数量：{len(analytic_result)}")
            if len(analytic_result) == 0:
                print(f"解析分析结果成功，数量：0, ResultText: {data}")
            result = []
            for item in analytic_result:
                t_ = item["result"]
                cv_id = item["key"]
                t_["cv_id"] = cv_id
                if re.match(r"^\w+-\w+-\w+-\w+-\w+$", cv_id) or re.match(r"^\w{32}$", cv_id):
                    result.append(t_)
            # print("=========================================")
            print(f"Get analyze result count: {len(result)}")
            return result
        except Exception as e:
            print(traceback.format_exc())
            print(f"分析简历发生异常：{e}")
            return []

    def resolve_jd(self, jd_info: str = None, jd_file_stream: bytes = None, index=1):
        content = ["请分析一下岗位信息:\n"]
        if jd_info:
            content.append(jd_info)
        else:
            content.append(Part.from_data(data=jd_file_stream, mime_type="application/pdf"))
        if index == 1:
            model = self.jd_resolve_model1
        else:
            model = self.jd_resolve_model2
        response = model.generate_content(
            content,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            stream=False,
        )
        result = response.candidates[0].content.parts[0].text
        result = json.loads(result.replace("```json", "").replace("```", "").strip())
        return result

    def embedding_texts(self, texts):
        try:
            model = TextEmbeddingModel.from_pretrained(self.embedding_model_id)
            inputs = [TextEmbeddingInput(text, "RETRIEVAL_QUERY") for text in texts]
            embeddings = model.get_embeddings(texts=inputs, output_dimensionality=768)
            return [embedding.values for embedding in embeddings]
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            return []

    def embedding_text(self, msg):
        try:
            model = TextEmbeddingModel.from_pretrained(self.embedding_model_id)
            inputs = [TextEmbeddingInput(msg, "RETRIEVAL_QUERY")]
            embeddings = model.get_embeddings(texts=inputs, output_dimensionality=768)
            return embeddings[0].values
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            return None

    def cv_abstract(self, cvs):
        content = []
        for item in cvs:
            origin = item["origin"]
            if origin == "boss":
                content.append("\nID: {}, 简历:".format(item["cv_id"]))
                content.append(Part.from_text(item["meta_json"]))
            else:
                content.append("\nID: {}, 简历:".format(item["cv_id"]))
                content.append(Part.from_uri(
                    mime_type="application/pdf",
                    uri=item["gcs_path"]))
        content.append("请输出结果")
        try:
            response = self.cv_abstract_model.generate_content(
                content,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=False,
            )
            result = response.candidates[0].content.parts[0].text
            result = json.loads(result.replace("```json", "").replace("```", "").strip())
            return result
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            return None

    def sentence_summary_abstract(self, sentence):
        content = ["句子\n", sentence, "请输出结果"]
        try:
            response = self.sentence_summary_abstract_model.generate_content(
                content,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=False,
            )
            result = response.candidates[0].content.parts[0].text
            result = json.loads(result.replace("```json", "").replace("```", "").strip())
            return result
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            return None

    def split_pdf(self, gcs_path: str):
        content = ["简历:", Part.from_uri(mime_type="application/pdf", uri=gcs_path), "\n请输出结果"]
        try:
            response = self.split_pdf_model.generate_content(
                content,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=False,
            )
            result = response.candidates[0].content.parts[0].text
            result = json.loads(result.replace("```json", "").replace("```", "").strip())
            return result
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            return None

    def interview_evaluation(self, template_save_path, content_save_path):
        content = ["面评模板:", Part.from_uri(mime_type=self.get_mime_type(template_save_path), uri=template_save_path),
                   "面试内容:", Part.from_uri(mime_type=self.get_mime_type(content_save_path), uri=content_save_path), "\n请输出结果"]
        try:
            response = self.interview_eva_model.generate_content(
                content,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
            )
            result = response.candidates[0].content.parts[0].text
            return result
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            return None


if __name__ == "__main__":
    ...