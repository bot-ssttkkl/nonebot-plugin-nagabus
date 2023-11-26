import random
import asyncio
from uuid import uuid4
from typing import Union
from datetime import datetime
from asyncio import create_task
from collections.abc import Mapping, Sequence

from nonebot import logger

from nonebot_plugin_nagabus.utils.tz import TZ_TOKYO
from nonebot_plugin_nagabus.naga.utils import model_type_to_str
from nonebot_plugin_nagabus.naga.api import AnalyzeTenhou, OrderReportList
from nonebot_plugin_nagabus.naga.model import (
    NagaModel,
    NagaOrder,
    NagaReport,
    NagaGameRule,
    NagaOrderStatus,
    NagaReportPlayer,
    NagaTonpuuModelType,
    NagaHanchanModelType,
)


class FakeNagaApi:
    def __init__(self):
        self.report = []
        self.order = []
        self.rest_np = 1500

    async def start(self):
        ...

    async def close(self):
        ...

    async def set_cookies(self, cookies: Mapping[str, str]):
        logger.info(
            f"naga_cookies set to {'; '.join(f'{kv[0]}={kv[1]}' for kv in cookies)}"
        )

    async def order_report_list(self, year: int, month: int) -> OrderReportList:
        return OrderReportList(report=self.report, order=self.order)

    @logger.catch
    async def _produce_order(self, order: NagaOrder):
        await asyncio.sleep(1)

        self.order.insert(0, order)
        logger.debug(f"Insert order (haihu_id: {order.haihu_id})")

    @logger.catch
    async def _produce_report(self, report: NagaReport):
        await asyncio.sleep(5)

        self.report.insert(0, report)
        logger.debug(
            f"Insert report (haihu_id: {report.haihu_id}, report_id: {report.report_id})"
        )

    async def analyze_custom(
        self,
        data: Union[dict, str],
        seat: int,
        rule: NagaGameRule,
        model_type: Union[
            Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ],
    ):
        time = (
            datetime.now(tz=TZ_TOKYO).replace(tzinfo=None).isoformat(timespec="seconds")
        )
        feat = "".join(str(random.randint(1, 9)) for _ in range(16))
        haihu_id = f"custom_haihu_{time}_{feat}"
        order = NagaOrder(
            haihu_id=haihu_id,
            status=NagaOrderStatus.ok,
            model=NagaModel(
                major=2, minor=2, old_type=0, type=model_type_to_str(model_type)
            ),
            rule=rule,
        )
        create_task(self._produce_order(order))

        self.rest_np -= 10

        report_id = str(uuid4())
        report = NagaReport(
            haihu_id=haihu_id,
            players=[NagaReportPlayer(nickname="AI", pt=0)] * 4,
            report_id=report_id,
            seat=0,
            model=NagaModel(
                major=2, minor=2, old_type=0, type=model_type_to_str(model_type)
            ),
            rule=rule,
        )
        create_task(self._produce_report(report))

    async def analyze_tenhou(
        self,
        haihu_id: str,
        seat: int,
        model_type: Union[
            Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ],
    ) -> AnalyzeTenhou:
        for o in self.order:
            if o.haihu_id == haihu_id:
                return AnalyzeTenhou(status=400, msg="すでに解析済みの牌譜です")

        order = NagaOrder(
            haihu_id=haihu_id,
            status=NagaOrderStatus.ok,
            model=NagaModel(
                major=2, minor=2, old_type=0, type=model_type_to_str(model_type)
            ),
            rule=NagaGameRule.hanchan,
        )
        create_task(self._produce_order(order))

        self.rest_np -= 50

        report_id = str(uuid4())
        report = NagaReport(
            haihu_id=haihu_id,
            players=[NagaReportPlayer(nickname="AI", pt=0)] * 4,
            report_id=report_id,
            seat=seat,
            model=NagaModel(
                major=2, minor=2, old_type=0, type=model_type_to_str(model_type)
            ),
            rule=NagaGameRule.hanchan,
        )
        create_task(self._produce_report(report))

        return AnalyzeTenhou(status=200, msg="")

    async def get_rest_np(self) -> int:
        return self.rest_np
