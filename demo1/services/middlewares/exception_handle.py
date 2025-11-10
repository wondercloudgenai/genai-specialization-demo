import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from http import HTTPStatus

from schema.user_schemas import TokenRestrictionStrategyModeEnum
from services.exceptions.custom_exceptions import DataProcessingException
from services.middlewares.token_session import TokenSessionError, TokenRestrictionStrategyError
from tools.rest_result import RestResult
logger = logging.getLogger("root")


def register_exception_handler(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request, exc: RequestValidationError):
        message = ""
        for error in exc.errors():
            message += ".".join([str(i) for i in error.get("loc")]) + ":" + error.get("msg") + ";"
        message = message.capitalize()
        return JSONResponse(RestResult.validate_error(message).__dict__,
                            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        return JSONResponse(RestResult(exc.status_code, str(exc), None).__dict__,
                            status_code=exc.status_code)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request, exc: SQLAlchemyError):
        logger.error(traceback.format_exc())
        logger.error("Request[url={}], ".format(request.url) + str(exc))
        return JSONResponse(RestResult.error("服务器异常").__dict__,
                            status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    @app.exception_handler(DataProcessingException)
    async def data_processing_exception_handler(request, exc: DataProcessingException):
        logger.error(traceback.format_exc())
        logger.error(f"Request[url={request.url}], 数据操作异常, 将启动Rollback, 对象：{exc.exc_object}, "
                     f"DataProcessingException: " + str(exc))
        return JSONResponse(RestResult.error(exc.message).__dict__,
                            status_code=HTTPStatus.OK)

    @app.exception_handler(TokenSessionError)
    async def token_exception_handler(request, exc: TokenSessionError):
        logger.error(traceback.format_exc())
        logger.error(f"Request[url={request.url}], 缓存数据操作异常, TokenSessionError: " + exc.message)
        return JSONResponse(RestResult.error("服务器异常").__dict__, status_code=HTTPStatus.OK)

    @app.exception_handler(TokenRestrictionStrategyError)
    async def token_restriction_exception_handler(request, exc: TokenRestrictionStrategyError):
        logger.error(traceback.format_exc())
        if exc.strategy == TokenRestrictionStrategyModeEnum.LIMIT_NUMBER_ONLINE:
            return JSONResponse(
                RestResult.forbidden("Exceeded the maximum number of simultaneous online users").__dict__,
            )
        logger.error(f"Request[url={request.url}], 缓存数据操作异常, {str(exc)}")
        return JSONResponse(RestResult.error("服务器异常").__dict__, status_code=HTTPStatus.OK)

    @app.exception_handler(Exception)
    async def runtime_exception_handler(request: Request, exc: Exception):
        request_json = await request.json()
        logger.error("Request[url={}, path_params={}, query_params={}, json_params={}]\n"
                     .format(request.url, request.path_params, request.query_params, request_json) + str(exc))
        return JSONResponse(RestResult.error().__dict__,
                            status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


