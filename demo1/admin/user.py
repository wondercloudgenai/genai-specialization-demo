import re
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Body
from sqlalchemy import func
from sqlalchemy.orm import Session

from model.model_user import AdminUserModel
from curd import UserDAO
import depend
from extentions import logger
from model import UserModel, users_companies_table, CVInfoUploadModel
from schema.page_schema import PageInfo
from schema.token_schema import Token
from schema.user_schemas import AdminUser
from services.middlewares.token_session import TokenSession
from services.service_user import UserService
from settings import setting
from tools.rest_result import restResult
from schema import user_schemas

admin_user_router = APIRouter(prefix="/adm/user", tags=["admin"])


@admin_user_router.get("/list/2", dependencies=[Depends(depend.super_admin)], description="获取所有管理员列表")
async def admin_user_list(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    fuzzy_search_key: str = "",
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(AdminUserModel)
    if fuzzy_search_key != "":
        query = query.filter(AdminUserModel.account.like(f"%{fuzzy_search_key}%"))
    query = query.order_by(AdminUserModel.create_time.desc())
    return restResult.success(data=UserDAO.page_data(query, page, "sample"))


@admin_user_router.get("/list/1", dependencies=[Depends(depend.admin_user)], description="获取所有用户列表，支持模糊搜索")
async def user_list(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    fuzzy_search_key: str = "",
    company_id: str = ""
):
    page = PageInfo(page_number, page_record_number)
    subquery_upload_cvs_count = session.query(func.count(CVInfoUploadModel.id)).filter(
        CVInfoUploadModel.uploader_id == UserModel.id).correlate(UserModel).label("upload_cvs_count")
    query = session.query(UserModel, subquery_upload_cvs_count).filter(UserModel.is_delete == False)
    if fuzzy_search_key != "":
        query = query.filter(UserModel.account.like(f"%{fuzzy_search_key}%"))

    if company_id:
        query = query.join(users_companies_table, UserModel.id == users_companies_table.c.user_id
                           ).filter(users_companies_table.c.company_id == company_id)
    query = query.order_by(UserModel.create_time.desc())

    results = query.offset((page.page_number - 1) * page.page_size).limit(page.page_size)

    r = []
    for result in results:
        user_model, upload_cvs_count = result
        var1 = user_model.sample()
        var1.update({"disabled": user_model.disabled})
        var1.update({"upload_cvs_count": upload_cvs_count})
        r.append(var1)

    data = {
        "data": r,
        "total": query.count(),
        "page_number": page.page_number,
        "page_record_number": page.page_size,
    }
    return restResult.success(data=data)


@admin_user_router.post("/disable/1", description="禁用/解禁用户", dependencies=[Depends(depend.admin_user)])
async def user_disable(
    user_id: Annotated[str, Body(embed=True)],
    disabled: Annotated[bool, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    user: UserModel = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        return restResult.fail("用户不存在")
    if disabled and user.disabled:
        return restResult.fail("当前用户已是禁用状态")
    if disabled is False and not user.disabled:
        return restResult.fail("当前用户已是非禁用状态")
    user.disabled = disabled
    session.commit()
    logger.info(f"更新用户{user}状态：disabled={disabled}")
    return restResult.success()


@admin_user_router.post("/disable/2", description="禁用/解禁管理员用户", dependencies=[Depends(depend.super_admin)])
async def user_disable(
    user_id: Annotated[str, Body(embed=True)],
    disabled: Annotated[bool, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    user: AdminUserModel = session.query(AdminUserModel).filter(AdminUserModel.id == user_id).first()
    if not user:
        return restResult.fail("用户不存在")
    if user.is_super:
        return restResult.fail("超管用户不允许禁用")
    if disabled and user.disabled:
        return restResult.fail("当前用户已是禁用状态")
    if disabled is False and not user.disabled:
        return restResult.fail("当前用户已是非禁用状态")
    user.disabled = disabled
    session.commit()
    logger.info(f"更新管理员用户{user}状态：disabled={disabled}")
    return restResult.success()


@admin_user_router.post("/login", description="管理员登录")
async def user_login(
    account: Annotated[str, Body(embed=True)],
    password: Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    user_model: AdminUserModel = session.query(AdminUserModel).filter(AdminUserModel.account == account).first()
    if not user_model:
        logger.error(f"管理员{account}登陆失败，用户不存在")
        return restResult.fail("管理员用户不存在")
    if user_model.disabled:
        logger.error(f"管理员{account}登陆失败，用户已被禁用")
        return restResult.fail("管理员用户已被禁用")
    verify_result = UserService.verify_password(password, user_model.password)
    if not verify_result:
        logger.error(f"管理员{account}登陆失败，用户密码验证失败")
        return restResult.fail("管理员用户密码不正确")
    expires_seconds = setting.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token_expires = timedelta(seconds=expires_seconds)
    access_token = UserService.create_access_token(
        data={"sub": user_model.account, "id": user_model.id, "adm": True},
        expires_delta=access_token_expires
    )

    try:
        # cache access token
        token_session = TokenSession.get_instance(access_token)
        if not token_session.create(expires_seconds):
            return restResult.fail("登录失败，服务器异常")
        session.commit()
    except Exception as e:
        raise e
    logger.info(f"管理员{user_model}登陆成功")
    return restResult.success(data=Token(access_token=access_token, token_type="bearer"))


@admin_user_router.post("/logout", description="管理员登出")
async def user_logout(
    current_user: AdminUser = Depends(depend.admin_user),
):
    token_session = TokenSession.get_instance(current_user.access_token)
    if not token_session.disable_token():
        return restResult.fail("登出失败，服务器异常")
    logger.info(f"管理员{current_user}登出成功")
    return restResult.success()


@admin_user_router.post("/reset/pwd", description="超管账户重置普通管理员密码", dependencies=[Depends(depend.super_admin)])
async def user_reset_pwd(
    user_id: Annotated[str, Body(embed=True)],
    new_password: Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    user_model: AdminUserModel = session.query(AdminUserModel).filter(AdminUserModel.id == user_id).first()
    if not user_model:
        return restResult.fail("用户不存在")
    if user_model.is_super:
        return restResult.fail("不能重置超管账户密码")
    if not re.match(user_schemas.USER_REGISTER_PASSWORD_PATTERN, new_password):
        return restResult.fail("密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20")
    user_model.password = UserService.get_password_hash(new_password)
    session.add(user_model)
    session.commit()
    logger.info(f"重置普通管理员{user_model}密码成功")
    TokenSession.disable_user("adm~~" + user_model.account)
    return restResult.success()


@admin_user_router.post("/modify/pwd", description="普通管理员修改自己的密码")
async def user_modify_pwd(
    old_password: Annotated[str, Body(embed=True)],
    new_password: Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
    current_user: AdminUser = Depends(depend.admin_user)
):
    user_model: AdminUserModel = session.query(AdminUserModel).filter(AdminUserModel.id == current_user.id).first()
    if not user_model:
        return restResult.fail("用户不存在")
    if not UserService.verify_password(old_password, user_model.password):
        return restResult.fail("原密码不正确")
    if UserService.verify_password(new_password, user_model.password):
        return restResult.fail("新密码与原密码相同")
    if not re.match(user_schemas.USER_REGISTER_PASSWORD_PATTERN, new_password):
        return restResult.fail("密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20")
    # 先强制下线已登录的账号,
    user_model.password = UserService.get_password_hash(new_password)
    session.add(user_model)
    ret, _ = TokenSession.disable_user("adm~~" + user_model.account)
    if not ret:
        session.rollback()
        return restResult.fail(f"预强制下线账号失败")
    session.commit()
    logger.info(f"管理员{user_model}修改密码成功")
    return restResult.success()


@admin_user_router.post("/create", description="新增管理员", dependencies=[Depends(depend.super_admin)])
async def create_user(
    account: Annotated[str, Body(embed=True)],
    password: Annotated[str, Body(embed=True)],
    session: Session = Depends(depend.get_db),
):
    if not re.match(user_schemas.USER_REGISTER_ACCOUNT_PATTERN, account):
        return restResult.fail("账户名只能由数字、字母和符号_.@组成，且长度3-20")
    if not re.match(user_schemas.USER_REGISTER_PASSWORD_PATTERN, password):
        return restResult.fail("密码至少包含数字、字母及特殊符号@!#%?.*的两种组合，且长度8-20")
    user_model = session.query(AdminUserModel).filter(AdminUserModel.account == account).first()
    if user_model:
        return restResult.fail("用户已存在")
    user_model = AdminUserModel(account=account, password=UserService.get_password_hash(password))
    session.add(user_model)
    session.commit()
    logger.info(f"管理员{user_model}创建成功")
    return restResult.success()


@admin_user_router.delete("/{user_id}/1", description="删除用户", dependencies=[Depends(depend.admin_user)])
async def delete_user(
    user_id: str,
    session: Session = Depends(depend.get_db),
):
    user_model: UserModel = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user_model:
        return restResult.fail("此用户账户不存在")
    user_model.is_delete = True
    session.add(user_model)
    user_model_str = f"{user_model}"
    session.commit()
    logger.info(f"注销账号{user_model_str}成功")
    return restResult.success()


@admin_user_router.delete("/{user_id}/2", description="删除管理员用户", dependencies=[Depends(depend.super_admin)])
async def delete_user(
    user_id: str,
    session: Session = Depends(depend.get_db),
):
    user_model: AdminUserModel = session.query(AdminUserModel).filter(AdminUserModel.id == user_id).first()
    if not user_model:
        return restResult.fail("此管理员账户不存在")
    if user_model.is_super:
        return restResult.fail("超管账户不能删除")
    session.delete(user_model)
    session.commit()
    logger.info(f"注销管理员账号{user_model}成功")
    return restResult.success()


@admin_user_router.get("/info", description="获取当前登录管理员信息")
async def get_current_user_info(
    current_user: AdminUser = Depends(depend.admin_user),
    session: Session = Depends(depend.get_db),
):
    user_model: AdminUserModel = session.query(AdminUserModel).filter(AdminUserModel.id == current_user.id).first()
    if not user_model:
        return restResult.fail("用户不存在")
    return restResult.success(data=user_model.sample())
