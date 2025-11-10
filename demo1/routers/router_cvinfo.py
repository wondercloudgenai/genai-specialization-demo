import hashlib
import json

from sqlalchemy.orm import Session
from starlette.requests import Request

import depend
from fastapi import APIRouter, Depends, Form, Body, UploadFile, BackgroundTasks

from extentions import logger
from model import OriginCVModel
from schema.cvinfo_schema import *
from uuid import uuid4
from typing import Annotated
from backgroup_task.main import analytic_cv, sentence_embedding, abstract_cv, split_pdf_chunks_and_embedding
from schema.jobdata_schema import CVOriginSchema
from schema.page_schema import PageInfo
from schema.user_schemas import CurrentUser
from services.service_search_task import SearchTaskService
from settings import setting
from tools.rest_result import restResult
from services.service_cvinfo import CvInfoService
from tools.pdf_extract import process_resume_pdf

cv_route = APIRouter(prefix="/cv")


@cv_route.post("/spider/add", dependencies=[Depends(depend.require_api_key)], description="前程无忧Spider专用上传简历")
async def add_spider_cv(
    cv_file: UploadFile = Form(),
    resume_id: str = Form(),
    jd_id: str = Form(),
    task_id: str = Form(),
    sn: int = Form(),  # 序列号
    meta_json: str = Form(default=""),
    source: str = Form(default=CVOriginSchema.SPIDER_EHIRE.value),
    resource_url: str = Form(default=""),
    session=Depends(depend.get_db),
    gcs_client=Depends(depend.get_gcs),
):
    file_name = "{}/{}.pdf".format(jd_id, uuid4().hex)
    ret = await CvInfoService.upload_cv_pdf_to_gcs(file_name, gcs_client, cv_file)
    if ret.is_fail:
        return restResult.fail(ret.msg)

    # step 1、添加数据库
    meta_json = json.loads(meta_json)
    gcs_path = f"gs://{setting.bucket_name}/{file_name}"
    ret = await CvInfoService.add_spider_search_task_cv(
        jd_id=jd_id,
        search_task_id=task_id,
        save_path=gcs_path,
        mark=resume_id,
        meta_json=meta_json,
        origin=source,
        resource_url=resource_url,
        session=session
    )
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    quota = setting.ANALYZE_ADD_WHEN_UPLOAD
    if sn % quota == 0:
        analytic_cv.apply_async(kwargs={"task_id": task_id, "jd_id": jd_id, "quota": quota})

    origin_cv_id = ret.data["origin_cv_id"]
    if CvInfoService.cv_dao.count_of_cv_sentence_embeddings(session, cv_id=origin_cv_id) == 0:
        texts = CvInfoService.extract_resume_meta_json_values(meta_json)
        if len(texts) > 0:
            sentence_embedding.apply_async(kwargs={"cv_id": origin_cv_id, "texts": texts})
    if CvInfoService.cv_dao.count_of_cv_keyword_embeddings(session, cv_id=origin_cv_id) == 0:
        cvs = [{"cv_id": origin_cv_id, "gcs_path": gcs_path, "origin": "ehire"}]
        abstract_cv.apply_async(kwargs={"cvs": cvs})
    return restResult.success()


@cv_route.post("/spider/boss/add", dependencies=[Depends(depend.require_api_key)],
               description="Boss直聘Spider专用上传简历")
async def add_spider_cv(
    resume_id: str = Form(),
    jd_id: str = Form(),
    task_id: str = Form(),
    sn: int = Form(),  # 序列号
    meta_json: str = Form(default=""),
    source: str = Form(default=CVOriginSchema.SPIDER_BOSS.value),
    resource_url: str = Form(default=""),
    session=Depends(depend.get_db),
):
    # step 1、添加数据库
    meta_json = json.loads(meta_json)
    ret = await CvInfoService.add_spider_search_task_cv(
        jd_id=jd_id,
        search_task_id=task_id,
        save_path="",
        mark=resume_id,
        meta_json=meta_json,
        origin=source,
        resource_url=resource_url,
        session=session
    )
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    quota = setting.ANALYZE_ADD_WHEN_UPLOAD
    if sn % quota == 0:
        analytic_cv.apply_async(kwargs={"task_id": task_id, "jd_id": jd_id, "quota": quota})

    origin_cv_id = ret.data["origin_cv_id"]
    if CvInfoService.cv_dao.count_of_cv_sentence_embeddings(session, cv_id=origin_cv_id) == 0:
        texts = CvInfoService.extract_boss_resume_meta_json_values(meta_json)
        if len(texts) > 0:
            sentence_embedding.apply_async(kwargs={"cv_id": origin_cv_id, "texts": texts})
    if CvInfoService.cv_dao.count_of_cv_keyword_embeddings(session, cv_id=origin_cv_id) == 0:
        cvs = [{"cv_id": origin_cv_id, "meta_json": json.dumps(meta_json, ensure_ascii=False), "origin": "boss"}]
        abstract_cv.apply_async(kwargs={"cvs": cvs})
    return restResult.success()


@cv_route.post("/upload", description="上传简历")
async def upload_cv(
    cv_file: UploadFile = Form(),
    session=Depends(depend.get_db),
    gcs_client=Depends(depend.get_gcs),
    current_user=Depends(depend.current_user),
):
    if cv_file.size > 10 * 1024 * 1024 or cv_file.content_type != "application/pdf":
        return restResult.fail("仅能上传小于10M, 且格式为PDF的简历")
    if cv_file.size <= 0:
        return restResult.fail("简历内容为空")

    # 计算mark值，使用文件md5来计算mark
    md5_hash = hashlib.md5()  # 创建一个 MD5 哈希对象
    while True:
        byte_block = await cv_file.read(4096)
        if not byte_block:
            break
        md5_hash.update(byte_block)
    await cv_file.seek(0)
    md5_hash.update(f"{current_user.id}{cv_file.filename}".encode("utf-8"))
    mark = f"v1_upload_{md5_hash.hexdigest()}"

    origin_cv_exists = CvInfoService.cv_dao.get_origin_cv_by_mark(mark, session)
    if origin_cv_exists and origin_cv_exists.name == cv_file.filename:
        return restResult.validate_error("请勿上传重复简历")

    h = uuid4().hex
    file_name = "v1_upload/{}.pdf".format(h)
    ret = await CvInfoService.upload_cv_pdf_to_gcs(file_name, gcs_client, cv_file)
    if ret.is_fail:
        return restResult.build_from_ret(ret)

    # step 1、添加数据库
    gs_save_path = f"gs://{setting.bucket_name}/{file_name}"
    ret = await CvInfoService.add_upload_cv(
        save_path=gs_save_path,
        cv_name=cv_file.filename,
        mark=mark,
        session=session,
        current_user=current_user
    )
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    origin_cv = ret.data["origin_cv"]
    pdf_stream = await cv_file.read()
    result = process_resume_pdf(pdf_stream=pdf_stream, chunk_size=350, chunk_overlap=40)
    logger.info(f"简历{gs_save_path}切片完成，共生成 {len(result)} 个文本块。")
    if result:
        texts = [i["text"] for i in result]
        split_pdf_chunks_and_embedding.apply_async(kwargs={"cv_id": origin_cv.id, "chunks": texts})
    cvs = [{"cv_id": origin_cv.id, "gcs_path": gs_save_path}]
    abstract_cv.apply_async(kwargs={"cvs": cvs})
    return restResult.success()


@cv_route.get("/list", description="根据Job查找对应的所有简历")
async def list_cv_route(
    request: Request,
    page_number: int = 1,
    page_record_number: int = 50,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db)
):
    jd_id = request.query_params.get("jd_id", "*")
    has_analytic = request.query_params.get("has_analytic", -1)
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    ret = await CvInfoService.list_current_user_cvs_via_job(
        session, page, current_user, jd_id=jd_id, has_analytic=has_analytic)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    return restResult.success(data=ret.data)


@cv_route.get("/list/st", description="根据搜索任务查找对应所有简历")
async def list_cv_via_search_task(
    st_id: str,
    page_number: int = 1,
    page_record_number: int = 50,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db)
):
    ret = SearchTaskService.valid_search_task(st_id, session, current_user, check_user=False)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    ret = SearchTaskService.get_cvs_via_search_task(st_id, session, current_user, page)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    return restResult.success(data=ret.data)


@cv_route.get("/detail")
async def detail_cv(cv_id: str, session=Depends(depend.get_db), current_user=Depends(depend.current_user)):
    ret = CvInfoService.valid_cv(cv_id, session, current_user, check_user=False)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    return restResult.success(data=ret.data.detail())


@cv_route.get("/download", description="简历下载接口")
async def download_cv(
    cv_id,
    gcs_client=Depends(depend.get_gcs),
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    ret = CvInfoService.valid_cv(cv_id, session, current_user, check_user=False)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    cv = ret.data
    if cv.origin_cv.origin == CVOriginSchema.SPIDER_BOSS.value:
        return restResult.fail("不支持的操作")
    cv_save_path = cv.origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "attachment")


@cv_route.get("/view", description="简历预览接口")
async def view_cv(
    cv_id,
    gcs_client=Depends(depend.get_gcs),
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    ret = CvInfoService.valid_cv(cv_id, session, current_user, check_user=False)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    cv = ret.data
    if cv.origin_cv.origin == CVOriginSchema.SPIDER_BOSS.value:
        return restResult.success(data=cv.detail())
    cv_save_path = cv.origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "inline")


@cv_route.get("/uploaded/view", description="用户上传的简历的预览接口")
async def uploaded_view_cv(
    upload_id: str,
    gcs_client=Depends(depend.get_gcs),
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    upload_cv = CvInfoService.cv_dao.get_uploaded_cv(upload_id, session)
    if not upload_cv:
        return restResult.not_found("请求资源异常")
    if upload_cv.uploader_id != current_user.id:
        return restResult.unauthorized("无资源操作权限")
    cv_save_path = upload_cv.origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "inline")


@cv_route.get("/uploaded/download", description="用户上传的简历的下载接口")
async def uploaded_download_cv(
    upload_id: str,
    gcs_client=Depends(depend.get_gcs),
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    upload_cv = CvInfoService.cv_dao.get_uploaded_cv(upload_id, session)
    if not upload_cv:
        return restResult.not_found("请求资源异常")
    if upload_cv.uploader_id != current_user.id:
        return restResult.unauthorized("无资源操作权限")
    cv_save_path = upload_cv.origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "attachment")


@cv_route.delete("/uploaded/{upload_id}", description="用户上传的简历的删除接口")
async def uploaded_delete_cv(
    upload_id: str,
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    ret = await CvInfoService.delete_uploaded_cv(upload_id, session, current_user)
    return restResult.build_from_ret(ret)


@cv_route.post("/spider/duplicate/detection", dependencies=[Depends(depend.require_api_key)],
               description="爬虫专用接口")
async def resume_duplicate_detection(
    jd_id: Annotated[str, Body(embed=True)],
    resume_id_list: Annotated[List[str], Body(embed=True)],
    session=Depends(depend.get_db),
):
    return restResult.build_from_ret(await CvInfoService.resume_duplicate_detection(jd_id, resume_id_list, session))


@cv_route.delete("/multiple", description="CVInfo批量删除接口")
async def delete_multiple_cv(
    cv_list: Annotated[List[str], Body(embed=True)],
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    if not cv_list:
        return restResult.fail("请求参数为空")
    return restResult.build_from_ret(await CvInfoService.delete_many(cv_list, session, current_user))


@cv_route.delete("/{cv_id}", description="CVInfo删除接口")
async def delete_cv(
    cv_id: str,
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    return restResult.build_from_ret(await CvInfoService.delete(cv_id, session, current_user))


@cv_route.get("/uploaded", description="获取当前用户上传的简历")
async def get_upload_cvs(
    page_number: int = 1,
    page_record_number: int = 50,
    session=Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    data = CvInfoService.cv_dao.get_uploaded_cvs_via_user(current_user.id, session, page)
    return restResult.success(data=data)

# @cv_route.post("/abstract", description="测试接口，用户将所有简历进行keywords-embedding和关键信息提取")
# async def abstract_cvs(
#     limit: Annotated[int, Body(embed=True)],
#     session: Session = Depends(depend.get_db),
#     current_user: CurrentUser = Depends(depend.current_user)
# ):
#     query = session.query(OriginCVModel).filter(OriginCVModel.keyword_embeddings == None)
#     if limit <= 0:
#         origin_cvs = query.all()
#     else:
#         origin_cvs = query.limit(limit).all()
#     for cv in origin_cvs:
#         p = [{"cv_id": cv.id, "gcs_path": cv.save_path}]
#         abstract_cv.apply_async(args=(p, ))
#     return restResult.success(data=[i.sample() for i in origin_cvs])
