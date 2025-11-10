import enum
import re
from typing import Literal, Union, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from schema.token_schema import Token


class UserLoginForm(BaseModel):
    account: str = Field(min_length=3, max_length=30, description="登录用户名")
    password: str


USER_REGISTER_ACCOUNT_PATTERN = r"^[0-9a-zA-Z_.@]{3,20}$"
USER_REGISTER_PASSWORD_PATTERN = r"^(?!([0-9]*|[A-Za-z]*|[@!#%?.*]*)$)[0-9a-zA-Z@!#%?.*]{8,20}$"


class UserRegisterForm(BaseModel):
    account: str = Field(description="账户名只能由数字、字母和符号_.@组成，且长度3-20")
    contact: Union[str, None, EmailStr] = Field(default=None, description="手机号码或者邮箱")
    password: str = Field(description="密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20")
    # password_confirm: str
    captcha: str = None
    company_name: str
    company_scale: Literal[1, 2, 3, 4, 5, 6] = None
    company_type: str = None
    company_introduction: str = None

    @field_validator("account")
    def validate_account(cls, v):
        if not re.match(USER_REGISTER_ACCOUNT_PATTERN, v):
            raise ValueError("账户名只能由数字、字母和符号_.@组成，且长度3-20")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        if not re.match(USER_REGISTER_PASSWORD_PATTERN, v):
            raise ValueError("密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20")
        return v


class CurrentUser(Token):
    id: str
    account: str
    email: Union[EmailStr, str] = ""
    display_name: Optional[str] = ""
    company_id: Optional[str] = None

    def __str__(self):
        return f"CurrentUser<id={self.id}, account={self.account}, company_id={self.company_id}>"


class AdminUser(Token):
    id: str
    account: str
    is_super: bool

    def __str__(self):
        return f"AdminUser<id={self.id}, account={self.account}, is_super={self.is_super}>"


class UserInfo(CurrentUser):

    class Config:
        orm_mode = True


class UserResetPwdSchema(BaseModel):
    password: str = Field(
        min_length=8,
        max_length=20,
        pattern=re.compile(r"^(?!([0-9]*|[A-Za-z]*|[@!#%?.*]*)$)[0-9a-zA-Z@!#%?.*]{8,20}$"),
        description="密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20"
    )
    contact: Union[str, EmailStr] = Field(description="手机号码或者邮箱")
    captcha: str


class UserModifyPwdSchema(BaseModel):
    new_password: str = Field(
        min_length=8,
        max_length=20,
        pattern=re.compile(r"^(?!([0-9]*|[A-Za-z]*|[@!#%?.*]*)$)[0-9a-zA-Z@!#%?.*]{8,20}$"),
        description="密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20"
    )
    original_password: str


class UserUpdateSchema(BaseModel):
    display_name: Optional[str] = Field(default=None, description="用户显示名")
    email: Optional[EmailStr] = Field(default=None, description="用户绑定的邮箱")

    def __str__(self):
        return f"<UserUpdate(display_name={self.display_name}, email={self.email})>"

    # @classmethod
    # @field_validator("phone")
    # def validate_phone(cls, v):
    #     if not re.match(r"^1[3-9]\d{9}$", v):
    #         raise ValueError('"foobar" not found in a')
    #     return v


class UserUpdatePhoneSchema(BaseModel):
    phone: Optional[str] = Field(default=None, pattern=r"^1[3-9]\d{9}$", description="用户绑定的手机号")
    captcha: str = Field(default=None, description="更新邮箱或者手机号时接收的验证码")


class CompanyUpdateSchema(BaseModel):
    company_name: Optional[str] = Field(default=None, description="用户的公司名")
    company_scale: Literal[1, 2, 3, 4, 5, 6] = Field(default=None, description="用户的公司规模")
    company_type: str = Field(default=None, description="用户的公司类型")
    company_introduction: str = Field(default=None, description="用户的公司介绍")


class TokenRestrictionStrategyModeEnum(enum.Enum):
    FORCED_OFFLINE: str = "FORCED_OFFLINE"
    LIMIT_NUMBER_ONLINE: str = "LIMIT_NUMBER_ONLINE"


if __name__ == '__main__':
    print(re.match(r"^(?!([0-9]*|[A-Za-z]*|[@!#%?.*])$)[0-9a-zA-Z@!#%?.*]{8,20}$", "12345qwe"))
