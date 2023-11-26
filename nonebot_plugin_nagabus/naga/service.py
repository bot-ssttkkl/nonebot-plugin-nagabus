import re
import asyncio
from asyncio import Lock
from typing import Union
from datetime import datetime
from inspect import isawaitable
from collections.abc import Mapping, Sequence

from httpx import Cookies
from nonebot import logger
from monthdelta import monthdelta
from nonebot_plugin_session import Session
from nonebot_plugin_orm import AsyncSession
from nonebot_plugin_datastore.db import get_engine
from tensoul.downloader import MajsoulDownloadError
from nonebot_plugin_session_orm import get_session_persist_id

from ..config import conf
from ..utils.tz import TZ_TOKYO
from .fake_api import FakeNagaApi
from .utils import model_type_to_str
from ..data.naga import NagaRepository
from ..data.mjs import get_majsoul_paipu
from .api import NagaApi, OrderReportList
from ..data.naga_cookies import get_naga_cookies, set_naga_cookies
from .errors import (
    OrderError,
    InvalidGameError,
    UnsupportedGameError,
    InvalidKyokuHonbaError,
)
from .model import (
    NagaOrder,
    NagaReport,
    NagaGameRule,
    NagaOrderStatus,
    NagaServiceOrder,
    NagaTonpuuModelType,
    NagaHanchanModelType,
    NagaServiceUserStatistic,
)

DURATION = 2


class ObservableOrderReport:
    def __init__(self, api: NagaApi):
        self.api = api
        self.value = None
        self._observers = []
        self._refresh_worker = None

    @logger.catch
    async def _refresh_once(self):
        current = datetime.now(tz=TZ_TOKYO)
        prev_month = current - monthdelta(months=1)

        list_this_month = await self.api.order_report_list(current.year, current.month)
        list_prev_month = await self.api.order_report_list(
            prev_month.year, prev_month.month
        )

        self.value = OrderReportList(
            report=[*list_this_month.report, *list_prev_month.report],
            order=[*list_this_month.order, *list_prev_month.order],
        )

    async def _refresh(self):
        while True:
            try:
                if len(self._observers) != 0:
                    logger.trace("refreshing naga orders and reports...")

                    await self._refresh_once()

                    observers = self._observers
                    self._observers = []

                    for ob in observers:
                        x = ob(self.value)
                        if isawaitable(x):
                            await x
            except BaseException as e:
                logger.exception(e)

            await asyncio.sleep(DURATION)

    def observe_once(self, callback):
        self._observers.append(callback)
        if self._refresh_worker is None:
            self._refresh_worker = asyncio.create_task(self._refresh())


class NagaService:
    _tenhou_haihu_id_reg = re.compile(
        r"^20\d{8}gm-[a-f\d]{4}-[a-z\d]{4,5}-[a-zA-Z\d]{8}$"
    )

    def __init__(self):
        self.cookies = Cookies()

        if conf().naga_fake_api:
            self.api = FakeNagaApi()
            logger.warning("using fake naga api")
        else:
            self.api = NagaApi(cookies_getter=lambda: self.cookies)

        self._majsoul_order_mutex = Lock()
        self._tenhou_order_mutex = Lock()

        self._last_custom_haihu_id = None

        self._order_report = ObservableOrderReport(self.api)

    async def start(self):
        cookies_obj = await get_naga_cookies()
        self.cookies = Cookies(cookies_obj)

    async def close(self):
        await self.api.close()

    async def set_cookies(self, cookies: Mapping[str, str]):
        await set_naga_cookies(cookies)
        self.cookies = Cookies(dict(cookies))
        logger.info(
            f"naga_cookies set to {'; '.join(f'{kv[0]}={kv[1]}' for kv in cookies.items())}"
        )

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
            timeout = conf().naga_timeout
            if timeout > 0:
                return await asyncio.wait_for(report, timeout)
            else:
                return await report
        finally:
            cancel_flag = True

    async def _order_custom(
        self,
        data: Union[list, str],
        rule: NagaGameRule,
        model_type: Union[
            None, Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ] = None,
    ) -> NagaOrder:
        current = datetime.now(tz=TZ_TOKYO)
        await self.api.analyze_custom(data, 0, rule, model_type)

        order_fut = asyncio.get_running_loop().create_future()
        retry = 0  # 下单完马上获取order的话，有时候order刷新不出来，可以多试几次

        def _make_callback():
            async def callback(order_report: OrderReportList):
                nonlocal retry

                try:
                    for order in order_report.order:
                        # order.haihu_id: custom_haihu_2023-05-25T23:46:07_QRIGFOKmA4HT4CJF
                        if not order.haihu_id.startswith("custom_haihu_"):
                            continue

                        if order.haihu_id == self._last_custom_haihu_id:
                            break

                        order_time = datetime.fromisoformat(
                            order.haihu_id[13:32]
                        ).replace(tzinfo=TZ_TOKYO)
                        if (
                            abs(current.timestamp() - order_time.timestamp()) >= 30
                        ):  # 时间差超过了30s
                            break

                        self._last_custom_haihu_id = order.haihu_id
                        order_fut.set_result(order)
                        return

                    if retry < 5:
                        self._order_report.observe_once(_make_callback())
                        retry += 1
                    else:
                        raise OrderError("order failed")
                except BaseException as e:
                    order_fut.set_exception(e)

            return callback

        self._order_report.observe_once(_make_callback())

        return await order_fut

    @staticmethod
    def _handle_model_type(
        rule: NagaGameRule,
        model_type: Union[
            None, Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ],
    ) -> Union[Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]]:
        if rule == NagaGameRule.hanchan:
            if model_type is None:
                model_type = [
                    NagaHanchanModelType.nishiki,
                    NagaHanchanModelType.kagashi,
                ]
            assert isinstance(model_type, list) or isinstance(model_type, tuple)
            for t in model_type:
                assert isinstance(t, NagaHanchanModelType)
        elif rule == NagaGameRule.tonpuu:
            if model_type is None:
                model_type = [NagaTonpuuModelType.nu, NagaTonpuuModelType.sigma]
            assert isinstance(model_type, list) or isinstance(model_type, tuple)
            for t in model_type:
                assert isinstance(t, NagaTonpuuModelType)

        return model_type

    async def analyze_majsoul(
        self,
        majsoul_uuid: str,
        kyoku: int,
        honba: int,
        session: Session,
        *,
        model_type: Union[
            None, Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ] = None,
    ) -> NagaServiceOrder:
        async with AsyncSession(get_engine()) as sess:
            repo = NagaRepository(sess)
            try:
                data = await get_majsoul_paipu(majsoul_uuid)
            except MajsoulDownloadError as e:
                logger.opt(colors=True).warning(
                    f"Failed to download paipu <y>{majsoul_uuid}</y>, code: {e.code}"
                )
                if e.code == 1203:
                    raise InvalidGameError(
                        f"invalid majsoul_uuid: {majsoul_uuid}"
                    ) from e
                else:
                    raise e

            if len(data["name"]) != 4:
                raise UnsupportedGameError("only yonma game is supported")

            if "東" in data["rule"]["disp"]:
                rule = NagaGameRule.tonpuu
            else:
                rule = NagaGameRule.hanchan

            log = None
            for i, log in enumerate(data["log"]):
                if log[0][0] == kyoku:
                    if honba == -1:
                        # 未指定本场
                        if (i == 0 or data["log"][i - 1][0][0] != kyoku) and (
                            i == len(data["log"]) - 1
                            or data["log"][i + 1][0][0] != kyoku
                        ):
                            # 该场次只存在一个本场
                            honba = log[0][1]
                            log = log
                        break
                    elif log[0][1] == honba:
                        log = log
                        break

            if log is None:
                available_kyoku_honba = [(log[0][0], log[0][1]) for log in data["log"]]
                raise InvalidKyokuHonbaError(available_kyoku_honba)

            model_type = self._handle_model_type(rule, model_type)
            model_type_str = model_type_to_str(model_type)

            haihu_id = ""
            new_order = False

            # 加锁防止重复下单
            local_order = await repo.get_local_majsoul_order(
                majsoul_uuid, kyoku, honba, model_type_str
            )
            if local_order is None:
                async with self._majsoul_order_mutex:
                    local_order = await repo.get_local_majsoul_order(
                        majsoul_uuid, kyoku, honba, model_type_str
                    )
                    if local_order is None:
                        # 不存在记录，安排解析
                        logger.opt(colors=True).info(
                            f"Ordering majsoul paipu <y>{majsoul_uuid} "
                            f"(kyoku: {kyoku}, honba: {honba})</y> analyze..."
                        )

                        # data["log"] = log
                        data = {
                            "title": data["title"],
                            "name": data["name"],
                            "rule": data["rule"],
                            "log": [log],
                        }

                        order = await self._order_custom([data], rule, model_type)
                        haihu_id = order.haihu_id

                        new_order = True

                        session_persist_id = await get_session_persist_id(session)
                        await repo.new_local_majsoul_order(
                            haihu_id,
                            session_persist_id,
                            majsoul_uuid,
                            kyoku,
                            honba,
                            model_type_str,
                        )

            if local_order is not None:
                # 存在记录
                if local_order.status == NagaOrderStatus.ok:
                    logger.opt(colors=True).info(
                        f"Found a existing majsoul paipu <y>{majsoul_uuid} "
                        f"(kyoku: {kyoku}, honba: {honba})</y> "
                        f"analyze report: {local_order.haihu_id}"
                    )
                    report = repo.parse_report(local_order.naga_report)
                    return NagaServiceOrder(report=report, cost_np=0)

                haihu_id = local_order.haihu_id
                logger.opt(colors=True).info(
                    f"Found a processing majsoul paipu <y>{majsoul_uuid} "
                    f"(kyoku: {kyoku}, honba: {honba})</y> "
                    f"analyze order: {haihu_id}"
                )

            assert haihu_id != ""

            logger.opt(colors=True).info(
                f"Waiting for majsoul paipu <y>{majsoul_uuid} "
                f"(kyoku: {kyoku}, honba: {honba})</y> "
                f"analyze report: {haihu_id} ..."
            )
            report = await self._get_report(haihu_id)

            if new_order:
                # 需要更新之前创建的NagaOrderOrm
                logger.opt(colors=True).debug(
                    f"Updating majsoul paipu <y>{majsoul_uuid} "
                    f"(kyoku: {kyoku}, honba: {honba})</y> "
                    f"analyze report: {haihu_id}..."
                )
                await repo.update_local_order(haihu_id, report)
                return NagaServiceOrder(report=report, cost_np=10)
            else:
                return NagaServiceOrder(report=report, cost_np=0)

    async def _order_tenhou(
        self,
        haihu_id: str,
        seat: int,
        model_type: Union[
            None, Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ] = None,
    ):
        res = await self.api.analyze_tenhou(haihu_id, seat, model_type)
        if res.status != 200:
            raise OrderError(res.msg)

    # needs test
    async def analyze_tenhou(
        self,
        haihu_id: str,
        seat: int,
        session: Session,
        *,
        model_type: Union[
            None, Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
        ] = None,
    ) -> NagaServiceOrder:
        async with AsyncSession(get_engine()) as sess:
            repo = NagaRepository(sess)
            if not self._tenhou_haihu_id_reg.match(haihu_id):
                raise InvalidGameError(f"invalid haihu_id: {haihu_id}")

            haihu_element = haihu_id.split("-")
            if len(haihu_element) != 4:
                raise InvalidGameError(f"invalid haihu_id: {haihu_id}")

            haihu_rule = int(haihu_element[1], 16)
            is_yonma = not bool(haihu_rule & 16)
            is_hanchan = bool(haihu_rule & 8)
            is_kuitan = not bool(haihu_rule & 4)
            is_online = bool(haihu_rule & 1)

            if is_yonma and is_kuitan and is_online:
                rule = NagaGameRule.hanchan if is_hanchan else NagaGameRule.tonpuu
            else:
                raise UnsupportedGameError("only online kuitan yonma game is supported")

            model_type = self._handle_model_type(rule, model_type)
            model_type_str = model_type_to_str(model_type)

            new_order = False

            # 加锁防止重复下单
            local_order = await repo.get_local_order(haihu_id, model_type_str)
            if local_order is None:
                async with self._tenhou_order_mutex:
                    local_order = await repo.get_local_order(haihu_id, model_type_str)
                    if local_order is None:
                        # 不存在记录，安排解析
                        logger.opt(colors=True).info(
                            f"Ordering tenhou paipu <y>{haihu_id}</y> analyze..."
                        )

                        await self._order_tenhou(haihu_id, seat, model_type)

                        new_order = True

                        session_persist_id = await get_session_persist_id(session)
                        await repo.new_local_order(
                            haihu_id, session_persist_id, rule, model_type_str
                        )

            if local_order is not None:
                # 存在记录
                if local_order.status == NagaOrderStatus.ok:
                    logger.opt(colors=True).info(
                        f"Found a existing tenhou paipu <y>{haihu_id})</y> "
                        "analyze report"
                    )
                    report = repo.parse_report(local_order.naga_report)
                    return NagaServiceOrder(report=report, cost_np=0)

                logger.opt(colors=True).info(
                    f"Found a processing tenhou paipu <y>{haihu_id})</y> "
                    "analyze order"
                )

            logger.opt(colors=True).info(
                f"Waiting for tenhou paipu <y>{haihu_id})</y> " f"analyze report..."
            )
            report = await self._get_report(haihu_id)

            if new_order:
                # 需要更新之前创建的NagaOrderOrm
                logger.opt(colors=True).debug(
                    f"Updating tenhou paipu <y>{haihu_id})</y> " "analyze report..."
                )
                await repo.update_local_order(haihu_id, report)

                return NagaServiceOrder(report=report, cost_np=50)
            else:
                return NagaServiceOrder(report=report, cost_np=0)

    async def statistic(self, year: int, month: int) -> list[NagaServiceUserStatistic]:
        async with AsyncSession(get_engine()) as sess:
            repo = NagaRepository(sess)
            t_begin = datetime(year, month, 1)
            t_end = datetime(year, month, 1) + monthdelta(months=1)
            orders = await repo.get_orders(t_begin, t_end)

            statistic = {}

            for order in orders:
                if order.customer_id not in statistic:
                    statistic[order.customer_id] = 0
                statistic[order.customer_id] += order.cost_np

            statistic = [
                NagaServiceUserStatistic(customer_id=x[0], cost_np=x[1])
                for x in statistic.items()
            ]
            statistic.sort(key=lambda x: x.cost_np, reverse=True)
            return statistic

    async def get_rest_np(self) -> int:
        return await self.api.get_rest_np()
