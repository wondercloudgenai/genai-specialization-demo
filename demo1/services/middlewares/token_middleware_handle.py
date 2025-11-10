from fastapi import FastAPI
from fastapi.security.utils import get_authorization_scheme_param
from starlette.exceptions import HTTPException
from starlette.requests import Request
from services.service_user import UserService


def register_token_middleware(app: FastAPI):
    @app.middleware("http")
    async def request_login_intercept(request: Request, call_next):
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            response = await call_next(request)
            return response
        try:
            token_data = UserService.check_token(token)
            request.state.authorization = token_data
        except HTTPException:
            ...
        response = await call_next(request)
        return response
