from fastapi import APIRouter
from routers.router_cvinfo import cv_route
from routers.router_jobdata import jd_router
from routers.router_candidate import candidate_route
from routers.router_user import user_router
from routers.router_index import index_route
from routers.router_ws import ws_router
from routers.router_interview_eva import interview_eva_route
from routers.router_boss_zhipin import boss_zhipin_route
from settings import setting

api_route = APIRouter()
api_route.include_router(user_router, tags=["User"], prefix=setting.api_prefix_path)

api_route.include_router(jd_router, tags=["Job"], prefix=setting.api_prefix_path)
api_route.include_router(cv_route, tags=["CV"], prefix=setting.api_prefix_path)
api_route.include_router(candidate_route, tags=["Candidate"], prefix=setting.api_prefix_path)
api_route.include_router(index_route, tags=["Index"], prefix=setting.api_prefix_path)
api_route.include_router(ws_router, tags=["WebSocket"], prefix=setting.api_prefix_path)
api_route.include_router(interview_eva_route, tags=["面试评价"], prefix=setting.api_prefix_path)
api_route.include_router(boss_zhipin_route, tags=["boss直聘扫码登录"], prefix=setting.api_prefix_path)
