from datetime import datetime
from io import StringIO
from typing import Optional

from monthdelta import monthdelta
from nonebot import on_command, Bot
from nonebot_plugin_datastore.db import get_engine
from nonebot_plugin_get_nickname import get_nickname
from nonebot_plugin_saa import MessageFactory
from nonebot_plugin_session import SessionIdType
from nonebot_plugin_session.model import SessionModel
from sqlalchemy.ext.asyncio import AsyncSession

from .interceptors.handle_error import handle_error
from ..ac import ac
from ..naga import naga
from ..utils.tz import TZ_TOKYO

statistic_srv = ac.create_subservice("statistic")


async def naga_statistic(bot: Bot, year: int, month: int):
    statistic = await naga.statistic(year, month)

    total_cost_np = 0

    async with AsyncSession(get_engine()) as db_sess:
        with StringIO() as sio:
            for i, s in enumerate(statistic):
                session_model: Optional[SessionModel] = await db_sess.get(SessionModel, s.customer_id)
                session = session_model.session
                if session.bot_type != bot.type:  # 来自其他平台的用户
                    nickname = session.get_id(SessionIdType.USER, include_bot_type=False, include_bot_id=False)
                else:
                    nickname = await get_nickname(session, bot)
                sio.write(f"#{i + 1} {nickname}: {s.cost_np}NP\n")

                total_cost_np += s.cost_np

            msg = (f"{year}年{month}月共使用{total_cost_np}NP\n\n" + sio.getvalue()).strip()

            await MessageFactory(msg).send(reply=True)


naga_statistic_this_month_matcher = on_command("naga本月使用情况", priority=5, block=True)
statistic_srv.patch_matcher(naga_statistic_this_month_matcher)


@naga_statistic_this_month_matcher.handle()
@handle_error()
async def naga_statistic_this_month(bot: Bot):
    cur = datetime.now(tz=TZ_TOKYO)
    await naga_statistic(bot, cur.year, cur.month)


naga_statistic_prev_month_matcher = on_command("naga上月使用情况", priority=5, block=True)
statistic_srv.patch_matcher(naga_statistic_prev_month_matcher)


@naga_statistic_prev_month_matcher.handle()
@handle_error()
async def naga_statistic_prev_month(bot: Bot):
    prev_month = datetime.now(tz=TZ_TOKYO) - monthdelta(months=1)
    await naga_statistic(bot, prev_month.year, prev_month.month)
