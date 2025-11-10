
from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from curd import CompanyDAO, JobDataDao
import depend
from extentions import logger
from model import UserModel, CompanyModel, users_companies_table, JobDataModel
from schema.page_schema import PageInfo
from schema.user_schemas import AdminUser
from tools.rest_result import restResult

admin_company_router = APIRouter(prefix="/adm/company", tags=["admin"])


@admin_company_router.get("/list", dependencies=[Depends(depend.admin_user)],
                          description="获取所有公司列表，支持模糊搜索")
async def company_list(
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    fuzzy_search_key: str = "",
):
    page = PageInfo(page_number, page_record_number)
    query = session.query(CompanyModel)
    if fuzzy_search_key != "":
        query = query.filter(CompanyModel.name.like(f"%{fuzzy_search_key}%"))
    query = query.order_by(CompanyModel.create_time.desc())
    return restResult.success(data=CompanyDAO.page_data(query, page, "sample"))


@admin_company_router.delete("/{company_id}", description="删除公司")
async def company_delete(
    company_id: str,
    session: Session = Depends(depend.get_db),
    admin_user: AdminUser = Depends(depend.super_admin),
):
    company = session.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        return restResult.fail("公司不存在")
    try:
        # 删除中间表中的关联记录
        execute_sql = users_companies_table.delete().where(users_companies_table.c.company_id == company_id)
        session.execute(execute_sql)
        # 删除 CompanyModel 记录
        session.delete(company)
        session.commit()
        logger.info(f"{admin_user}删除公司{company}及关联记录成功.")
        return restResult.success()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"删除公司{company}时发生数据库异常: {e}")
        return restResult.fail("服务器异常")
    except Exception as e:
        session.rollback()
        logger.error(f"删除公司{company}时发生数据库异常: {e}")
        return restResult.fail("服务器异常")


@admin_company_router.get("/{company_id}/users", dependencies=[Depends(depend.admin_user)],
                          description="获取某个公司下的所有用户")
async def get_company_users(
    company_id: str,
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    fuzzy_search_key: str = "",
):
    company: CompanyModel = session.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        return restResult.fail("公司不存在")

    page = PageInfo(page_number, page_record_number)
    query = session.query(UserModel).join(
        users_companies_table, users_companies_table.c.user_id == UserModel.id).filter(
        users_companies_table.c.company_id == company_id)
    if fuzzy_search_key:
        query = query.filter(UserModel.account.like(f"%{fuzzy_search_key}%"))
    data = CompanyDAO.page_data(query, page, "sample")
    return restResult.success(data=data)


@admin_company_router.get("/{company_id}/jds", dependencies=[Depends(depend.admin_user)],
                          description="获取某个公司下的所有JD")
async def get_company_jds(
    company_id: str,
    session: Session = Depends(depend.get_db),
    page_number: int = 1,
    page_record_number: int = 50,
    fuzzy_search_key: str = ""
):
    company: CompanyModel = session.query(CompanyModel).filter(CompanyModel.id == company_id).first()
    if not company:
        return restResult.fail("公司不存在")
    page = PageInfo(page_number, page_record_number)
    query = session.query(JobDataModel).filter(JobDataModel.company_id == company_id)
    if fuzzy_search_key:
        query = query.filter(JobDataModel.name.like(f"%{fuzzy_search_key}%"))
    query = query.order_by(JobDataModel.create_time.desc())
    return restResult.success(data=JobDataDao.page_data(query, page, "sample"))
