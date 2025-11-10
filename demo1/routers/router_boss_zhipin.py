from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse, Response

import depend
from services.service_boss_zhipin import BossZhiPinService
from tools.rest_result import restResult

boss_zhipin_route = APIRouter(prefix="/boss-zp", dependencies=[Depends(depend.has_logged)])
# boss_zhipin_route = APIRouter(prefix="/boss-zp")


@boss_zhipin_route.get("/random-key", description="获取随机key")
async def get_random_key():
    return restResult.build_from_ret(BossZhiPinService.get_random_key())


@boss_zhipin_route.get("/qrcode/{qr_id}", description="获取二维码")
async def get_qrcode(qr_id):
    qrcode_bytes = BossZhiPinService.get_qrcode(qr_id)
    if qrcode_bytes is None:
        return restResult.fail("二维码获取失败")
    headers = {
        'Content-Disposition': 'inline'
    }
    return Response(content=qrcode_bytes, headers=headers, media_type="image/png")


@boss_zhipin_route.get("/qrcode-scan/{qr_id}", description="二维码有效检测")
async def qrcode_scan(qr_id):
    return restResult.build_from_ret(await BossZhiPinService.qrcode_scan(qr_id))


@boss_zhipin_route.get("/login-scan/{qr_id}", description="是否扫码登陆成功检测")
async def login_scan(qr_id):
    ret = BossZhiPinService.login_scan(qr_id)
    if ret.is_fail:
        return restResult.build_from_ret(ret)
    cookies = ret.data
    wbg = cookies["wbg"]
    if int(wbg) != 1:
        return restResult.forbidden("请切换为招聘者身份扫码登录")
    return restResult.success(data=cookies)
