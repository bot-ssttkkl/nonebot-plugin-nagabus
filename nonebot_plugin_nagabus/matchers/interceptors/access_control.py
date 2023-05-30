from functools import wraps

from nonebot.internal.matcher import current_bot, current_event, current_matcher
from nonebot_plugin_access_control.errors import RateLimitedError, PermissionDeniedError
from nonebot_plugin_access_control.service import Service


def access_control(service: Service):
    def decorator(func):
        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            bot = current_bot.get()
            event = current_event.get()

            if not await service.check(bot, event, acquire_rate_limit_token=False):
                raise PermissionDeniedError()

            token = await service.acquire_token_for_rate_limit(bot, event)
            if token is None:
                raise RateLimitedError()

            matcher = current_matcher.get()
            matcher.state["ac_token"] = token

            try:
                return await func(*args, **kwargs)
            except BaseException as e:
                await token.retire()
                raise e

        return wrapped_func

    return decorator
