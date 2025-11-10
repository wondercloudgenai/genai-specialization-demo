from sqlalchemy.orm import Session
from starlette.requests import Request

import depend
from typing import Annotated

from fastapi import APIRouter, Depends, Form

from backgroup_task.analytic import Analytic
from backgroup_task.main import analytic_jd
from model import JobDataModel
from schema.jobdata_schema import *
from backgroup_task.main import analytic_cv
from schema.page_schema import PageInfo
from schema.user_schemas import CurrentUser
from services.exceptions.custom_exceptions import DataProcessingException
from services.service_search_task import SearchTaskService
from services.service_jobdata import JobDataService

from tools.rest_result import restResult

jd_router = APIRouter(prefix="/jd")


@jd_router.post("/create", description="创建JobData接口")
async def create(
    schema: JobDataSchema,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = JobDataService.create(schema, session, current_user)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    analytic_jd.apply_async(kwargs={"jd_id": str(ret.data)})
    return restResult.success(data=ret.data)


@jd_router.get("/list", description="获取所有job-data接口")
async def list_job(
    page_number: int = 1,
    page_record_number: int = 50,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    if not current_user.company_id:
        return restResult.forbidden(msg="当前用户未加入任何公司组织")
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    ret = JobDataService.list_job(session, current_user, page)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    return restResult.success(data=ret.data)


@jd_router.get("/menu/list", description="获取所有job-data-menu接口")
async def list_memu_all_job(
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    if not current_user.company_id:
        return restResult.forbidden(msg="当前用户未加入任何公司组织")
    ret = JobDataService.list_job_menu(session=session, current_user=current_user)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    return restResult.success(data=ret.data)


@jd_router.get("/detail", description="获取某一个JobData详情接口")
async def detail(
    jd_id,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = JobDataService.valid_jd(jd_id, session, current_user, check_user=False)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    jd = ret.data
    return restResult.success(data=jd.detail())


@jd_router.post("/analytic/summary/modify", description="修改JobData Summary接口")
async def modify_summary(
    summary: JobDataSummarySchema,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = JobDataService.modify_jd_summary(summary, session, current_user)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    return restResult.success(data=ret.data)


@jd_router.post("/analytic/keyword/modify", description="修改JobData Keywords接口")
async def modify_summary(
    keyword: JobDataKeywordSchema,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = JobDataService.modify_jd_keyword(keyword, session, current_user)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    return restResult.success(data=ret.data)


@jd_router.get("/search/list")
async def analytic_task_list(
    jd_id: str,
    page_number: int = 1,
    page_record_number: int = 50,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    ret = JobDataService.get_jd_search_tasks(jd_id, session, current_user, page)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    return restResult.success(data=ret.data)


@jd_router.post("/search/start", description="检索任务开启接口")
async def search_task_start(
    schema: SearchTaskStartSchema,
    request: Request,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    if schema.origin == CVOriginSchema.SPIDER_EHIRE.value:
        request_json = await request.json()
        ehire_username, ehire_member, ehire_password = (
            request_json.get("ehire_username"), request_json.get("ehire_member"), request_json.get("ehire_password"))
        if not ehire_username or not ehire_member or not ehire_password:
            return restResult.validate_error("请提供正确的前程无忧账户、会员及密码")
        payload = {
            "username": request_json.get("ehire_username"),
            "member_name": request_json.get("ehire_member"),
            "password": request_json.get("ehire_password"),
        }
        payload.update(schema.model_dump())
        ret = await SearchTaskService.create_ehire_spider_task(session, current_user, **payload)
        if ret.is_fail:
            return restResult.fail(ret.msg)
        return restResult.success(data=ret.data)
    elif schema.origin == CVOriginSchema.VECTOR.value:
        payload = schema.model_dump()
        ret = await SearchTaskService.create_vector_task(session, current_user, **payload)
        if ret.is_fail:
            return restResult.fail(ret.msg)
        return restResult.success(data=ret.data)
    elif schema.origin == CVOriginSchema.SPIDER_BOSS.value:
        request_json = await request.json()
        user_cookies = request_json.get("user_cookies")
        if not user_cookies:
            return restResult.validate_error("请先扫码登录")
        payload = {
            "user_cookies": user_cookies
        }
        payload.update(schema.model_dump())
        ret = await SearchTaskService.create_boss_spider_task(session, current_user, **payload)
        if ret.is_fail:
            return restResult.fail(ret.msg)
        return restResult.success(data=ret.data)
    else:
        return restResult.fail("暂未支持的操作")


@jd_router.get("/search/detail/{st_id}", description="接口检索任务详情接口")
async def search_task_detail(
    st_id: str,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = SearchTaskService.valid_search_task(st_id, session, current_user, check_user=False)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    search_task = ret.data
    return restResult.success(data=search_task.sample())


@jd_router.post("/spider/task/callback", dependencies=[Depends(depend.require_api_key)])
async def analytic_task_callback(
    callback_schema: SearchTaskCallbackSchema,
    session: Session = Depends(depend.get_db)
):
    ret = SearchTaskService.search_task_callback(callback_schema, session)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    # 所有爬取任务结束后
    if "complete" in callback_schema.status.lower() and callback_schema.success_upload != 0:
        analytic_cv.apply_async(
            kwargs={"task_id": callback_schema.task_id, "jd_id": callback_schema.jd_id, "quota": False})
    return restResult.success()


@jd_router.post("/description/analytics", dependencies=[Depends(depend.has_logged)])
async def analytics_jd_description_file(
    job_description_str: Annotated[str, Form()] = None,
    job_description_file: UploadFile = None,
):
    if not job_description_file and not job_description_str:
        return restResult.fail("岗位描述参数异常")
    analytics_client = Analytic()
    if job_description_str:
        analytics_result = analytics_client.resolve_jd(jd_info=job_description_str, index=1)
    elif job_description_file:
        steam_bytes = await job_description_file.read()
        analytics_result = analytics_client.resolve_jd(jd_file_stream=steam_bytes, index=1)
    else:
        return restResult.fail("岗位描述参数异常")
    return restResult.success(data=analytics_result)


@jd_router.delete("/{jd_id}", description="删除一条JD记录")
async def delete_jd(
    jd_id: str,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    return restResult.build_from_ret(JobDataService.delete_by_id(jd_id, session, current_user))


@jd_router.post("/rename", description="对JD进行重命名")
async def rename_jd(
    schema: JobDataRenameSchema,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = JobDataService.valid_jd(schema.jd_id, session, current_user, check_user=True)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    jd = ret.data
    ret = JobDataService.update_jd(jd, session, current_user, name=schema.name)
    return restResult.build_from_ret(ret)


@jd_router.post("/update", description="更新JD信息")
async def update_jd(
    schema: JobDataUpdateSchema,
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user)
):
    ret = JobDataService.get_jd_via_user(schema.jd_id, session, current_user)
    if ret.is_fail:
        return restResult.fail(ret.msg)
    jd = ret.data
    if schema.zone_id and not JobDataService.jd_dao.get_zone_by_id(schema.zone_id, session):
        return restResult.fail("请选择正确的岗位区域")

    payload = schema.model_dump(exclude={"reanalyze"}, exclude_none=True)
    try:
        ret = JobDataService.update_jd(jd, session, current_user, commit=False, **payload)
        if ret.is_fail:
            raise DataProcessingException(ret.msg, jd)
        if schema.reanalyze:
            ret = JobDataService.delete_jd_attachments(jd, session, current_user, commit=False)
            if ret.is_fail:
                raise DataProcessingException(ret.msg, jd)
            analytic_jd.apply_async(kwargs={"jd_id": str(schema.jd_id)})
            # ret = await JobDataService.sync_analytic_jd(jd, session, commit=False)
            # if ret.is_fail:
            #     raise DataProcessingException(ret.msg, jd)
        session.commit()
        return restResult.success()
    except DataProcessingException:
        session.rollback()
        raise


@jd_router.get("/zone/list", dependencies=[Depends(depend.has_logged)], description="获取地址区域List")
async def zone_list(session: Session = Depends(depend.get_db)):
    data = JobDataService.jd_dao.list_jd_zone(session)
    return restResult.success(data=data)


@jd_router.post("/ana/debug", dependencies=[Depends(depend.require_api_key)], description="调试调用")
async def analyze_debug(request: Request, session: Session = Depends(depend.get_db)):
    results = session.query(JobDataModel).all()
    debug = request.query_params.get("debug", False)
    for i in results:
        if i.keyword_summary is not None:
            continue
        analytic_jd.apply_async(kwargs={"jd_id": i.id})
        print(f"添加分析任务，{i}")
        if debug:
            break
    return restResult.success(data=[i.memu() for i in results])
