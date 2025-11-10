from sqlalchemy.orm import Session
from starlette.requests import Request

import depend
from typing import Annotated

from fastapi import APIRouter, Form, UploadFile, Depends

from backgroup_task.analytic import Analytic
from services.service_celery_task import CeleryTaskService
from tools.rest_result import restResult

index_route = APIRouter(prefix="/index")


@index_route.post("/analytic/dcp", description="根据岗位描述信息进行大模型AI分析")
async def index_analytic_description(keywords: Annotated[str, Form()]):
    if not keywords:
        return restResult.fail("岗位描述参数异常")
    analytics_client = Analytic()
    analytics_result = analytics_client.resolve_jd(jd_info=keywords, index=2)
    return restResult.success(data=analytics_result)


@index_route.post("/analytic/file", description="根据岗位描述pdf文件进行大模型AI分析")
async def index_analytic_description(file: UploadFile):
    if not file:
        return restResult.fail("岗位描述参数异常")
    if not file.filename.endswith(".pdf"):
        return restResult.fail("当前仅支持PDF文件解析")
    analytics_client = Analytic()
    steam_bytes = await file.read()
    analytics_result = analytics_client.resolve_jd(jd_file_stream=steam_bytes, index=2)
    return restResult.success(data=analytics_result)


celery_task_service = CeleryTaskService()


@index_route.post("/bg/celery/callback", description="celery后台任务回调接口",
                  dependencies=[Depends(depend.require_api_key)])
async def celery_callback(request: Request, session: Session = Depends(depend.get_db)):
    return restResult.build_from_ret(await celery_task_service.dispatch(request, session))
