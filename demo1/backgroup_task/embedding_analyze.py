import traceback
from tqdm import tqdm
import time
import vertexai
from google.cloud import aiplatform
from google.oauth2.service_account import Credentials
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances


credentials = Credentials.from_service_account_info({...})
project_id = "wonder-ai1"
region = "us-central1"
# vertexai.init(project=project_id, location=region, credentials=credentials)
embedding_model = "text-multilingual-embedding-002"


class EmbeddingVectorGenerator(object):

    def __init__(self, **kwargs):
        self.credentials_info = kwargs.get("credentials_info")
        self.project_id = kwargs.get("project_id")
        self.region = kwargs.get("region")
        self.embedding_model_endpoint = kwargs.get("endpoint_id")
        credentials = Credentials.from_service_account_info(self.credentials_info)
        vertexai.init(project=self.project_id, location=self.region, credentials=credentials)

    def tuning_embedding_text(self, texts):
        endpoint_name = f"projects/{self.project_id}/locations/{self.region}/endpoints/{self.embedding_model_endpoint}"
        endpoint = aiplatform.Endpoint(endpoint_name=endpoint_name)
        instances = [
            {"content": text, "task_type": "DEFAULT", "title": ""} for text in texts
        ]

        try:
            response = endpoint.predict(instances=instances)
            # 提取嵌入向量
            return response.predictions
        except Exception as e:
            traceback.print_exc()
            print(f"调用端点时发生错误: {e}")
            return None

def embedding_text(msg):
    try:
        model = TextEmbeddingModel.from_pretrained(embedding_model)
        inputs = [TextEmbeddingInput(msg, "RETRIEVAL_DOCUMENT")]
        embeddings = model.get_embeddings(texts=inputs, output_dimensionality=768)
        return embeddings[0].values
    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return None


def tuning_embedding_text(msg, endpoint_id="1300452875310202880"):
    endpoint = aiplatform.Endpoint(endpoint_name=f"projects/{project_id}/locations/{region}/endpoints/{endpoint_id}")
    instances = [
        {"content": msg, "task_type": "RETRIEVAL_DOCUMENT", "title": msg}
    ]

    try:
        response = endpoint.predict(instances=instances)
        # 提取嵌入向量
        embeddings = response.predictions[0]
        return embeddings
    except Exception as e:
        traceback.print_exc()
        print(f"调用端点时发生错误: {e}")
        return None


def cos_similarity(a, b):
    """计算两个向量的余弦相似度，处理文本 Embedding 时最常用、也最推荐的方法， 数值范围：-1 到 1，
    1: 向量方向完全相同（语义极度相似）。
    0: 向量方向互相垂直（语义上不相关）。
    -1: 向量方向完全相反（语义上是反义词，例如“好”和“坏”）。
    常用于文本语义搜索、RAG、文档分类
    """
    vector_a = np.array(a)
    vector_b = np.array(b)
    cos_sim = cosine_similarity(vector_a.reshape(1, -1), vector_b.reshape(1, -1))
    return cos_sim


def euclidean_distance(a, b):
    """
    计算两个向量欧几里得距离, 即几何学中的直线距离，而在向量中，用于衡量的是两个向量的终点在空间中的直线距离，
    数值范围：0 到 +∞
    0: 两个向量完全相同。
    数值越大: 表示两个向量在空间中相距越远，语义上越不相似。
    常用于图像相似度、某些聚类算法
    """
    vector_a = np.array(a)
    vector_b = np.array(b)
    return euclidean_distances(vector_a.reshape(1, -1), vector_b.reshape(1, -1))[0][0]
    # return np.linalg.norm(vector_a - vector_b)


def dot_product(a, b):
    """计算两个向量点积,当向量被“归一化”后，它和余弦相似度是等价的，因此在大型向量数据库中非常流行
    它同时考虑了向量的方向和大小。
    数值范围：-∞ 到 +∞
    值越大: 通常表示越相似。
    高效的语义搜索 (需配合向量归一化)
    """
    # 归一化向量 (L2 Normalization)
    vector_a = np.array(a)
    vector_b = np.array(b)
    norm_a = vector_a / np.linalg.norm(vector_a)
    norm_b = vector_b / np.linalg.norm(vector_b)
    return np.dot(norm_a, norm_b)


def normalize_vector(vector):
    """对输入的numpy向量进行L2范数归一化"""
    norm = np.linalg.norm(vector)
    if norm == 0:
        # 如果是零向量，无法归一化，直接返回原向量
        return vector
    return vector / norm


def main():
    generator = EmbeddingVectorGenerator(
        project_id="wonder-ai1",
        credentials_info={
            ...
        },
        region="us-central1",
        endpoint_id="1558099236023697408"
    )
    # texts = ["我在数据分析方面有很强的技能，能够利用 Excel 和 SQL 进行数据建模和报表制作。", "我没有任何数据分析相关的经验"]
    texts = ["主导跨部门项目并提前两周完成，获得客户书面表扬", "通过数据分析优化广告投放，使获客成本降低25%", "管理10人团队，实施敏捷开发流程，提升交付效率30%", "撰写5篇行业白皮书，为公司官网带来超过2万次专业访问", "设计全新库存管理系统，将周转效率提升40%", "使用Python自动化日常报表，每周节省团队8小时工时", "维护关键客户关系，实现年度续约率98%", "负责新产品市场推广，首季度实现销售额超目标15%", "精通Figma和Adobe Creative Suite，完成3次品牌视觉升级", "流利使用英语和日语，成功协调跨国团队完成产品本地化"]
    vectors = generator.tuning_embedding_text(texts)
    for vector in vectors:
        print(f"Vector: {vector[:15]}...")


if __name__ == "__main__":
    main()
    # text1, text2, text3 = (,
    #                        "我精通 Excel 和 SQL，擅长数据分析、数据建模和生成数据报告。",
    #                        "我没有任何数据分析相关的经验")
    # vector1, vector2, vector3 = embedding_text(text1), embedding_text(text2), embedding_text(text3)
    # print(f"Text1: {text1}\nText2: {text2}\nText3: {text3}")
    # print("-----------------------------------------------")
    # print(f"Vector1: {vector1[:5]}...\nVector2: {vector2[:5]}...\nVector3: {vector3[:5]}...")
    # print(f"Text1<>Text2 余弦相似度：{cos_similarity(vector1, vector2)[0][0]:.4f}")
    # print(f"Text1<>Text2 欧几里得距离：{euclidean_distance(vector1, vector2):.4f}")
    # print(f"Text1<>Text2 点积：{dot_product(vector1, vector2):.4f}")
    # print(f"Text1<>Text3 余弦相似度：{cos_similarity(vector1, vector3)[0][0]:.4f}")
    # print(f"Text1<>Text3 欧几里得距离：{euclidean_distance(vector1, vector3):.4f}")
    # print(f"Text1<>Text3 点积：{dot_product(vector1, vector3):.4f}")
    # print(f"Text2<>Text3 余弦相似度：{cos_similarity(vector2, vector3)[0][0]:.4f}")
    # print(f"Text2<>Text3 欧几里得距离：{euclidean_distance(vector2, vector3):.4f}")
    # print(f"Text2<>Text3 点积：{dot_product(vector2, vector3):.4f}")
    #
    # print("===========================================================")
    # text1, text2, text3 = ("我在数据分析方面有很强的技能，能够利用 Excel 和 SQL 进行数据建模和报表制作。",
    #                        "我精通 Excel 和 SQL，擅长数据分析、数据建模和生成数据报告。",
    #                        "I have no specific or outstanding skills in data analysis, and l never use Excel or SQL ago.")
    # vector1, vector2, vector3 = tuning_embedding_text(text1), tuning_embedding_text(text2), tuning_embedding_text(text3)
    # print(f"Text1: {text1}\nText2: {text2}\nText3: {text3}")
    # print("-----------------------------------------------")
    # print(f"Vector1: {vector1[:5]}...\nVector2: {vector2[:5]}...\nVector3: {vector3[:5]}...")
    # print(f"Text1<>Text2 余弦相似度：{cos_similarity(vector1, vector2)[0][0]:.4f}")
    # print(f"Text1<>Text2 欧几里得距离：{euclidean_distance(vector1, vector2):.4f}")
    # print(f"Text1<>Text2 点积：{dot_product(vector1, vector2):.4f}")
    # print(f"Text1<>Text3 余弦相似度：{cos_similarity(vector1, vector3)[0][0]:.4f}")
    # print(f"Text1<>Text3 欧几里得距离：{euclidean_distance(vector1, vector3):.4f}")
    # print(f"Text1<>Text3 点积：{dot_product(vector1, vector3):.4f}")
    # print(f"Text2<>Text3 余弦相似度：{cos_similarity(vector2, vector3)[0][0]:.4f}")
    # print(f"Text2<>Text3 欧几里得距离：{euclidean_distance(vector2, vector3):.4f}")
    # print(f"Text2<>Text3 点积：{dot_product(vector2, vector3):.4f}")