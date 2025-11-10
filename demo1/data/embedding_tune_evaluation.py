import json
import traceback

import numpy as np
import vertexai
from google.cloud import aiplatform
from google.oauth2.service_account import Credentials
from sklearn.metrics import ndcg_score
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

credentials = Credentials.from_service_account_info({
    ...
})
project_id = "wonder-ai1"
region = "us-central1"
vertexai.init(project=project_id, location=region, credentials=credentials)
embedding_model = "text-multilingual-embedding-002"


def embedding_text(texts):
    try:
        model = TextEmbeddingModel.from_pretrained(embedding_model)
        inputs = [TextEmbeddingInput(text, "DEFAULT") for text in texts]
        embeddings = model.get_embeddings(texts=inputs, output_dimensionality=768)
        return [i.values for i in embeddings]
    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return None


def tuning_embedding_text(texts, endpoint_id="1300452875310202880"):
    endpoint = aiplatform.Endpoint(endpoint_name=f"projects/{project_id}/locations/{region}/endpoints/{endpoint_id}")
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


def preprocess_labels(flat_labels_list: list) -> dict:
    """
    将扁平的标签列表转换为嵌套的字典格式。

    Args:
        flat_labels_list: 您提供的 [{"query-id": ..., "corpus-id": ..., "score": ...}] 格式的列表。

    Returns:
        一个嵌套字典，格式为 {query_id: {corpus_id: score}}。
    """
    nested_labels = {}
    for item in flat_labels_list:
        query_id = item["query-id"]
        corpus_id = item["corpus-id"]
        score = item["score"]

        if query_id not in nested_labels:
            nested_labels[query_id] = {}
        nested_labels[query_id][corpus_id] = score

    return nested_labels


def evaluate_model_v1(
        test_queries: dict,
        test_corpus: dict,
        labels: dict,
        model_f: int = 1
) -> float:
    """
    在测试集上高效评估一个Embedding模型的NDCG@10分数。

    Args:
        model_f: 要评估的Vertex AI Embedding模型选择，为1时候选择Base Model，为2时候用优化后的Model。
        test_queries: {query_id: text} 的字典。
        test_corpus: {doc_id: text} 的字典。
        labels: 【预处理后】的嵌套字典，格式为 {query_id: {doc_id: score}}。

    Returns:
        平均NDCG@10分数。
    """
    query_ids = [i["_id"] for i in test_queries]
    query_texts = [i["text"] for i in test_queries]
    doc_ids = [i["_id"] for i in test_corpus]
    doc_texts = [i["text"] for i in test_corpus]

    print("Step 1: 正在为所有查询和文档进行批量向量化...")
    # 1. 一次性获取所有查询和文档的Embeddings
    query_embeddings_list = embedding_text(query_texts) if model_f == 1 else tuning_embedding_text(query_texts)
    doc_embeddings_list = embedding_text(doc_texts) if model_f == 1 else tuning_embedding_text(doc_texts)

    # 将其转换为 NumPy 数组和ID映射，方便后续操作
    query_embedding_map = {qid: emb for qid, emb in zip(query_ids, query_embeddings_list)}
    doc_embeddings_matrix = np.array([emb for emb in doc_embeddings_list])

    # 预先计算所有文档向量的范数，用于快速计算余弦相似度
    doc_norms = np.linalg.norm(doc_embeddings_matrix, axis=1)

    all_ndcg_scores = []
    doc_id_to_index = {doc_id: i for i, doc_id in enumerate(doc_ids)}

    print("Step 2: 正在逐一计算每个查询的NDCG分数...")
    for query_id in query_ids:
        # 2. 获取当前查询的向量
        query_vec = np.array(query_embedding_map[query_id])

        # 3. 使用矩阵运算高效计算余弦相似度
        # similarity = (query_vec @ doc_embeddings_matrix.T) / (np.linalg.norm(query_vec) * doc_norms)
        # 为避免除以零，添加一个小的epsilon
        query_norm = np.linalg.norm(query_vec)
        denominator = query_norm * doc_norms + 1e-9  # 避免除以0
        similarities = np.dot(query_vec, doc_embeddings_matrix.T) / denominator

        # 4. 准备NDCG计算的输入 (这部分逻辑不变)
        true_relevance = np.zeros(len(doc_ids))

        # 从预处理好的labels中获取真实评分
        if query_id in labels:
            for doc_id, relevance in labels.get(query_id, {}).items():
                if doc_id in doc_id_to_index:
                    true_relevance[doc_id_to_index[doc_id]] = relevance

        # predicted_scores 就是我们刚用矩阵运算得到的 similarities
        predicted_scores = similarities

        # 5. 计算NDCG@10
        # 确保 y_true 和 y_score 都是二维的
        ndcg = ndcg_score([true_relevance], [predicted_scores], k=10)
        all_ndcg_scores.append(ndcg)

    print("Step 3: 计算平均NDCG分数...")
    return np.mean(all_ndcg_scores)


def main():
    with open("embedding_tune_evaluation.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        queries = data["queries"]
        corpus = data["docs"]
        labels = data["labels"]
        labels = preprocess_labels(labels)

        ndcg_base = evaluate_model_v1(queries, corpus, labels, model_f=1)
        ndcg_tune = evaluate_model_v1(queries, corpus, labels, model_f=2)

        print(f"Base Model NDCG@10: {ndcg_base}, Tune Model NDCG@10: {ndcg_tune}, "
              f"性能提升率：{(ndcg_tune - ndcg_base) / ndcg_base}")


if __name__ == "__main__":
    texts = [
        "我在数据分析方面有很强的技能，能够利用 Excel 和 SQL 进行数据建模和报表制作",
        "具备扎实的数据处理与分析功底，熟练运用SQL和Excel完成数据建模及可视化报表",
        "作为项目负责人，我的职责是把控项目生命周期，管理风险，并与各方干-系人有效沟通，以达成项目目标"
    ]
    embeddings = tuning_embedding_text(texts)
    for idx, embedding in enumerate(embeddings):
        print(f"Text: {texts[idx]}, Embedding: {embedding[:5]}...")

