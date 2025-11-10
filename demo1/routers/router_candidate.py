from starlette.requests import Request

import depend
from fastapi import APIRouter, Depends

from schema.jobdata_schema import JobDataCandidateSchema
from schema.page_schema import PageInfo
from tools.rest_result import restResult
from services.service_candidate import CandidateService

candidate_route = APIRouter(prefix="/candidate")


@candidate_route.get("/list")
async def candidate_list_via_jd_id(
    request: Request,
    page_number: int = 1,
    page_record_number: int = 50,
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    jd_id = request.query_params.get("jd_id", "*")
    page = PageInfo(page_number=page_number, page_size=page_record_number)
    ret = CandidateService.list_candidates_via_jd(session, current_user, jd_id=jd_id, page=page)
    return restResult.build_from_ret(ret)


@candidate_route.post("/create")
async def create_jd_candidate(
    candidate_schema: JobDataCandidateSchema,
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    ret = CandidateService.create_candidate(candidate_schema, session, current_user)
    return restResult.build_from_ret(ret)


@candidate_route.delete("/{candidate_id}")
async def remove_candidate(
    candidate_id: str,
    session=Depends(depend.get_db),
    current_user=Depends(depend.current_user)
):
    ret = CandidateService.remove_candidate(candidate_id, session, current_user)
    return restResult.build_from_ret(ret)

