import asyncio
from typing import Union
from uuid import uuid4

from nonebot import logger

from nonebot_plugin_nagabus.naga.api import OrderReportList
from nonebot_plugin_nagabus.naga.model import NagaGameRule, NagaHanchanModelType, NagaTonpuuModelType, NagaOrder, \
    NagaModel, NagaReport, NagaReportPlayer, NagaOrderStatus


class FakeNagaApi:
    def __init__(self):
        self.report = []
        self.order = []

    async def close(self):
        ...

    async def order_report_list(self, year: int, month: int) -> OrderReportList:
        return OrderReportList(report=self.report, order=self.order)

    async def analyze_custom(self, data: Union[dict, str], seat: int = 0,
                             rule: NagaGameRule = NagaGameRule.hanchan,
                             model_type: Union[
                                 NagaHanchanModelType, NagaTonpuuModelType] = NagaHanchanModelType.nishiki):
        haihu_id = str(uuid4())
        order = NagaOrder(haihu_id=haihu_id, status=NagaOrderStatus.ok, model=NagaModel(2, 0, model_type), rule=rule)
        self.order.insert(0, order)
        logger.info(f"Insert order (haihu_id: {order.haihu_id})")

        await asyncio.sleep(3)

        report_id = str(uuid4())
        report = NagaReport(haihu_id=haihu_id, players=[NagaReportPlayer("AI", 0)] * 4, report_id=report_id, seat=0,
                            model=NagaModel(2, 0, model_type), rule=rule)
        self.report.insert(0, report)
        logger.info(f"Insert report (haihu_id: {order.haihu_id}, report_id: {report.report_id})")
