from collections.abc import Mapping

from ..datastore import plugin_data


async def get_naga_cookies() -> dict:
    return await plugin_data.config.get("naga_cookies", {})


async def set_naga_cookies(cookies: Mapping[str, str]):
    await plugin_data.config.set("naga_cookies", cookies)
