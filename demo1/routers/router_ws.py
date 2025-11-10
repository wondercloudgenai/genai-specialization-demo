import asyncio
import json
import typing
import uuid

from sqlalchemy import text

import depend

from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from fastapi import WebSocket, APIRouter, Depends, WebSocketDisconnect, WebSocketException, status

from backgroup_task.main import text_embedding, analyze_chat_cvs
from extentions import logger
from model import JobDataModel
from model.database import SessionLocal
from schema.cvinfo_schema import CVOriginSchema
from schema.user_schemas import CurrentUser
from services.service_cvinfo import CvInfoService
from services.service_jobdata import JobDataService
from services.service_user import UserService

ws_router = APIRouter(prefix="/ws")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, websocket: WebSocket, client_id):
        self.active_connections.pop(client_id)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_personal_json(self, data, websocket: WebSocket):
        await websocket.send_json(data)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)


manager = ConnectionManager()


async def ws_authenticate(token: str):
    try:
        if token.lower().startswith("bearer"):
            _, token = get_authorization_scheme_param(token)
        with SessionLocal() as session:
            current_user: CurrentUser = UserService.get_current_user_by_token(token, session)
            yield current_user
    except HTTPException as e:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Could not validate credentials")


async def get_text_embedding(text: str):
    celery_task = text_embedding.apply_async(args=(text, ))
    while not celery_task.ready():
        await asyncio.sleep(0.5)  # 定时检查任务状态
        # 任务完成，通过 WebSocket 发送结果
    ret = celery_task.result
    return ret


async def get_analytic_cvs(msg: str, cvs: str, job_info: str):
    celery_task = analyze_chat_cvs.apply_async(args=(msg, cvs, job_info, ))
    while not celery_task.ready():
        await asyncio.sleep(0.5)  # 定时检查任务状态
        # 任务完成，通过 WebSocket 发送结果
    ret = celery_task.result
    return ret


@ws_router.websocket("/jd-chat")
async def websocket_endpoint(
    websocket: WebSocket,
    jd_id: str,
    mode: typing.Literal["Pan-Mode", "Context-Mode", "Overlay-Mode"] = "Pan-Mode",
    current_user: CurrentUser = Depends(ws_authenticate),
    session: Session = Depends(depend.get_db)
):
    ret = JobDataService.valid_jd(jd_id, session, current_user, check_user=True)
    if ret.is_fail:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="创建会话失败，" + ret.msg)
    jd: JobDataModel = ret.data
    client_id = uuid.uuid4().hex
    await manager.connect(websocket, client_id)
    logger.info(f"{current_user}, ClientId={client_id} connected, {jd}")

    try:
        while True:
            receive_text = await websocket.receive_text()
            if not receive_text or len(receive_text.strip()) <= 0:
                await manager.send_personal_message("ERR:" + "Empty message", websocket)
                continue
            embedding = await get_text_embedding(receive_text)
            if not embedding:
                await manager.send_personal_message("ERR:" + "服务器异常", websocket)
                continue
            try:
                cvs = await get_jd_cvs_via_embedding(embedding, jd.id, session)
                logger.info(f"Websocket【ClientId={client_id}】，Msg: {receive_text}，过滤出简历数量: {len(cvs)}")
                if cvs:
                    _c = []
                    for cv in cvs:
                        if cv["origin"] == CVOriginSchema.SPIDER_BOSS.value:
                            _c.append({
                                    "cv_id": cv["v1_cv_id"],
                                    "meta_json": json.dumps(cv["meta_json"], ensure_ascii=False),
                                    "origin": cv["origin"]
                                })
                        else:
                            _c.append({
                                "cv_id": cv["v1_cv_id"],
                                "gcs_path": cv["gcs_save_path"],
                                "origin": cv["origin"]
                            })
                    payload = {
                        "msg": receive_text,
                        "cvs": _c,
                        "job_info": jd.summary.summary if jd.summary and jd.summary.summary else jd.name,
                    }
                    ret = await get_analytic_cvs(**payload)
                    if ret["result"]:
                        data = ret["data"]
                        cvs_ids = [i["key"] for i in data]
                        s = CvInfoService.cv_dao.get_cvs(cvs_ids, session)
                        if len(s) == len(data):
                            s.sort(key=lambda x: x.id)
                            data.sort(key=lambda x: x["key"])
                            for idx, item in enumerate(data):
                                item["name"] = s[idx].origin_cv.name
                                item["cv_id"] = item.pop("key")

                        await manager.send_personal_json(data, websocket)
                    else:
                        await manager.send_personal_message("ERR:" + ret["msg"], websocket)
                else:
                    await manager.send_personal_json([], websocket)
            except Exception as e:
                logger.error(e)
                await manager.send_personal_message("ERR:" + "服务器异常", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        logger.info(f"{current_user}, websocket={websocket} disconnected")


async def get_jd_cvs_via_embedding(embedding: str, jd_id: str, session: Session):
    return await CvInfoService.get_jd_cvs_via_embedding(embedding, jd_id, session, limit=200)



