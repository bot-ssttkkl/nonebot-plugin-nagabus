import asyncio
import random
from asyncio import create_task
from datetime import datetime
from typing import Union
from uuid import uuid4

from nonebot import logger

from nonebot_plugin_nagabus.naga.api import OrderReportList, AnalyzeTenhou
from nonebot_plugin_nagabus.naga.model import NagaGameRule, NagaHanchanModelType, NagaTonpuuModelType, NagaOrder, \
    NagaModel, NagaReport, NagaReportPlayer, NagaOrderStatus
from nonebot_plugin_nagabus.utils.tz import TZ_TOKYO


class FakeNagaApi:
    def __init__(self):
        self.report = []
        self.order = []

    async def close(self):
        ...

    async def order_report_list(self, year: int, month: int) -> OrderReportList:
        return OrderReportList(report=self.report, order=self.order)

    async def _produce_report(self, report: NagaReport):
        await asyncio.sleep(20)

        self.report.insert(0, report)
        logger.info(f"Insert report (haihu_id: {report.haihu_id}, report_id: {report.report_id})")

    async def analyze_custom(self, data: Union[dict, str], seat: int = 0,
                             rule: NagaGameRule = NagaGameRule.hanchan,
                             model_type: Union[
                                 NagaHanchanModelType, NagaTonpuuModelType] = NagaHanchanModelType.nishiki):
        time = datetime.now(tz=TZ_TOKYO).replace(tzinfo=None).isoformat(timespec='seconds')
        feat = ''.join(str(random.randint(1, 9)) for _ in range(16))
        haihu_id = f"custom_haihu_{time}_{feat}"
        order = NagaOrder(haihu_id=haihu_id, status=NagaOrderStatus.ok, model=NagaModel(2, 0, model_type), rule=rule)
        self.order.insert(0, order)
        logger.info(f"Insert order (haihu_id: {order.haihu_id})")

        report_id = str(uuid4())
        report = NagaReport(haihu_id=haihu_id, players=[NagaReportPlayer("AI", 0)] * 4, report_id=report_id, seat=0,
                            model=NagaModel(2, 0, model_type), rule=rule)
        create_task(self._produce_report(report))

    async def analyze_tenhou(self, haihu_id: str, seat: int,
                             model_type: NagaHanchanModelType = NagaHanchanModelType.nishiki) -> AnalyzeTenhou:
        for o in self.order:
            if o.haihu_id == haihu_id:
                return AnalyzeTenhou(status=400, msg="すでに解析済みの牌譜です")

        order = NagaOrder(haihu_id=haihu_id, status=NagaOrderStatus.ok, model=NagaModel(2, 0, model_type),
                          rule=NagaGameRule.hanchan)
        self.order.insert(0, order)
        logger.info(f"Insert order (haihu_id: {order.haihu_id})")

        report_id = str(uuid4())
        report = NagaReport(haihu_id=haihu_id, players=[NagaReportPlayer("AI", 0)] * 4, report_id=report_id, seat=seat,
                            model=NagaModel(2, 0, model_type), rule=NagaGameRule.hanchan)
        create_task(self._produce_report(report))

        return AnalyzeTenhou(status=200, msg="")
