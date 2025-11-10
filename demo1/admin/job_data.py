import typing
from typing import Annotated

from fastapi import APIRouter, Depends, Body
from sqlalchemy import nullslast, func
from sqlalchemy.orm import Session

from curd import JobDataDao
import depend
from extentions import logger
from model import JobDataModel, JobDataCVSearchTaskModel, CVInfoModel, CVInfoAnalyzeModel, JobCandidateModel
from schema.page_schema import PageInfo
from schema.user_schemas import AdminUser
from tools.rest_result import restResult
from backgroup_task.main import analytic_cv, analytic_jd

admin_jd_router = APIRouter(prefix="/adm/jd", tags=["admin"], dependencies=[Depends(depend.admin_user)])


@admin_jd_router.get("/list", description="获取所有jd，支持模糊搜索")
async def jd_list(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    fuzzy_search_key: str = "",
    company_id: str = ""
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(JobDataModel)
    if fuzzy_search_key != "":
        query = query.filter(JobDataModel.name.like(f"%{fuzzy_search_key}%"))
    if company_id:
        query = query.filter(JobDataModel.company_id == company_id)
    query = query.order_by(JobDataModel.create_time.desc())
    return restResult.success(data=JobDataDao.page_data(query, page, "detail"))


@admin_jd_router.delete("/{jd_id}", description="删除一个JD")
async def user_disable(
    jd_id: str,
    session: Session = Depends(depend.get_db),
    admin_user: AdminUser = Depends(depend.admin_user),
):
    jd = session.query(JobDataModel).filter(JobDataModel.id == jd_id).first()
    if not jd:
        return restResult.fail("岗位不存在")
    session.delete(jd)
    jd_info = f"{jd}"
    session.commit()
    logger.info(f"{admin_user}删除岗位{jd_info}成功.")
    return restResult.success()


@admin_jd_router.get("/{jd_id}/st-list", description="获取某个JD的搜索任务列表")
async def get_jd_search_list(
    jd_id: str,
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
):
    jd = session.query(JobDataModel).filter(JobDataModel.id == jd_id).first()
    if not jd:
        return restResult.fail("岗位不存在")
    page = PageInfo(page_number, page_record_number)
    query = session.query(JobDataCVSearchTaskModel).filter(JobDataCVSearchTaskModel.jd_id == jd_id).order_by(
        JobDataCVSearchTaskModel.create_time.desc()
    )
    return restResult.success(data=JobDataDao.page_data(query, page, "detail"))


@admin_jd_router.get("/{jd_id}/candidates", description="获取某个JD的所有候选人")
async def get_jd_search_list(
    jd_id: str,
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(JobCandidateModel).filter(JobCandidateModel.jd_id == jd_id).order_by(
        JobCandidateModel.create_time.desc()
    )
    return restResult.success(data=JobDataDao.page_data(query, page, "detail"))


@admin_jd_router.get("/{jd_id}/cvs", description="获取某个JD下的简历列表")
async def get_jd_cvs(
    jd_id: str,
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(CVInfoModel).outerjoin(CVInfoAnalyzeModel,
                                                 CVInfoModel.id == CVInfoAnalyzeModel.v1_cv_id).filter(
        CVInfoModel.jd_id == jd_id).order_by(nullslast(CVInfoAnalyzeModel.suitability.desc()),
                                             CVInfoModel.create_time.desc())
    return restResult.success(data=JobDataDao.page_data(query, page, "detail"))


@admin_jd_router.get("/st/{st_id}/cvs", description="获取某个搜索任务下的简历列表")
async def get_search_task_cvs(
    st_id: str,
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(CVInfoModel).outerjoin(CVInfoAnalyzeModel,
                                                 CVInfoModel.id == CVInfoAnalyzeModel.v1_cv_id).filter(
        CVInfoModel.search_task_id == st_id).order_by(nullslast(CVInfoAnalyzeModel.suitability.desc()),
                                                      CVInfoModel.create_time.desc())
    return restResult.success(data=JobDataDao.page_data(query, page, "detail"))


@admin_jd_router.post("/st/analyze/start", description="开始某个检索任务的简历分析后台任务, 仅分析未分析的简历")
async def analytic_job_cvs(
    st_id: Annotated[str, Body(embed=True)],
    quota: Annotated[typing.Union[bool, int], Body(embed=True)] = False,
    session: Session = Depends(depend.get_db),
):
    task = session.query(JobDataCVSearchTaskModel).filter(JobDataCVSearchTaskModel.id == st_id).first()
    if not task:
        return restResult.not_found(msg="请求资源错误")
    non_analyzed_cvs = session.query(CVInfoModel).filter(
        CVInfoModel.search_task_id == st_id, CVInfoModel.analyze_status == -1).all()
    if not non_analyzed_cvs:
        return restResult.fail("该任务下没有未分析的简历")
    analytic_cv.apply_async(kwargs={"task_id": st_id, "jd_id": task.jd_id, "quota": quota})
    return restResult.success()


@admin_jd_router.post("/analyze/start", description="开始某个JD下的简历分析后台任务, 仅分析未分析的简历")
async def analytic_job_cvs(
    jd_id: Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    jd = session.query(JobDataModel).filter(JobDataModel.id == jd_id).first()
    if not jd:
        return restResult.not_found(msg="请求资源错误")

    grouped_data = session.query(CVInfoModel.search_task_id, func.count(CVInfoModel.id).label(
        'non_analyzed_cvs_count')).filter(CVInfoModel.jd_id == jd_id, CVInfoModel.analyze_status == -1
                                          ).group_by(CVInfoModel.search_task_id).all()
    if len(grouped_data) <= 0:
        return restResult.fail("该JD下没有未分析的简历")
    for st_id, non_analyzed_cvs_count in grouped_data:
        if non_analyzed_cvs_count > 0:
            analytic_cv.apply_async(kwargs={"task_id": st_id, "jd_id": jd_id, "quota": non_analyzed_cvs_count})
    return restResult.success()


@admin_jd_router.post("/summary/analyze/start", description="开始某个JD的Summary分析后台任务")
async def analytic_job_cvs(
    jd_id: Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    jd = session.query(JobDataModel).filter(JobDataModel.id == jd_id).first()
    if not jd:
        return restResult.not_found(msg="请求资源错误")
    analytic_jd.apply_async(kwargs={"jd_id": jd_id})
    return restResult.success()


