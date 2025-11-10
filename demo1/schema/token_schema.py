from pydantic import BaseModel
from typing import Union


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(Token):
    adm: bool = False
    sub: Union[str, None] = None
    id: str = ""

    @property
    def account(self):
        return self.sub if not self.adm else f"adm~~{self.sub}"
