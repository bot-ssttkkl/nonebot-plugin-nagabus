from io import StringIO
from typing import Optional
from datetime import datetime

from monthdelta import monthdelta
from nonebot import Bot, on_command
from nonebot_plugin_saa import MessageFactory
from nonebot_plugin_session_orm import get_session_by_persist_id
from ssttkkl_nonebot_utils.interceptor.handle_error import handle_error
from ssttkkl_nonebot_utils.interceptor.with_handling_reaction import (
    with_handling_reaction,
)

from ..ac import ac
from ..naga import naga
from ..utils.tz import TZ_TOKYO
from .errors import error_handlers
from ..utils.nickname import get_nickname
from ..naga.model import NagaServiceUserStatistic

statistic_srv = ac.create_subservice("statistic")


async def naga_statistic(
    bot: Bot,
    year: int,
    month: int,
    statistic: list[NagaServiceUserStatistic],
    rest_np: Optional[int] = None,
):
    total_cost_np = 0

    with StringIO() as sio:
        for i, s in enumerate(statistic):
            session = await get_session_by_persist_id(s.customer_id)
            sio.write(f"#{i + 1} {await get_nickname(bot, session)}: {s.cost_np}NP\n")

            total_cost_np += s.cost_np

        msg = f"{year}年{month}月共使用{total_cost_np}NP"
        if rest_np is not None:
            msg += f"，剩余{rest_np}NP"
        msg = (msg + "\n\n" + sio.getvalue()).strip()

        await MessageFactory(msg).send(reply=True)


naga_statistic_this_month_matcher = on_command(
    "naga本月使用情况", aliases={"naga-statistic"}, priority=5, block=True
)
statistic_srv.patch_matcher(naga_statistic_this_month_matcher)


@naga_statistic_this_month_matcher.handle()
@handle_error(error_handlers)
@with_handling_reaction()
async def naga_statistic_this_month(bot: Bot):
    cur = datetime.now(tz=TZ_TOKYO)
    statistic = await naga.statistic(cur.year, cur.month)
    rest_np = await naga.get_rest_np()
    await naga_statistic(bot, cur.year, cur.month, statistic, rest_np)


naga_statistic_prev_month_matcher = on_command("naga上月使用情况", priority=5, block=True)
statistic_srv.patch_matcher(naga_statistic_prev_month_matcher)


@naga_statistic_prev_month_matcher.handle()
@handle_error(error_handlers)
@with_handling_reaction()
async def naga_statistic_prev_month(bot: Bot):
    prev_month = datetime.now(tz=TZ_TOKYO) - monthdelta(months=1)
    statistic = await naga.statistic(prev_month.year, prev_month.month)
    await naga_statistic(bot, prev_month.year, prev_month.month, statistic)
