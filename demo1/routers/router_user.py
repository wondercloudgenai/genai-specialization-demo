from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Annotated

import depend
from schema import user_schemas
from schema.token_schema import TokenData
from schema.user_schemas import *
from depend import get_db
from services.service_cvinfo import CvInfoService
from services.service_user import UserService
from tools.rest_result import RestResult

user_router = APIRouter(prefix="/user", tags=["User"])


@user_router.post("/register/captcha", description="用户注册时发送验证码接口")
async def send_register_captcha(phone: Annotated[str, Body(embed=True)],
                                session: Session = Depends(get_db)):
    result = await UserService.send_register_captcha(phone, session)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.post("/reset/pwd/captcha", description="用户重置密码发送验证码接口")
async def send_reset_pwd_captcha(phone: Annotated[str, Body(embed=True)],
                                 session: Session = Depends(get_db)):
    result = await UserService.send_reset_pwd_captcha(phone, session)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.post("/reset/pwd", description="用户重置密码接口")
async def reset_pwd_user(form_data: user_schemas.UserResetPwdSchema,
                         session: Session = Depends(get_db)):
    result = await UserService.reset_password(form_data, session)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.post("/modify/pwd", description="用户修改密码接口")
async def reset_pwd_user(form_data: user_schemas.UserModifyPwdSchema,
                         session: Session = Depends(get_db),
                         current_user: CurrentUser = Depends(depend.current_user)):
    result = await UserService.modify_password(form_data, session, current_user)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.post("/register/account/chk", description="用户检查注册Account有效性接口")
async def check_register_account(account: Annotated[str, Body(embed=True)],
                                 session: Session = Depends(get_db)):
    user = UserService.get_user_by_account(account, session)
    return RestResult.success(data=user is not None)


@user_router.post("/register", description="用户注册接口")
async def register_user(form_data: user_schemas.UserRegisterForm, session: Session = Depends(get_db)):
    result = await UserService.register(form_data, session)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.post("/login", description="用户登录接口")
async def login_for_access_token(form_data: user_schemas.UserLoginForm,
                                 session: Session = Depends(get_db)):
    result = await UserService.login(form_data, session)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.post("/logout", description="用户退出接口")
async def logout_for_access_token(current_user: CurrentUser = Depends(depend.current_user),
                                  session: Session = Depends(get_db)):
    result = await UserService.logout(current_user, session)
    if result.is_fail:
        return RestResult.fail(result.msg)
    return RestResult.success(data=result.data)


@user_router.get("/info/me", description="用户获取本人信息接口")
async def get_user_self_info(current_user: UserInfo = Depends(depend.current_user),
                             session: Session = Depends(depend.get_db)):
    return RestResult.success(data=UserService.get_current_user_info(current_user, session))


@user_router.get("/cmp/info/me", description="用户获取当前公司信息接口")
async def get_user_self_info(current_user: CurrentUser = Depends(depend.current_user),
                             session: Session = Depends(depend.get_db)):
    if not current_user.company_id:
        return RestResult.fail("当前用户未关联任何公司")
    data = UserService.get_current_user_company_info(current_user, session)
    if not data:
        return RestResult.fail("未查询到当前用户关联公司信息")
    if current_user.company_id:
        e = await CvInfoService.get_cv_count_via_company(current_user.company_id, session, current_user)
        data.update(e)
    return RestResult.success(data=data)


@user_router.post("/update/info", description="更新用户信息")
async def update_user(
    update_schema: UserUpdateSchema,
    current_user: UserInfo = Depends(depend.current_user),
    session: Session = Depends(depend.get_db)
):
    if update_schema.email:
        # 查询信绑定的邮箱是否已经被别人绑定
        u = UserService.get_user(update_schema.email, session)
        if u is not None and u.id != current_user.id:
            return RestResult.fail("当前邮箱已被TA人绑定")
    ret = UserService.update_current_user_infos(update_schema, current_user, session)
    return RestResult.build_from_ret(ret)


@user_router.post("/update/company/info", description="更新用户当前公司信息")
async def update_company_info(
    update_schema: CompanyUpdateSchema,
    current_user: UserInfo = Depends(depend.current_user),
    session: Session = Depends(depend.get_db)
):
    ret = UserService.update_current_user_company(update_schema, current_user, session)
    return RestResult.build_from_ret(ret)
