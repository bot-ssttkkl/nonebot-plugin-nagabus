import asyncio
from functools import wraps

from nonebot import logger
from nonebot_plugin_saa import MessageFactory


def send_waiting_prompt():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def send_delayed_waiting_prompt(delay: float = 5.0):
                try:
                    await asyncio.sleep(delay)
                    await asyncio.shield(MessageFactory(f"努力解析中").send(reply=True))
                except asyncio.CancelledError as e:
                    raise e
                except BaseException as e:
                    logger.exception(e)

            task = asyncio.create_task(send_delayed_waiting_prompt())

            try:
                await func(*args, **kwargs)
            finally:
                if task and not task.done():
                    task.cancel()

        return wrapper

    return decorator
