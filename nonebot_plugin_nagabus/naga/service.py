import asyncio
import json
from asyncio import Lock
from datetime import datetime, timezone
from inspect import isawaitable
from typing import Dict, Union, Optional, List, Tuple

from monthdelta import monthdelta
from nonebot import logger
from sqlalchemy import select, update

from .api import NagaApi, OrderReportList
from .fake_api import FakeNagaApi
from .model import NagaGameRule, NagaHanchanModelType, NagaTonpuuModelType, NagaOrder, NagaReport, NagaOrderStatus, \
    NagaServiceOrder, NagaServiceUserStatistic
from ..config import conf
from ..data.naga import MajsoulOrderOrm, NagaOrderOrm, NagaOrderSource
from ..data.session import get_session
from ..mjs import get_majsoul_paipu
from ..utils.tz import TZ_TOKYO

DURATION = 2


class ObservableOrderReport:
    def __init__(self, api: NagaApi):
        self.api = api
        self.value = None
        self._observers = []
        self._refresh_worker = None

    async def _refresh(self):
        while True:
            observers = self._observers
            self._observers = []

            if len(observers) != 0:
                logger.info("refreshing naga orders and reports...")

                current = datetime.now(tz=TZ_TOKYO)
                prev_month = current - monthdelta(months=1)

                list_this_month = await self.api.order_report_list(current.year, current.month)
                list_prev_month = await self.api.order_report_list(prev_month.year, prev_month.month)

                self.value = OrderReportList(report=[*list_this_month.report, *list_prev_month.report],
                                             order=[*list_this_month.order, *list_prev_month.order])

                for ob in observers:
                    x = ob(self.value)
                    if isawaitable(x):
                        await x

            await asyncio.sleep(DURATION)

    def observe_once(self, callback):
        self._observers.append(callback)
        if self._refresh_worker is None:
            self._refresh_worker = asyncio.create_task(self._refresh())


class NagaError(BaseException):
    ...


class OrderError(NagaError):
    ...


class UnsupportedGameError(NagaError):
    ...


class InvalidKyokuHonbaError(NagaError):
    def __init__(self, available_kyoku_honba: List[Tuple[int, int]]):
        super().__init__()
        self.available_kyoku_honba = available_kyoku_honba


class NagaService:
    def __init__(self, cookies: Dict[str, str], timeout: float = 90.0):
        if conf.naga_fake_api:
            self.api = FakeNagaApi()
            logger.warning("using fake naga api")
        else:
            self.api = NagaApi(cookies)

        self._order_mutex = Lock()
        self._majsoul_order_mutex = Lock()
        self._tenhou_order_mutex = Lock()

        self._order_report = ObservableOrderReport(self.api)
        self.timeout = timeout

    async def close(self):
        await self.api.close()

    async def _get_report(self, haihu_id: str) -> NagaReport:
        report = asyncio.get_running_loop().create_future()
        cancel_flag = False

        def _make_callback():
            async def callback(order_report: OrderReportList):
                try:
                    for r in order_report.report:
                        if r.haihu_id == haihu_id:
                            report.set_result(r)
                            break
                    else:
                        if not cancel_flag:
                            self._order_report.observe_once(_make_callback())
                except BaseException as e:
                    report.set_exception(e)

            return callback

        self._order_report.observe_once(_make_callback())

        try:
            if self.timeout > 0:
                return await asyncio.wait_for(report, self.timeout)
            else:
                return await report
        finally:
            cancel_flag = True

    async def _order_custom(self, data: Union[list, str],
                            rule: NagaGameRule,
                            model_type: Union[NagaHanchanModelType,
                                              NagaTonpuuModelType]) -> NagaOrder:
        async with self._order_mutex:
            current = datetime.now(tz=TZ_TOKYO)
            await self.api.analyze_custom(data, 0, rule, model_type)

            res = await self.api.order_report_list(current.year, current.month)
            if len(res.order) == 0:
                raise OrderError('order failed')

            order = res.order[0]
            # order.haihu_id: custom_haihu_2023-05-25T23:46:07_QRIGFOKmA4HT4CJF
            order_time = datetime.fromisoformat(order.haihu_id[13:32]).replace(tzinfo=TZ_TOKYO)
            if abs(current.timestamp() - order_time.timestamp()) >= 30:  # 时间差超过了30s
                raise OrderError('order failed')

            return order

    async def analyze_majsoul(self, majsoul_uuid: str, kyoku: int, honba: int,
                              customer_id: int,
                              *,
                              model_type: Union[NagaHanchanModelType,
                                                NagaTonpuuModelType, None] = None) -> NagaServiceOrder:
        sess = get_session()
        data = await get_majsoul_paipu(majsoul_uuid)

        if len(data["name"]) != 4:
            raise UnsupportedGameError()

        if "東" in data["rule"]["disp"]:
            rule = NagaGameRule.tonpuu
        else:
            rule = NagaGameRule.hanchan

        if model_type is None:
            if rule == NagaGameRule.hanchan:
                model_type = NagaHanchanModelType.nishiki
            else:
                model_type = NagaTonpuuModelType.sigma

        haihu_id = ""
        new_order = False

        async def _get_local_order() -> Optional[NagaOrderOrm]:
            stmt = select(MajsoulOrderOrm).where(MajsoulOrderOrm.paipu_uuid == majsoul_uuid,
                                                 MajsoulOrderOrm.kyoku == kyoku,
                                                 MajsoulOrderOrm.honba == honba,
                                                 MajsoulOrderOrm.model_type == model_type.value)

            order_orm: Optional[MajsoulOrderOrm] = (await sess.execute(stmt)).scalar_one_or_none()
            if order_orm is not None:
                if order_orm.order.status == NagaOrderStatus.ok or \
                        datetime.now(tz=timezone.utc).timestamp() - order_orm.order.update_time.timestamp() < 90:
                    return order_orm.order
                else:  # 超过90s仍未分析完成则删除重来
                    logger.opt(colors=True).info(f"Delete majsoul paipu <y>{majsoul_uuid} "
                                                 f"(kyoku: {kyoku}, honba: {honba}, "
                                                 f"model_type: {model_type.name})</y> analyze order "
                                                 f"because it takes over 90 seconds and still not done")
                    await sess.delete(order_orm.order)
                    await sess.commit()
                    return None

        # 加锁防止重复下单
        local_order = await _get_local_order()
        if local_order is None:
            async with self._majsoul_order_mutex:
                local_order = await _get_local_order()
                if local_order is None:
                    # 不存在记录，安排解析
                    logger.opt(colors=True).info(f"Ordering majsoul paipu <y>{majsoul_uuid} "
                                                 f"(kyoku: {kyoku}, honba: {honba}, "
                                                 f"model_type: {model_type.name})</y> analyze...")

                    log = None
                    for l in data["log"]:
                        if l[0][0] == kyoku and l[0][1] == honba:
                            log = l
                            break

                    if log is None:
                        available_kyoku_honba = [(l[0][0], l[0][1]) for l in data["log"]]
                        raise InvalidKyokuHonbaError(available_kyoku_honba)

                    # data["log"] = log
                    data = {
                        "title": data["title"],
                        "name": data["name"],
                        "rule": data["rule"],
                        "log": [log]
                    }

                    order = await self._order_custom([data], rule, model_type)
                    haihu_id = order.haihu_id

                    new_order = True

                    order_orm = NagaOrderOrm(haihu_id=haihu_id,
                                             customer_id=customer_id,
                                             cost_np=10,
                                             source=NagaOrderSource.majsoul,
                                             model_type=model_type.value,
                                             status=NagaOrderStatus.analyzing,
                                             create_time=datetime.now(tz=timezone.utc),
                                             update_time=datetime.now(tz=timezone.utc))

                    majsoul_order_orm = MajsoulOrderOrm(naga_haihu_id=haihu_id,
                                                        paipu_uuid=majsoul_uuid,
                                                        kyoku=kyoku,
                                                        honba=honba,
                                                        model_type=model_type.value,
                                                        order=order_orm)

                    sess.add(order_orm)
                    sess.add(majsoul_order_orm)
                    await sess.commit()

        if local_order is not None:
            # 存在记录
            if local_order.status == NagaOrderStatus.ok:
                logger.opt(colors=True).info(f"Found a existing majsoul paipu <y>{majsoul_uuid} "
                                             f"(kyoku: {kyoku}, honba: {honba}, "
                                             f"model_type: {model_type.name})</y> "
                                             "analyze report")
                report = NagaReport(*json.loads(local_order.naga_report))
                return NagaServiceOrder(report, 0)

            logger.opt(colors=True).info(f"Found a processing majsoul paipu <y>{majsoul_uuid} "
                                         f"(kyoku: {kyoku}, honba: {honba}, "
                                         f"model_type: {model_type.name})</y> "
                                         "analyze order")
            haihu_id = local_order.naga_haihu_id

        assert haihu_id != ""

        report = await self._get_report(haihu_id)

        if new_order:
            # 需要更新之前创建的NagaOrderOrm
            logger.opt(colors=True).debug(f"Updating majsoul paipu <y>{majsoul_uuid} "
                                          f"(kyoku: {kyoku}, honba: {honba},"
                                          f" model_type: {model_type.name})</y> "
                                          "analyze report...")
            stmt = update(NagaOrderOrm).where(NagaOrderOrm.haihu_id == haihu_id).values(
                status=NagaOrderStatus.ok, naga_report=json.dumps(report), update_time=datetime.now(timezone.utc)
            )
            await sess.execute(stmt)
            await sess.commit()

            return NagaServiceOrder(report, 10)
        else:
            return NagaServiceOrder(report, 0)

    async def _order_tenhou(self, haihu_id: str, seat: int, model_type: NagaHanchanModelType) -> NagaOrder:
        async with self._order_mutex:
            current = datetime.now(tz=TZ_TOKYO)
            res = await self.api.analyze_tenhou(haihu_id, seat, model_type)
            if res.status != 200:
                raise OrderError(res.msg)

            res = await self.api.order_report_list(current.year, current.month)
            for o in res.order:
                if o.haihu_id == haihu_id:
                    return o

            raise OrderError("order failed")

    # needs test
    async def analyze_tenhou(self, haihu_id: str, seat: int, customer_id: int,
                             *,
                             model_type: NagaHanchanModelType = NagaHanchanModelType.nishiki) -> NagaServiceOrder:
        sess = get_session()

        new_order = False

        async def _get_local_order() -> Optional[NagaOrderOrm]:
            stmt = select(NagaOrderOrm).where(NagaOrderOrm.haihu_id == haihu_id,
                                              NagaOrderOrm.model_type == model_type.value)

            order_orm: Optional[NagaOrderOrm] = (await sess.execute(stmt)).scalar_one_or_none()
            if order_orm is not None:
                if order_orm.status == NagaOrderStatus.ok or \
                        datetime.now(tz=timezone.utc).timestamp() - order_orm.update_time.timestamp() < 300:
                    return order_orm
                else:  # 超过90s仍未分析完成则删除重来
                    logger.opt(colors=True).info(f"Delete tenhou paipu <y>{haihu_id} "
                                                 f"(model_type: {model_type.name})</y> analyze order "
                                                 f"because it takes over 90 seconds and still not done")
                    await sess.delete(order_orm)
                    await sess.commit()
                    return None

        # 加锁防止重复下单
        local_order = await _get_local_order()
        if local_order is None:
            async with self._tenhou_order_mutex:
                local_order = await _get_local_order()
                if local_order is None:
                    # 不存在记录，安排解析
                    logger.opt(colors=True).info(f"Ordering tenhou paipu <y>{haihu_id} "
                                                 f"(model_type: {model_type.name})</y> analyze...")

                    order = await self._order_tenhou(haihu_id, seat, model_type)

                    new_order = True

                    order_orm = NagaOrderOrm(haihu_id=haihu_id,
                                             customer_id=customer_id,
                                             cost_np=10,
                                             source=NagaOrderSource.tenhou,
                                             model_type=model_type.value,
                                             status=NagaOrderStatus.analyzing,
                                             create_time=datetime.now(tz=timezone.utc),
                                             update_time=datetime.now(tz=timezone.utc))

                    sess.add(order_orm)
                    await sess.commit()

        if local_order is not None:
            # 存在记录
            if local_order.status == NagaOrderStatus.ok:
                logger.opt(colors=True).info(f"Found a existing tenhou paipu <y>{haihu_id} "
                                             f"(model_type: {model_type.name})</y> "
                                             "analyze report")
                report = NagaReport(*json.loads(local_order.naga_report))
                return NagaServiceOrder(report, 0)

            logger.opt(colors=True).info(f"Found a processing tenhou paipu <y>{haihu_id} "
                                         f"(model_type: {model_type.name})</y> "
                                         "analyze order")

        report = await self._get_report(haihu_id)

        if new_order:
            # 需要更新之前创建的NagaOrderOrm
            logger.opt(colors=True).debug(f"Updating tenhou paipu <y>{haihu_id} "
                                          f"(model_type: {model_type.name})</y> "
                                          "analyze report...")
            stmt = update(NagaOrderOrm).where(NagaOrderOrm.haihu_id == haihu_id).values(
                status=NagaOrderStatus.ok, naga_report=json.dumps(report), update_time=datetime.now(timezone.utc)
            )
            await sess.execute(stmt)
            await sess.commit()

            return NagaServiceOrder(report, 50)
        else:
            return NagaServiceOrder(report, 0)

    async def statistic(self, year: int, month: int) -> List[NagaServiceUserStatistic]:
        sess = get_session()

        t_begin = datetime(year, month, 1)
        t_end = datetime(year, month, 1) + monthdelta(months=1)

        stmt = select(NagaOrderOrm).where(NagaOrderOrm.create_time >= t_begin,
                                          NagaOrderOrm.create_time < t_end)

        orders = (await sess.execute(stmt)).scalars()

        statistic = {}

        for order in orders:
            if order.customer_id not in statistic:
                statistic[order.customer_id] = 0
            statistic[order.customer_id] += order.cost_np

        statistic = [NagaServiceUserStatistic(x[0], x[1]) for x in statistic.items()]
        statistic.sort(key=lambda x: x.cost_np, reverse=True)
        return statistic
