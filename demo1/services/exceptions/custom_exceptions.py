class DataProcessingException(Exception):
    def __init__(self, message, exception_object):
        """此异常仅作为需要进行SqlAlchemy Rollback回滚时候抛出此异常"""
        self.message = message
        self._exception_object = f"{exception_object}"
        super().__init__(self.message)

    @property
    def exc_object(self):
        return self._exception_object
