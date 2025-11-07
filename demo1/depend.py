from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request

from model.model_user import AdminUserModel
from model.database import SessionLocal
from schema.user_schemas import AdminUser
from settings import setting
from tools.gcs import GCSClient
from services.service_user import UserService
from schema.token_schema import TokenData


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# gcs_client = None
gcs_client = GCSClient()


def get_gcs():
    return gcs_client


def require_api_key(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate X-API-KEY",
        headers={"X-API-Key-Authenticate": "error"},
    )
    try:
        x_api_key = request.headers.get("X-API-Key")
        if not x_api_key or x_api_key != setting.X_API_KEY:
            raise credentials_exception
    except KeyError:
        raise credentials_exception


def has_logged(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        _r: TokenData = request.state.__getattr__("authorization")
        return _r
    except AttributeError:
        raise credentials_exception


token_data = has_logged


def current_user(request: Request):
    _token_data = has_logged(request)
    with SessionLocal() as session:
        return UserService.get_current_user_by_token(_token_data.access_token, session)


def admin_user(request: Request):
    _token_data = has_logged(request)
    with SessionLocal() as session:
        user = session.query(AdminUserModel).filter(AdminUserModel.id == _token_data.id).first()
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate administrator credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        disabled_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Available user account",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if not user:
            raise credentials_exception
        if user.disabled:
            raise disabled_exception
        return AdminUser(
            access_token=_token_data.access_token,
            token_type=_token_data.token_type,
            id=user.id,
            account=user.account,
            is_super=user.is_super
        )


def super_admin(request: Request):
    user = admin_user(request)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate super-administrator credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not user.is_super:
        raise credentials_exception
    return user


