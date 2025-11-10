from pydantic import BaseModel


class PageInfo:

    def __init__(self, page_number=1, page_size=10):
        self.page_number = page_number
        self.page_size = page_size

    def normal(self):
        if self.page_number < 1:
            self.page_number = 1
        if self.page_size > 50:
            self.page_size = 50
        return {
            "page_number": self.page_number,
            "page_record_number": self.page_size
        }


