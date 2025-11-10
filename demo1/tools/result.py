import enum


class FailReasonEnum(enum.Enum):
    FAIL = 'FAIL'
    OK = 'OK'
    NOT_FOUND = 'NOT_FOUND'
    UNAUTHORIZED = 'UNAUTHORIZED'
    ERROR = 'ERROR'
    PARAM_ERROR = 'PARAM_ERROR'
    FORBIDDEN = 'FORBIDDEN'


class Result(object):
    def __init__(self, result: bool, msg: str = '', data: object = None, reason: FailReasonEnum = None):
        self.result = result
        self.msg = msg
        self.data = data
        self.reason = reason

    @staticmethod
    def ok(data: object = None, reason: FailReasonEnum = FailReasonEnum.OK):
        return Result(True, msg='OK', data=data, reason=reason)

    @staticmethod
    def fail(msg: str, data: object = None, reason: FailReasonEnum = FailReasonEnum.FAIL):
        return Result(False, msg, data=data, reason=reason)

    def serialize(self):
        return {"result": self.result, "msg": self.msg, "data": self.data, "reason": self.reason.value}

    @property
    def is_ok(self):
        return self.result is True

    @property
    def is_fail(self):
        return self.result is False

    def __repr__(self):
        return str(self.__dict__)

