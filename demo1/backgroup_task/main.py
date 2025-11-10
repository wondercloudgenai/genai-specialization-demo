import typing

from celery import Celery
import requests

from settings import setting
from tools.pdf_extract import process_resume_pdf
from .analytic import Analytic
from .analytic_base import AnalyticSessionChatManager, AnalyticSessionChatException
from .analytic_session_chat import AnalyticChat

ai_analytic = Analytic()
ai_analytic_chat_manager = AnalyticSessionChatManager()
url = "http://localhost:8080/api/v1"

app = Celery('tasks', broker=setting.REDIS_URL, backend=setting.REDIS_URL)
headers = {
    "x-api-key": setting.X_API_KEY,
}


celery_task_event_literal = typing.Literal[
    "jd_detail_get",
    "jd_analyze_create",
    "cv_non_analytic_get",
    "cv_non_analytic_get_json",
    "cv_analytic_attach_create",
    "cv_abstract_attach_create",
    "cv_analytic_status_update",
    "cv_sentence_embeddings_create",
    "cv_keyword_embeddings_create",
    "search_task_status_update",
    "search_task_detail_get",
    "search_task_vector_cvs_retrieval",
    "interview_eva_result_update"
]


def celery_task_callback(event: celery_task_event_literal, **payload):
    _url = url + "/index/bg/celery/callback?event=" + event
    res = requests.post(_url, headers=headers, json=payload)
    print(f"[Debug]: Event({event}) celery callback response code: {res.status_code}, text: {res.text}")
    if res.status_code == 200 and res.json()["code"] == 200:
        return res.json()["data"]
    return None


@app.task
def analytic_jd(jd_id):
    payload = {
        "jd_id": jd_id,
    }
    jd_info = celery_task_callback("jd_detail_get", **payload)
    if jd_info:
        analytic_content = "岗位名称:\n{}".format(jd_info["name"])
        analytic_content += "\n岗位要求:\n{}".format(jd_info["work_request"])
        analytic_content += "\n岗位工作内容:\n{}".format(jd_info["work_info"])
        analytic_content += "\n岗位职责:\n{}".format(jd_info["responsibilities"])
        # 完成AI接口调用

        result = ai_analytic.analytic_jd(analytic_content)
        if result:
            result["jd_id"] = jd_id

            if celery_task_callback("jd_analyze_create", **result):
                print("创建JD分析结果成功")


@app.task
def analytic_cv(task_id, jd_id, **kwargs):
    # t1 = time.time()
    params = {"search_task_id": task_id}
    params.update(kwargs)
    data = celery_task_callback("cv_non_analytic_get", **params)
    if not data:
        print(f"获取【TaskId={task_id}，JobId={jd_id}，quota={kwargs.get('quota')}】获取未分析简历异常")
        return
    cvs = data["cvs"]
    v = []
    for cv in cvs:
        v.append({
            "cv_id": cv["cv_id"],
            "analyze_status": 0,
        })

    print(f"获取【TaskId={task_id}，JobId={jd_id}，quota={kwargs.get('quota')}】获取未分析简历成功，数量：{len(cvs)}")
    ret = celery_task_callback("cv_analytic_status_update", cvs=v)
    print(f"【TaskId={task_id}，JobId={jd_id}】批量更新简历分析状态{'成功' if ret else '失败'}")
    result = ai_analytic.analytic_cv(cvs=cvs, job_info=data["job_info"])
    if result:
        payload = {"analyzes": result, "task_id": task_id}
        if celery_task_callback("cv_analytic_attach_create", **payload):
            print(f"【TaskId={task_id}，JobId={jd_id}】数据库保存分析记录成功")
        else:
            print(f"【TaskId={task_id}，JobId={jd_id}】数据库保存分析记录失败")


def cv_texts_embedding(cv_id, texts):
    texts_len = len(texts)
    d, v = divmod(texts_len, 150)
    if v > 0:
        d += 1

    embeddings = []
    embedding_result = True
    for i in range(d):
        tmp_texts = texts[i * 150:(i + 1) * 150]
        values = ai_analytic.embedding_texts(tmp_texts)
        if values:
            for idx, text in enumerate(tmp_texts):
                embedding_item = {
                    "cv_id": cv_id,
                    "sentence": text,
                    "embedding": values[idx]
                }
                embeddings.append(embedding_item)
        else:
            embedding_result = False
            break
    if embedding_result:
        return True, embeddings
    return False, []


@app.task
def sentence_embedding(cv_id, texts):
    embedding_result, embeddings = cv_texts_embedding(cv_id, texts)
    if not embedding_result:
        print(f"生成简历SentenceEmbedding, OriginCV[cv_id={cv_id}]失败")
    else:
        print(f"生成简历SentenceEmbedding, OriginCV[cv_id={cv_id}]成功")
        ret = celery_task_callback("cv_sentence_embeddings_create", embeddings=embeddings)
        if ret:
            print(f"生成简历SentenceEmbedding, OriginCV[cv_id={cv_id}]记录成功，保存记录结果：{ret}")
        else:
            print(f"生成简历SentenceEmbedding, OriginCV[cv_id={cv_id}]记录失败，{ret}")


# def create_analyze_chat(chat_session_id: str, owner: str, job_info: str):
#     chat = AnalyticSessionChatManager.get_session(chat_session_id)
#     if not chat:
#         new_chat = AnalyticChat(job_info)
#         AnalyticSessionChatManager.register_session(chat_session_id, new_chat, owner)
#     return Result.ok().__dict__


@app.task
def analyze_chat_cvs(msg: str, cvs, job_info: str):
    analyze_chat = AnalyticChat(job_info)
    ret = analyze_chat.analyze(msg, cvs)
    return ret.serialize()


@app.task
def text_embedding(text):
    return ai_analytic.embedding_text(text)


@app.task
def abstract_cv(cvs):
    if not isinstance(cvs, list):
        cvs = [cvs]
    print(f"【Abstract-CV】开始提取简历信息及关键字，本次简历批次数量：{len(cvs)}")
    results = ai_analytic.cv_abstract(cvs)
    _results = []
    if results:
        print(f"【Abstract-CV】提取简历信息及关键字成功，数量：{len(cvs)}")
        for item in results:
            keywords_embedding_list = []
            print(f"【Abstract-CV】开始计算Keywords-Embedding, keywords={item['keywords']}")
            keywords = [f"tag: {text}" for text in item["keywords"]]
            embeddings = ai_analytic.embedding_texts(keywords)
            if embeddings:
                for idx, text in enumerate(item["keywords"]):
                    embedding_item = {
                        "keyword": text,
                        "embedding": embeddings[idx]
                    }
                    keywords_embedding_list.append(embedding_item)
                print(f"【Abstract-CV】计算Keywords-Embedding, keywords={item['keywords']}成功")
            else:
                print(f"【Abstract-CV】计算Keywords-Embedding, keywords={item['keywords']}失败")
            _results.append({
                "cv_id": item["key"],
                "info": item["info"],
                "keywords": keywords_embedding_list
            })
        payload = {"results": _results}
        if celery_task_callback("cv_abstract_attach_create", **payload):
            print(f"【Abstract-CV】提取简历信息及关键字数据库保存分析记录成功")
        else:
            print(f"【Abstract-CV】提取简历信息及关键字数据库保存分析记录失败")


@app.task
def cvs_search_task_via_vector(task_id):
    try:
        payload = {"search_task_id": task_id, "status": "Starting", "reason": "Starting"}
        celery_task_callback("search_task_status_update", **payload)
        payload = {"search_task_id": task_id}
        task = celery_task_callback("search_task_detail_get", **payload)
        if not task:
            print(f"【Search-Vector-CV】获取搜索任务详情失败")
            payload = {"search_task_id": task_id, "status": "Failed", "reason": "Server error"}
            celery_task_callback("search_task_status_update", **payload)
            return
        keyword = task["keyword"]
        jd_id = task["jd_id"]
        limit = task["search_number"]
        zone = task["zone"]
        keyword_summary = task["keyword_summary"]
        embedding = ai_analytic.embedding_text(keyword_summary)
        if not embedding:
            print(f"【Search-Vector-CV】Embedding计算失败")
            payload = {"search_task_id": task_id, "status": "Failed", "reason": "Server error"}
            celery_task_callback("search_task_status_update", **payload)
            return
        payload = {"search_task_id": task_id, "jd_id": jd_id, "limit": limit, "zone": zone, "embedding": embedding}
        ret = celery_task_callback("search_task_vector_cvs_retrieval", **payload)
        if ret:
            print(f"【Search-Vector-CV】检索向量英才建立数据库成功，{ret}")
            payload = {"search_task_id": task_id, "status": "Completed", "reason": "search task completed"}
            celery_task_callback("search_task_status_update", **payload)
        else:
            print(f"【Search-Vector-CV】检索向量英才建立数据库失败")
            payload = {"search_task_id": task_id, "status": "Failed", "reason": "Server error"}
            celery_task_callback("search_task_status_update", **payload)
    except Exception as e:
        print(f"【Search-Vector-CV】检索向量英才建立数据库异常, {e}")
        payload = {"search_task_id": task_id, "status": "Failed", "reason": "Celery task error"}
        celery_task_callback("search_task_status_update", **payload)


@app.task
def split_pdf_chunks_and_embedding(cv_id, chunks):
    if chunks:
        print(f"【简历Embedding】切片简历成功，CV_ID: {cv_id}")
        embedding_result, embeddings = cv_texts_embedding(cv_id, chunks)
        if not embedding_result:
            print(f"【简历Embedding】, OriginCV[cv_id={cv_id}]失败")
        else:
            print(f"【简历Embedding】, OriginCV[cv_id={cv_id}]成功")
            ret = celery_task_callback("cv_sentence_embeddings_create", embeddings=embeddings)
            if ret:
                print(f"【简历Embedding】, OriginCV[cv_id={cv_id}]记录成功，保存记录结果：{ret}")
            else:
                print(f"【简历Embedding】, OriginCV[cv_id={cv_id}]记录失败，{ret}")
    else:
        print(f"【简历Embedding】切片简历失败，CV_ID: {cv_id}")


@app.task
def interview_eva(task_id, template_save_path, content_save_path):
    print(f"【面试评价】开始AI面评，模板路径：{template_save_path}，内容路径：{content_save_path}")
    result = ai_analytic.interview_evaluation(template_save_path, content_save_path)
    if result:
        payload = {"result": result, "status": 1, "task_id": task_id}
        print(f"【面试评价】AI面评成功")
    else:
        payload = {"result": result, "status": 0, "task_id": task_id}
        print(f"【面试评价】AI面评失败")
    celery_task_callback("interview_eva_result_update", **payload)

