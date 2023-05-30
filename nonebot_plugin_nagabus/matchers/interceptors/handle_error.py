import asyncio
from functools import wraps

from httpx import HTTPError
from nonebot import logger
from nonebot.adapters.onebot.v11 import ActionFailed
from nonebot.exception import MatcherException, ActionFailed
from nonebot.internal.matcher import current_matcher
from nonebot_plugin_access_control.errors import RateLimitedError

from ..errors import BadRequestError
from ...naga.service import OrderError, InvalidGameError, UnsupportedGameError


def handle_error(silently: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            matcher = current_matcher.get()

            try:
                return await func(*args, **kwargs)
            except MatcherException as e:
                raise e
            except ActionFailed as e:
                # 避免当发送消息错误时再尝试发送
                logger.exception(e)
            except BadRequestError as e:
                if not silently:
                    await matcher.finish(e.message)
            except RateLimitedError as e:
                if not silently:
                    await matcher.finish("已达到使用次数上限")
            except OrderError as e:
                logger.warning(e)
                if not silently:
                    await matcher.finish("不知道为什么总之解析错误，请在NAGA网页端检查是否已成功解析")
            except InvalidGameError as e:
                logger.warning(e)
                if not silently:
                    await matcher.finish("牌谱链接不正确")
            except UnsupportedGameError as e:
                logger.warning(e)
                if not silently:
                    await matcher.finish("只支持四麻牌谱")
            except HTTPError as e:
                logger.exception(e)
                if not silently:
                    await matcher.finish(f"网络错误")
            except asyncio.TimeoutError as e:
                logger.warning(e)
                if not silently:
                    await matcher.finish(f"查询超时")
            except Exception as e:
                logger.exception(e)
                if not silently:
                    await matcher.finish(f"内部错误：{type(e)}{str(e)}")

        return wrapped_func

    return decorator
