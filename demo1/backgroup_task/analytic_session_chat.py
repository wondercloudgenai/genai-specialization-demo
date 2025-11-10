import json
import traceback
import typing
from typing import Iterable

import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationResponse, ChatSession
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from backgroup_task.analytic_base import AnalyticBase, AnalyticSessionChatException
from settings import setting
from tools.redis_cache_template import RedisCacheTemplate
from tools.result import Result

filter_mode_literal = typing.Literal["Pan-Mode", "Context-Mode", "Overlay-Mode"]


class AnalyticChat(AnalyticBase):

    suitability_threshold = 30  # 匹配度阈值，低于该阈值的直接pass
    cv_filter_model_prompt = """
    你是一名资深的人力资源专家。你的任务是根据提供的招聘岗位信息，对即将输入的候选人简历进行专业评估，并筛选出符合条件的简历。请输出一个 JSON 格式的评估报告。
    #### 评估内容：
    1. **匹配度**（suitability）：候选人与岗位要求的匹配度，范围为 0-100。
    2. **适配理由**（reason）：候选人适配岗位的理由，控制在 40 个字以内。
    
    #### 重要前提：
    - 如果简历中存在大量乱码、缺失完整句子或无法获取候选人姓名，则匹配度为 0。
    - 如果简历内容缺失重要信息（如姓名、工作经历、项目经验等），则匹配度也为 0。
    - 对于匹配度低于50%的候选人，直接忽略。
    
    #### 返回格式：
    - 返回一个列表，每个子项包含以下内容：
      - `key`: 简历 ID
      - `suitability`: 候选人与岗位的匹配度
      - `reason`: 适配理由
    """

    def __init__(self, job_info):
        super().__init__()
        self.model_name = "gemini-1.5-pro-002"
        self.job_info = job_info
        self.cv_filter_model = GenerativeModel(
            self.model_name,
            system_instruction=[self.cv_filter_model_prompt, "## 岗位信息如下：\n" + self.job_info]
        )
        self.chat_session: typing.Optional[ChatSession] = None
        self.filter_mode: typing.Literal["Pan-Mode", "Context-Mode", "Overlay-Mode"] = "Pan-Mode"

    def __str__(self):
        return f"AnalyticSessionChat<FilterMode={self.filter_mode}>"

    def filter_cvs_with_mode1(self, special_condition, cvs):
        """
        filter by pan-mode
        pan-mode：Each resume sent to the big model is the batch of resumes passed in at the beginning of the session.
        :param special_condition: the special request condition.
        :return:
        """
        if not special_condition.strip() or len(special_condition.strip()) <= 3:
            return Result.fail("请输入输入有效的内容")
        content = []
        print(f"{self}，特殊要求Content: {special_condition}，待分析简历数量：{len(cvs)}")
        content.append(f"\n岗位特殊要求：\n{special_condition}")
        i = 0
        for item in cvs:
            content.append("\n简历ID: {}, 简历:".format(item["cv_id"]))
            if item["origin"] == "boss":
                content.append(Part.from_text(item["meta_json"]))
            else:
                content.append(Part.from_uri(
                    mime_type="application/pdf",
                    uri=item["gcs_path"]))
            i += 1
        content.append("\n请输出评估结果")
        response_stream = self.cv_filter_model.generate_content(
            content,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            stream=True,
        )
        result = self.get_result_from_response_stream(response_stream)
        return Result.ok(data=result)

    def filter_cvs_with_mode2(self, special_condition, cvs):
        """
        filter by overlay mode
        context-mode：Each filtered resume is filtered again based on the previous filtering results.
        the context kept by a chat-session named 'vertexai.generative_models.ChatSession' which implemented historical
        message saving function
        :param special_condition: the special request condition.
        :return:
        """
        if not special_condition.strip() or len(special_condition.strip()) <= 3:
            return Result.fail("请输入有效的内容")
        try:
            if not self.chat_session:
                chat_session = self.cv_filter_model.start_chat()
                self.chat_session = chat_session
        except Exception as e:
            print(f"创建简历过滤Session异常，{e}")
            raise AnalyticSessionChatException("创建会话失败，服务器异常")
        content = []
        for item in cvs:
            content.append("\n简历ID: {}, 简历:".format(item["cv_id"]))
            content.append("\n简历ID: {}, 简历:".format(item["cv_id"]))
            if item["origin"] == "boss":
                content.append(Part.from_text(item["meta_json"]))
            else:
                content.append(Part.from_uri(
                    mime_type="application/pdf",
                    uri=item["gcs_path"]))
        print(f"{self}，特殊要求Content: {special_condition}")
        content.append(f"\n岗位特殊要求\n{special_condition}")
        content.append("\n请输出评估结果")
        response_stream: Iterable["GenerationResponse"] = self.chat_session.send_message(
            content,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            stream=True
        )
        result = self.get_result_from_response_stream(response_stream)
        return Result.ok(data=result)

    def get_result_from_response_stream(self, response_stream: Iterable["GenerationResponse"]):
        result = ""
        for res in response_stream:
            result += res.text
        print(result)
        # result = response_stream.text
        try:
            result = json.loads(result.replace("```json", "").replace("```", "").strip())
        # except JSONDecodeError:
        #     result = json.loads(result.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            # case1 Expecting property name enclosed in double quotes
            if "Expecting property name enclosed in double quotes" in str(e):
                result = result.replace("\'", "\"")
                result = json.loads(result)
            else:
                print(result)
                print(f"{self} 解析结果异常，{e}")
                traceback.print_exc()
                raise AnalyticSessionChatException("会话结果解析异常")
        # 有可能返回的key值格式有问题，有问题的直接过滤掉
        result = [i for i in result if len(i["key"]) == 32 and i["suitability"] >= self.suitability_threshold]
        for i in result:
            print(i)
        print("===================================")
        return result

    def analyze(self, msg, cvs):
        try:
            if self.filter_mode == "Pan-Mode":
                ret = self.filter_cvs_with_mode1(msg, cvs)
            elif self.filter_mode == "Context-Mode":
                ret = self.filter_cvs_with_mode2(msg, cvs)
            else:
                ret = Result.fail("请求异常")
            return ret
        except AnalyticSessionChatException as e:
            return Result.fail(msg=str(e))
        except Exception as e:
            traceback.print_exc()
            return Result.fail(msg="服务器异常，{}".format(e))

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


if __name__ == "__main__":
    ...

