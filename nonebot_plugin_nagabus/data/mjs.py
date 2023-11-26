import json
from typing import Any, Callable
from collections.abc import Awaitable
from typing_extensions import deprecated

import aiofiles
from nonebot import logger
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_localstore import get_cache_dir
from nonebot_plugin_majsoul.paipu import download_paipu

from .base import SqlModel
from .utils.atomic_cache import get_atomic_cache


@deprecated
class MajsoulPaipuOrm(SqlModel):
    __tablename__ = "nonebot_plugin_nagabus_majsoul_paipu"
    __table_args__ = {"extend_existing": True}

    paipu_uuid: Mapped[str] = mapped_column(primary_key=True)
    content: Mapped[str]


# 为了方便单测时mock实现
_download_paipu_delegate: Callable[[str], Awaitable[Any]] = download_paipu


def _set_download_paipu_delegate(download_paipu_delegate):
    global _download_paipu_delegate
    _download_paipu_delegate = download_paipu_delegate


async def _do_get_majsoul_paipu(uuid: str):
    mjs_paipu_dir = get_cache_dir("nonebot_plugin_nagabus") / "mjs_paipu"
    mjs_paipu_dir.mkdir(parents=True, exist_ok=True)

    paipu_file = mjs_paipu_dir / f"{uuid}.json"
    if paipu_file.exists():
        logger.opt(colors=True).info(f"Use cached majsoul paipu <y>{uuid}</y>")
        async with aiofiles.open(paipu_file, "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    else:
        logger.opt(colors=True).info(f"Downloading majsoul paipu <y>{uuid}</y> ...")
        data = await _download_paipu_delegate(uuid)
        async with aiofiles.open(paipu_file, "w+", encoding="utf-8") as f:
            await f.write(json.dumps(data))
        return data


async def get_majsoul_paipu(uuid: str):
    return await get_atomic_cache(
        f"mjs_paipu_{uuid}", lambda: _do_get_majsoul_paipu(uuid)
    )
