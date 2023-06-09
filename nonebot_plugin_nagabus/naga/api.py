import json
from typing import Dict, List, Union, Sequence

from httpx import AsyncClient
from nonebot import logger
from pydantic import BaseModel

from .model import NagaReport, NagaOrder, NagaHanchanModelType, NagaTonpuuModelType, NagaGameRule
from .utils import model_type_to_str


class OrderReportList(BaseModel):
    report: List[NagaReport]
    order: List[NagaOrder]


class AnalyzeTenhou(BaseModel):
    status: int = 200
    msg: str = ""


class NagaApi:
    _BASE_URL = "https://naga.dmv.nico/naga_report/api"

    _HEADER = {
        "Cache-Control": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
    }

    def __init__(self, cookies: Dict[str, str]):
        async def req_hook(request):
            logger.trace(f"Request: {request.method} {request.url} - Waiting for response")

        async def resp_hook(response):
            request = response.request
            logger.trace(f"Response: {request.method} {request.url} - Status {response.status_code}")
            response.raise_for_status()

        self.client: AsyncClient = AsyncClient(
            base_url=self._BASE_URL,
            cookies=cookies,
            headers=self._HEADER,
            follow_redirects=True,
            event_hooks={'request': [req_hook], 'response': [resp_hook]}
        )

    async def close(self):
        await self.client.aclose()

    async def order_report_list(self, year: int, month: int) -> OrderReportList:
        resp = await self.client.get(
            "/order_report_list/",
            headers={
                "Referer": "https://naga.dmv.nico/naga_report/order_report_list/"
            },
            params={"year": year, "month": month}
        )
        return OrderReportList.parse_obj(resp.json())

    async def analyze_tenhou(self, haihu_id: str, seat: int = 0,
                             rule: NagaGameRule = NagaGameRule.hanchan,
                             model_type: Union[None, Sequence[NagaHanchanModelType],
                                               Sequence[NagaHanchanModelType]] = None) -> AnalyzeTenhou:
        model_type = self._handle_model_type(rule, model_type)

        data = {
            "haihu_id": haihu_id,
            "seat": seat,
            "reanalysis": 0,
            "player_types": model_type_to_str(model_type),
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"]
        }

        resp = await self.client.post(
            "/url_analyze/",
            headers={
                "Referer": "https://naga.dmv.nico/naga_report/order_form/"
            },
            data=data
        )

        if len(resp.content) > 0:
            return AnalyzeTenhou.parse_obj(resp.json())
        else:
            return AnalyzeTenhou(status=200, msg="")

    async def analyze_custom(self, data: Union[list, str], seat: int = 0,
                             rule: NagaGameRule = NagaGameRule.hanchan,
                             model_type: Union[None, Sequence[NagaHanchanModelType],
                                               Sequence[NagaTonpuuModelType]] = None):
        if not isinstance(data, str):
            data = json.dumps(data, ensure_ascii=False)

        model_type = self._handle_model_type(rule, model_type)

        res_data = {
            "json_data": data,
            "seat": seat,
            "game_type": rule.value,
            "player_types": model_type_to_str(model_type),
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"]
        }

        await self.client.post(
            "/custom_haihu_analyze/",
            headers={
                "Referer": "https://naga.dmv.nico/naga_report/order_form/"
            },
            data=res_data
        )
