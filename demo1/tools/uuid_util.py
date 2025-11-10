import uuid


class UUIDUtil(object):
    @staticmethod
    def generate():
        return uuid.uuid4().hex
