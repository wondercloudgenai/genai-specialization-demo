from fastapi import FastAPI
from fastapi.security.utils import get_authorization_scheme_param
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from extentions import logger


def register_log_middleware(app: FastAPI):
    @app.middleware("http")
    async def log_intercept(request: Request, call_next):
        log_message = f"{request.method}[{request.url.path}] ===<"
        try:
            # 处理 JSON 请求体
            if "application/json" in request.headers.get("content-type", ""):
                try:
                    json_body = await request.json()
                    json_body = json_body if len(str(json_body)) < 300 else str(json_body)[:300] + "..."
                    log_message += f" Json: {json_body}"
                except Exception as e:
                    log_message += f" Fail to parse JSON: {e}"

            log_message += f" Params: {request.query_params}, PathParams: {request.path_params}"
            logger.debug(log_message)

        except Exception as e:
            logger.debug(f"{request.method}[{request.url.path}] ===< Fail to load request parameters, {e}")

        # 获取响应体 (需要注意大型响应)
        response = await call_next(request)
        try:
            if response.headers["content-type"] == "application/json":
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                s = response_body[:512] + b'...' if len(response_body) > 512 else response_body

                # 重新构建响应，因为body_iterator只能迭代一次
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                logger.debug(f"{request.method}[{request.url.path}] ===> ResponseCode: {response.status_code} "
                             f"Response Body: {s.decode()}")  # 解码字节为字符串
            else:
                logger.debug(f"{request.method}[{request.url.path}] ===> ResponseCode: {response.status_code}")
        except Exception as e:
            logger.debug(f"Failed to read response body: {e}")
        return response
