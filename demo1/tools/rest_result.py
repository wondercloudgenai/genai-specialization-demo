import enum
from http import HTTPStatus as hs

__all__ = ['RestResult', 'restResult']

from tools.result import Result, FailReasonEnum


class CustomStatus(enum.IntEnum):

    def __new__(cls, value, description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class RestResult:

    FAIL_CODE = 1001

    def __init__(self, code: int, msg: str = '', data: object = None):
        self.code = code
        self.msg = msg
        self.data = data

    @staticmethod
    def success(data: object = None):
        return RestResult(hs.OK.value, "ok", data)

    @staticmethod
    def not_found(msg: str = 'Request resource not found.'):
        return RestResult(hs.NOT_FOUND.value, msg, None)

    @staticmethod
    def unauthorized(msg: str = hs.UNAUTHORIZED.description):
        return RestResult(hs.UNAUTHORIZED.value, msg, None)

    @staticmethod
    def forbidden(msg: str = hs.FORBIDDEN.description):
        return RestResult(hs.UNAUTHORIZED.value, msg, None)

    @staticmethod
    def error(msg: str = hs.INTERNAL_SERVER_ERROR):
        return RestResult(hs.INTERNAL_SERVER_ERROR.value, msg, None)

    @staticmethod
    def validate_error(msg: str = hs.UNPROCESSABLE_ENTITY.description):
        return RestResult(hs.UNPROCESSABLE_ENTITY, msg, None)

    @staticmethod
    def fail(msg: str = ''):
        return RestResult(RestResult.FAIL_CODE, msg, None)

    @staticmethod
    def build_from_ret(ret: Result, error_msg="", success_msg=""):
        if ret.is_fail:
            em = str(ret.msg) if not error_msg else error_msg
            if ret.reason == FailReasonEnum.UNAUTHORIZED:
                return RestResult.unauthorized(em)
            elif ret.reason == FailReasonEnum.FORBIDDEN:
                return RestResult.forbidden(em)
            elif ret.reason == FailReasonEnum.ERROR:
                return RestResult.error(em)
            elif ret.reason == FailReasonEnum.NOT_FOUND:
                return RestResult.not_found(em)
            elif ret.reason == FailReasonEnum.PARAM_ERROR:
                return RestResult.validate_error(em)
            else:
                return RestResult.fail(em)
        r = RestResult.success(data=ret.data)
        if success_msg:
            r.msg = success_msg
        return r


restResult = RestResult
