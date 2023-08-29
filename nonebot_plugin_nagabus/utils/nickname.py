from nonebot import Bot, logger
from nonebot_plugin_session import Session, SessionIdType
from ssttkkl_nonebot_utils.platform import platform_func


async def get_nickname(bot: Bot, session: Session):
    nickname = session.get_id(SessionIdType.USER, include_bot_type=False, include_bot_id=False)

    if session.bot_type == bot.type:
        try:
            nickname = await platform_func(bot.type).get_user_nickname(session, bot)
        except BaseException as e:
            logger.opt(exception=e).error("获取用户昵称失败")

    return nickname
