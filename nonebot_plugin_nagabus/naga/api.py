import re
import json
from typing import Union, Callable
from collections.abc import Sequence

from nonebot import logger
from pydantic import BaseModel
from httpx import Cookies, AsyncClient

from .utils import model_type_to_str
from .errors import InvalidTokenError
from .model import (
    NagaOrder,
    NagaReport,
    NagaGameRule,
    NagaTonpuuModelType,
    NagaHanchanModelType,
)


class OrderReportList(BaseModel):
    report: list[NagaReport]
    order: list[NagaOrder]


class AnalyzeTenhou(BaseModel):
    status: int = 200
    msg: str = ""


class NagaApi:
    _BASE_URL = "https://naga.dmv.nico/naga_report"

    _HEADER = {
        "Cache-Control": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
    }

    def __init__(self, cookies_getter: Callable[[], Cookies]):
        self.cookies_getter = cookies_getter

        async def req_hook(request):
            # 手动设置cookies
            self.cookies.set_cookie_header(request)
            logger.trace(
                f"Request: {request.method} {request.url} - Waiting for response"
            )

        async def resp_hook(response):
            request = response.request
            logger.trace(
                f"Response: {request.method} {request.url} - Status {response.status_code}"
            )

            # 始终清除掉响应带的cookies
            self.client.cookies = None

            if response.status_code == 302:
                # 给定token无效时，响应状态码总为302
                raise InvalidTokenError()
            else:
                response.raise_for_status()

        self.client: AsyncClient = AsyncClient(
            base_url=self._BASE_URL,
            headers=self._HEADER,
            follow_redirects=True,
            event_hooks={"request": [req_hook], "response": [resp_hook]},
        )

    @property
    def cookies(self) -> Cookies:
        return self.cookies_getter()

    async def close(self):
        await self.client.aclose()

    async def order_report_list(self, year: int, month: int) -> OrderReportList:
        resp = await self.client.get(
            "/api/order_report_list/",
            headers={"Referer": "https://naga.dmv.nico/naga_report/order_report_list/"},
            params={"year": year, "month": month},
        )
        resp_json = resp.json()
        assert resp_json["status"] == 200
        return OrderReportList.parse_obj(resp_json)

    async def _get_csrfmiddlewaretoken(self) -> str:
        resp = await self.client.get("/order_form/")
        mat = re.search(
            r"<input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\"(.*)\">",
            resp.text,
        )
        if mat is None:
            raise RuntimeError("cannot get csrfmiddlewaretoken")
        return mat.group(1)

    async def analyze_tenhou(
        self,
        haihu_id: str,
        seat: int,
        model_type: Union[
            Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ],
    ) -> AnalyzeTenhou:
        data = {
            "haihu_id": haihu_id,
            "seat": seat,
            "reanalysis": 0,
            "player_types": model_type_to_str(model_type),
            "csrfmiddlewaretoken": await self._get_csrfmiddlewaretoken(),
        }

        resp = await self.client.post(
            "/api/url_analyze/",
            headers={"Referer": "https://naga.dmv.nico/naga_report/order_form/"},
            data=data,
        )

        if len(resp.content) > 0:
            return AnalyzeTenhou.parse_obj(resp.json())
        else:
            return AnalyzeTenhou(status=200, msg="")

    async def analyze_custom(
        self,
        data: Union[list, str],
        seat: int,
        rule: NagaGameRule,
        model_type: Union[
            Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ],
    ):
        if not isinstance(data, str):
            data = json.dumps(data, ensure_ascii=False)

        res_data = {
            "json_data": data,
            "seat": seat,
            "game_type": rule.value,
            "player_types": model_type_to_str(model_type),
            "csrfmiddlewaretoken": await self._get_csrfmiddlewaretoken(),
        }

        await self.client.post(
            "/api/custom_haihu_analyze/",
            headers={"Referer": "https://naga.dmv.nico/naga_report/order_form/"},
            data=res_data,
        )

    async def get_rest_np(self) -> int:
        resp = await self.client.get("/order_form/")
        mat = re.search(r"const base_left_point = (\d+)", resp.text)
        if mat is None:
            raise RuntimeError("cannot get base_left_point")
        return int(mat.group(1))
