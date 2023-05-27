from datetime import datetime
from io import StringIO

from monthdelta import monthdelta
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.internal.matcher import Matcher

from ..ac import ac
from ..naga import naga
from ..utils.tz import TZ_TOKYO

statistic_srv = ac.create_subservice("statistic")


async def naga_statistic(bot: Bot, event: MessageEvent, matcher: Matcher, year: int, month: int):
    statistic = await naga.statistic(year, month)

    nicknames = {}
    if isinstance(event, GroupMessageEvent):
        members = await bot.get_group_member_list(group_id=event.group_id)
        for m in members:
            nicknames[m['user_id']] = m['nickname']

    total_cost_np = 0

    with StringIO() as sio:
        for i, s in enumerate(statistic):
            total_cost_np += s.cost_np

            if s.customer_id in nicknames:
                nickname = nicknames[s.customer_id]
            else:
                user = await bot.get_stranger_info(user_id=s.customer_id)
                nickname = user['nickname']

            sio.write(f"#{i + 1} {nickname}: {s.cost_np}NP\n")

        msg = (f"{year}年{month}月共使用{total_cost_np}NP\n\n" + sio.getvalue()).strip()

        await matcher.send(Message([
            MessageSegment.reply(event.message_id),
            MessageSegment.text(msg)
        ]))


naga_statistic_this_month_matcher = on_command("naga本月使用情况", priority=5, block=True)
statistic_srv.patch_matcher(naga_statistic_this_month_matcher)


@naga_statistic_this_month_matcher.handle()
async def naga_statistic_this_month(bot: Bot, event: MessageEvent, matcher: Matcher):
    cur = datetime.now(tz=TZ_TOKYO)
    await naga_statistic(bot, event, matcher, cur.year, cur.month)


naga_statistic_prev_month_matcher = on_command("naga上月使用情况", priority=5, block=True)
statistic_srv.patch_matcher(naga_statistic_prev_month_matcher)


@naga_statistic_prev_month_matcher.handle()
async def naga_statistic_prev_month(bot: Bot, event: MessageEvent, matcher: Matcher):
    prev_month = datetime.now(tz=TZ_TOKYO) - monthdelta(months=1)
    await naga_statistic(bot, event, matcher, prev_month.year, prev_month.month)
