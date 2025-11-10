from fastapi import APIRouter

from admin.company import admin_company_router
from admin.cvs import admin_cvs_router
from admin.job_data import admin_jd_router
from admin.user import admin_user_router
from settings import setting

admin_router = APIRouter()
admin_router.include_router(admin_company_router, prefix=setting.api_prefix_path)
admin_router.include_router(admin_cvs_router, prefix=setting.api_prefix_path)
admin_router.include_router(admin_jd_router, prefix=setting.api_prefix_path)
admin_router.include_router(admin_user_router, prefix=setting.api_prefix_path)
