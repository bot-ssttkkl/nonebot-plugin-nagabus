import asyncio
from functools import wraps
from typing import Type

from httpx import HTTPError
from nonebot import logger
from nonebot.adapters.onebot.v11 import ActionFailed
from nonebot.exception import MatcherException, ActionFailed
from nonebot.internal.matcher import Matcher
from nonebot_plugin_access_control.errors import RateLimitedError

from nonebot_plugin_nagabus.naga.service import OrderError


class BadRequestError(Exception):
    def __init__(self, message=None):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


def handle_error(matcher: Type[Matcher], silently: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except MatcherException as e:
                raise e
            except BadRequestError as e:
                if not silently:
                    await matcher.finish(e.message)
            except ActionFailed as e:
                # 避免当发送消息错误时再尝试发送
                logger.exception(e)
            except RateLimitedError as e:
                if not silently:
                    await matcher.finish("已达到使用次数上限")
            except OrderError as e:
                if not silently:
                    await matcher.finish("不知道为什么总之解析错误，请在NAGA网页端检查是否已成功解析")
            except HTTPError as e:
                logger.exception(e)
                if not silently:
                    await matcher.finish(f"网络错误")
            except asyncio.TimeoutError as e:
                logger.warning(type(e))
                if not silently:
                    await matcher.finish(f"查询超时")
            except Exception as e:
                logger.exception(e)
                if not silently:
                    await matcher.finish(f"内部错误：{type(e)}{str(e)}")

        return wrapped_func

    return decorator
