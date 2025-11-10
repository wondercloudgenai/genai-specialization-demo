from pydantic import BaseModel
from typing import List, Union, Dict

class ResponseSchema(BaseModel):
    status: int = 20000
    msg: str = ""
    data: Union[List, Dict, str] = []

