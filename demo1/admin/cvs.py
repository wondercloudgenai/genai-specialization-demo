import typing

from fastapi import APIRouter, Depends, Body
from sqlalchemy import nullslast, or_, func
from sqlalchemy.orm import Session

from curd import CvInfoDao
import depend
from extentions import logger
from model import CVInfoModel, CVInfoAnalyzeModel, CVInfoUploadModel, OriginCVModel, OriginCVSentenceEmbeddingModel, \
    OriginCVKeywordEmbeddingModel
from schema.cvinfo_schema import CVOriginSchema
from schema.page_schema import PageInfo
from services.service_cvinfo import CvInfoService
from tools.rest_result import restResult
from backgroup_task.main import cv_pdf_split_and_embedding, abstract_cv


admin_cvs_router = APIRouter(prefix="/adm/cv", tags=["admin"], dependencies=[Depends(depend.admin_user)])


@admin_cvs_router.get("/list", description="获取所有简历列表")
async def cvs_list(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    jd_id: str = "",
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(CVInfoModel).outerjoin(CVInfoAnalyzeModel, CVInfoModel.id == CVInfoAnalyzeModel.v1_cv_id)
    if jd_id:
        query = query.filter(CVInfoModel.jd_id == jd_id)
    query = query.order_by(nullslast(CVInfoAnalyzeModel.suitability.desc()), CVInfoModel.create_time.desc())
    return restResult.success(data=CvInfoDao.page_data(query, page, "detail"))


@admin_cvs_router.get("/detail/{cv_id}", description="获取简历详情")
async def cv_detail(
    cv_id: str,
    session: Session = Depends(depend.get_db),
):
    cv = session.query(CVInfoModel).filter(CVInfoModel.id == cv_id).first()
    if not cv:
        return restResult.not_found("简历不存在")
    return restResult.success(data=cv.detail())


@admin_cvs_router.get("/view/{cv_id}", description="简历预览")
async def cv_view(
    cv_id: str,
    session: Session = Depends(depend.get_db),
    gcs_client=Depends(depend.get_gcs),
):
    cv = session.query(CVInfoModel).filter(CVInfoModel.id == cv_id).first()
    if not cv:
        return restResult.not_found("简历不存在")
    if cv.origin_cv.origin == CVOriginSchema.SPIDER_BOSS.value:
        return restResult.success(data=cv.detail())
    cv_save_path = cv.origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "inline")


@admin_cvs_router.delete("/{cv_id}", description="删除一个简历")
async def delete_cv(
    cv_id: str,
    session: Session = Depends(depend.get_db),
):
    cv = session.query(CVInfoModel).filter(CVInfoModel.id == cv_id).first()
    if not cv:
        return restResult.not_found("简历不存在")
    session.delete(cv)
    session.commit()
    logger.info(f"【Admin】删除简历{cv}")
    return restResult.success()


@admin_cvs_router.get("/uploaded/list", description="获取用户上传的简历列表")
async def uploaded_cvs(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    user_id: str = "",
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(CVInfoUploadModel).join(OriginCVModel, OriginCVModel.id == CVInfoUploadModel.cv_id)
    if user_id:
        query = query.filter(CVInfoUploadModel.uploader_id == user_id)
    query = query.order_by(CVInfoUploadModel.create_time.desc())
    return CvInfoDao.page_data(query, page, "sample")


@admin_cvs_router.get("/uploaded/view/{upload_id}", description="预览用户上传的简历")
async def uploaded_view(
    upload_id: str,
    gcs_client=Depends(depend.get_gcs),
    session: Session = Depends(depend.get_db),
):
    uploaded_cv = session.query(CVInfoUploadModel).filter(CVInfoUploadModel.id == upload_id).first()
    if not uploaded_cv:
        return restResult.not_found("请求资源不存在")
    cv_save_path = uploaded_cv.origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "inline")


@admin_cvs_router.delete("/uploaded/{upload_id}", description="删除用户上传的简历")
async def uploaded_delete_cv(
    upload_id: str,
    session: Session = Depends(depend.get_db),
):
    uploaded_cv = session.query(CVInfoUploadModel).filter(CVInfoUploadModel.id == upload_id).first()
    if not uploaded_cv:
        return restResult.not_found("请求资源不存在")
    session.delete(uploaded_cv)
    session.commit()
    return restResult.success()


@admin_cvs_router.get("/origins/list", description="获取简历原始数据列表")
async def origins_cvs_list(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    zone: str = "",
    source: typing.Literal["v1_upload", "v2_upload", "ehire"] = "",
    embedded: typing.Optional[bool] = None
):
    page = PageInfo(page_number, page_record_number)
    subquery_sentence_embedding_count = session.query(func.count(OriginCVSentenceEmbeddingModel.id)).filter(
        OriginCVSentenceEmbeddingModel.cv_id == OriginCVModel.id).correlate(OriginCVModel).label("count1")
    subquery_keyword_embedding_count = session.query(func.count(OriginCVKeywordEmbeddingModel.id)).filter(
        OriginCVKeywordEmbeddingModel.cv_id == OriginCVModel.id).correlate(OriginCVModel).label("count2")
    query = session.query(OriginCVModel, subquery_sentence_embedding_count, subquery_keyword_embedding_count)
    if zone:
        query = query.filter(OriginCVModel.zone.like(f"%{zone}%"))
    if source:
        query = query.filter(OriginCVModel.origin == source)
    if embedded is True:
        query = query.filter(OriginCVModel.keyword_embeddings != None, OriginCVModel.sentence_embeddings != None)
    elif embedded is False:
        query = query.filter(or_(OriginCVModel.keyword_embeddings == None, OriginCVModel.sentence_embeddings == None))
    else:
        ...
    query = query.order_by(OriginCVModel.create_time.desc())
    results = query.offset((page.page_number - 1) * page.page_size).limit(page.page_size)

    r = []
    for result in results:
        origin_cv_model, count1, count2 = result
        var1 = origin_cv_model.detail()
        var1.update({"sentence_embeddings_count": count1})
        var1.update({"keyword_embeddings_count": count2})
        r.append(var1)
    data = {
        "data": r,
        "total": query.count(),
        "page_number": page.page_number,
        "page_record_number": page.page_size,
    }
    return restResult.success(data=data)


@admin_cvs_router.post("/origin/embedding/start", description="启动简历关键词和句子向量embedding")
async def origins_cvs_embedding_start(
    origin_cv_id: typing.Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    origin: OriginCVModel = session.query(OriginCVModel).filter(OriginCVModel.id == origin_cv_id).first()
    if not origin:
        return restResult.not_found("请求资源不存在")
    cv_pdf_split_and_embedding.apply_async(kwargs={"cv_id": origin_cv_id, "cv_gs_path": origin.save_path})
    cvs = [{"cv_id": origin_cv_id, "gcs_path": origin.save_path}]
    abstract_cv.apply_async(kwargs={"cvs": cvs})
    return restResult.success()


@admin_cvs_router.get("/origin/view/{origin_cv_id}", description="预览源简历")
async def uploaded_view(
    origin_cv_id: str,
    gcs_client=Depends(depend.get_gcs),
    session: Session = Depends(depend.get_db),
):
    origin_cv: OriginCVModel = session.query(OriginCVModel).filter(OriginCVModel.id == origin_cv_id).first()
    if not origin_cv:
        return restResult.not_found("请求资源不存在")
    cv_save_path = origin_cv.save_path
    return await CvInfoService.get_stream_cv(cv_save_path, gcs_client, "inline")
