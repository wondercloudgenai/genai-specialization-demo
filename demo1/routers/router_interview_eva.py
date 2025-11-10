import mimetypes
import typing
from uuid import uuid4

from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse, FileResponse

import depend

from fastapi import APIRouter, Form, UploadFile, Depends

from backgroup_task.main import interview_eva
from extentions import logger
from model.model_interview_evaluation import InterviewEvaTemplateModel, InterviewEvaResultModel
from schema.page_schema import PageInfo
from schema.user_schemas import CurrentUser
from services.service_interview_eva import InterviewEvaService
from settings import setting
from tools.gcs import GCSClient
from tools.rest_result import restResult
from tools.uuid_util import UUIDUtil

interview_eva_route = APIRouter(prefix="/interview_eva")
interview_eva_service = InterviewEvaService()


@interview_eva_route.post("/template/upload", description="上传面试评价模板")
async def upload_interview_eva_template(
    template_file: UploadFile = Form(),
    session: Session = Depends(depend.get_db),
    current_user: CurrentUser = Depends(depend.current_user),
    gcs_client: GCSClient = Depends(depend.get_gcs)
):
    if template_file.size > 10 * 1024 * 1024 or template_file.content_type != "application/pdf":
        return restResult.fail("仅能上传小于10M, 且格式为PDF的面评模板")
    if template_file.size <= 0:
        return restResult.fail("面试评价模板内容为空")

    if interview_eva_service.get_interview_eva_template(
        session, user_id=current_user.id, template_name=template_file.filename
    ):
        return restResult.fail("已存在同名的面评模板")
    file_name = "{}/{}.pdf".format("interview_eva_template", uuid4().hex)
    status, msg = await gcs_client.upload(template_file, file_name)
    if status:
        gcs_path = f"gs://{setting.bucket_name}/{file_name}"
        template = InterviewEvaTemplateModel(
            name=template_file.filename, creator_id=current_user.id, save_path=gcs_path
        )
        session.add(template)
        session.commit()
        session.refresh(template)
        logger.info(f"{current_user}上传面评模板成功， {template}")
        return restResult.success(data=template.sample())
    return restResult.fail(msg="上传面评模板失败")


@interview_eva_route.get("/template/list", description="获取面试评价模板列表")
async def list_interview_eva_template(
    page_number: int = 1,
    page_record_number: int = 50,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db)
):
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    data = interview_eva_service.get_interview_eva_template_list(session, page, current_user.id)
    return restResult.success(data=data)


@interview_eva_route.delete("/template/{template_id}", description="删除面评模板")
async def delete_interview_eva_template(
    template_id: str,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db)
):
    template = interview_eva_service.get_interview_eva_template(session, template_id=template_id)
    if not template:
        return restResult.not_found("请求资源不存在")
    if template.creator_id != current_user.id:
        return restResult.forbidden("无权限访问")
    template_info = f"{template}"
    session.delete(template)
    session.commit()
    logger.info(f"{current_user}删除面评模板成功， {template_info}")
    return restResult.success()


@interview_eva_route.get("/template/view/{template_id}", description="预览/下载面评模板")
async def view_interview_eva_template(
    template_id: str,
    mode: typing.Literal["view", "download"] = "view",
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db),
    gcs_client: GCSClient = Depends(depend.get_gcs)
):
    template = interview_eva_service.get_interview_eva_template(session, template_id=template_id)
    if not template:
        return restResult.not_found("请求资源不存在")
    if template.creator_id != current_user.id:
        return restResult.forbidden("无权限访问")
    file_obj = gcs_client.download(gcs_client.get_filename_from_gcs_path(template.save_path))
    if mode == "download":
        headers = {
            'Content-Disposition': 'attachment; filename="{}"'.format(template.name)
        }
    else:
        headers = {
            'Content-Disposition': 'inline'
        }
    return StreamingResponse(file_obj, headers=headers, media_type="application/pdf")


@interview_eva_route.post("/start", description="生成面评")
async def start_interview_eva(
    template_id: str = Form(),
    content_file: UploadFile = Form(),
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db),
    gcs_client: GCSClient = Depends(depend.get_gcs)
):
    template = interview_eva_service.get_interview_eva_template(session, template_id=template_id)
    if not template:
        return restResult.not_found("面评模板不存在")
    if template.creator_id != current_user.id:
        return restResult.forbidden("无权限访问")
    file_suffix = content_file.filename.split(".")[-1]
    if "." not in content_file.filename or file_suffix.lower() not in ["pdf", "txt", "mp4"]:
        return restResult.fail("面评内容文件仅支持PDF、TXT、Mp4格式")
    file_name = "{}/{}.{}".format("interview_eva_content", uuid4(

    ).hex, file_suffix)
    status, msg = await gcs_client.upload(content_file, file_name)
    if status:
        gcs_path = f"gs://{setting.bucket_name}/{file_name}"
        _id = UUIDUtil.generate()
        instance = InterviewEvaResultModel(
            id=_id,
            template_id=template_id,
            payload_save_path=gcs_path,
            payload_filename=content_file.filename,
        )
        session.add(instance)
        session.commit()
        session.refresh(instance)
        interview_eva.apply_async(
            kwargs={"task_id": _id, "template_save_path": template.save_path, "content_save_path": gcs_path}
        )
        logger.info(f"{current_user}发起面评任务成功， {instance}")
        return restResult.success(data=_id)
    return restResult.fail(msg="面评任务生成失败")


@interview_eva_route.get("/result/list", description="获取面评结果列表")
async def get_interview_eva_result_list(
    page_number: int = 1,
    page_record_number: int = 50,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db),
):
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    data = interview_eva_service.get_interview_eva_result_list(session, page, current_user.id)
    return restResult.success(data=data)


@interview_eva_route.get("/result/{result_id}", description="获取面评结果数据")
async def get_interview_eva_result(
    result_id: str,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db),
):
    result = interview_eva_service.get_interview_eva_result(session, result_id)
    if not result:
        return restResult.not_found("请求资源不存在")
    if result.template.creator_id != current_user.id:
        return restResult.forbidden("无权限访问")
    return restResult.success(data=result.sample())


@interview_eva_route.get("/result/download/{result_id}", description="下载面评结果, 当前仅支持docx")
async def view_interview_eva_result(
    result_id: str,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db),
):
    result: InterviewEvaResultModel = interview_eva_service.get_interview_eva_result(session, result_id)
    if not result:
        return restResult.not_found("请求资源不存在")
    if result.template.creator_id != current_user.id:
        return restResult.forbidden("无权限访问")
    if result.status.lower() not in ["success"]:
        return restResult.fail("暂无面评结果")
    markdown_content = result.content
    ret = await interview_eva_service.convert_markdown_to_doc(markdown_content, result.id)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    converted_file_path = ret.data
    return FileResponse(converted_file_path, filename=f"{UUIDUtil.generate()}.docx")


@interview_eva_route.delete("/result/{result_id}", description="删除面评")
async def delete_interview_eva_result(
    result_id: str,
    current_user=Depends(depend.current_user),
    session=Depends(depend.get_db)
):
    result = interview_eva_service.get_interview_eva_result(session, result_id=result_id)
    if not result:
        return restResult.not_found("请求资源不存在")
    if result.template.creator_id != current_user.id:
        return restResult.forbidden("无权限访问")
    result_info = f"{result}"
    session.delete(result)
    session.commit()
    logger.info(f"{current_user}删除面评成功， {result_info}")
    return restResult.success()
