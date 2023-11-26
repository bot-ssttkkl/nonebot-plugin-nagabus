import asyncio

from nonebot import logger
from httpx import HTTPError
from ssttkkl_nonebot_utils.nonebot import default_command_start
from ssttkkl_nonebot_utils.errors.error_handler import ErrorHandlers
from nonebot_plugin_access_control_api.errors import (
    RateLimitedError,
    PermissionDeniedError,
)

from ..config import conf
from ..naga.errors import OrderError, InvalidGameError, UnsupportedGameError

error_handlers = ErrorHandlers()


@error_handlers.register(RateLimitedError)
def _(e):
    return conf().access_control_reply_on_rate_limited


@error_handlers.register(PermissionDeniedError)
def _(e):
    return conf().access_control_reply_on_permission_denied


@error_handlers.register(OrderError)
def _(e):
    msg = f"不知道为什么总之解析错误，请在NAGA网页端检查是否已成功解析（{str(e)}）"
    logger.opt(exception=e).error(msg)
    return msg


@error_handlers.register(InvalidGameError)
def _(e):
    return "牌谱链接不正确"


@error_handlers.register(UnsupportedGameError)
def _(e):
    return "只支持四麻牌谱"


@error_handlers.register(UnsupportedGameError)
def _(e):
    msg = f"Token无效，请通过{default_command_start}naga-set-cookies指令设置Token"
    logger.opt(exception=e).error(msg)
    return msg


@error_handlers.register(HTTPError)
def _(e):
    msg = "网络错误"
    logger.opt(exception=e).error(msg)
    return msg


@error_handlers.register(asyncio.TimeoutError)
def _(e):
    msg = "查询超时，请在NAGA网页端检查是否已成功解析"
    logger.opt(exception=e).error(msg)
    return msg


__all__ = ("error_handlers",)
