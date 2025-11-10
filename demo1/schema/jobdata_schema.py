import enum
import typing

from fastapi import UploadFile
from pydantic import BaseModel, Field, field_validator
from typing import List, Union, Literal

from schema.cvinfo_schema import CVOriginSchema


class JobDataSchema(BaseModel):
    # company_id: str
    name: str
    zone_id: str
    responsibilities: str = Field(default="", max_length=1200, description="工作职责，长度不能超过1200")
    work_info: str = Field(default="", max_length=1200, description="工作内容，长度不能超过1200")
    work_request: str = Field(default="", max_length=1200, description="岗位要求，长度不能超过1200")

    def __repr__(self):
        return (f"JobData(name={self.name}, zone={self.zone_id}, responsibilities={self.responsibilities[:100]}..., "
                f"work_info={self.work_info[:100]}..., work_request={self.work_request[:100]}...)")


class JobDataSummarySchema(BaseModel):
    jd_id: str
    summary: str


class JobDataKeywordItemSchema(BaseModel):
    id: str = None
    key_word: str
    weight: float
    status: bool = True


class JobDataKeywordSchema(BaseModel):
    jd_id: str
    keywords: List[JobDataKeywordItemSchema]


class JobDataAnalyticSchema(BaseModel):
    jd_id: str
    keyword_summary: str
    job_summary: str

    def __str__(self):
        return (f"JobDataAnalytic<jd_id={self.jd_id}, keyword_summary={self.keyword_summary[:100]}..., "
                f"job_summary={self.job_summary[:100]}...>")


class SearchTaskSchema(BaseModel):
    search_id: str
    success_number: int


class SearchTaskStartSchema(BaseModel):
    jd_id: str
    search_number: int = 100
    extra: typing.Optional[dict] = {}
    origin: str


class SearchTask51EhireStartSchema(SearchTaskStartSchema):
    ehire_member: str
    ehire_username: str
    ehire_password: str


class JobDataSummaryAnalyticSchema(BaseModel):
    job_description_file: typing.Optional[UploadFile]
    job_description_str: typing.Optional[str]


class SearchTaskCallbackSchema(BaseModel):
    jd_id: str
    task_id: str
    status: str
    reason: str
    search_total: int = 0
    success_upload: int = 0


class JobDataCandidateSchema(BaseModel):
    cv_id: str


class JobDataRenameSchema(BaseModel):
    name: str
    jd_id: str


class JobDataUpdateSchema(BaseModel):
    name: str = Field(default=None, description="职位名")
    jd_id: str
    zone_id: str = Field(default=None, description="职位区域")
    responsibilities: str = Field(default=None, max_length=1200, description="工作职责，长度不能超过1200")
    work_info: str = Field(default=None, max_length=1200, description="工作内容，长度不能超过1200")
    work_request: str = Field(default=None, max_length=1200, description="岗位要求，长度不能超过1200")
    reanalyze: bool = Field(default=False)            # 是否对岗位重新分析


class CreateAnalyzeChatSessionSchema(BaseModel):
    jd_id: str = Field(description="需要分析的岗位Id")
    # scope: str = Field(description="需要分析的简历范围，当前未使用", default=None)
    mode: Literal["Pan-Mode", "Context-Mode", "Overlay-Mode"] = "Pan-Mode"


class JobDataSearchTaskStatusEnum(enum.Enum):
    waiting = "Waiting"
    starting = "Starting"
    failed = "Failed"
    success = "Success"
