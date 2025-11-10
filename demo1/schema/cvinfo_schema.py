import enum
import typing

from pydantic import BaseModel
from typing import List, Union


class CVMetadataKeywordSchema(BaseModel):
    key: str
    value: str


class CVMetadataAttachSchema(BaseModel):
    cv_id: str
    cv_metadata: CVMetadataKeywordSchema


class CVInfoSchema(BaseModel):
    jd_id: str
    save_path: str
    source: str
    cv_metadata: List[CVMetadataKeywordSchema] = None


class CVInfoIDSchema(BaseModel):
    cv_id: str


class CVinfoAnalyzeSchema(CVInfoIDSchema):
    suitability: float
    reason: str
    advantages: List
    disadvantages: List

    def __str__(self):
        return f"CVinfoAnalyzeSchema<cv_id={self.cv_id}, suitability={self.suitability}>"


class CVSentenceEmbeddingSchema(BaseModel):
    cv_id: str
    sentence: str
    embedding: list

    def __str__(self):
        return (f"CVSentenceEmbeddingSchema<resume_id={self.cv_id}, sentence={self.sentence}>,"
                f" embedding={self.embedding[:10]}...")


class CVKeywordEmbeddingSchema(BaseModel):
    cv_id: str
    keyword: str
    embedding: list

    def __str__(self):
        return (f"CVKeywordEmbeddingSchema<resume_id={self.cv_id}, keyword={self.keyword}>,"
                f" embedding={self.embedding[:10]}...")


class CVOriginSchema(enum.Enum):
    SPIDER_EHIRE: str = "ehire"
    SPIDER_BOSS: str = "boss"
    VECTOR: str = "vector"
    V2_UPLOAD: str = "v2_upload"
    V1_UPLOAD: str = "v1_upload"


class CVUpdateSchema(BaseModel):
    cv_id: str
    analyze_status: typing.Literal[-1, 0, 1]
