from typing import Optional

from sqlalchemy.orm import sessionmaker
from nonebot.message import run_postprocessor
from nonebot.internal.matcher import current_matcher
from nonebot_plugin_datastore.db import get_engine, post_db_init
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

_session: Optional[async_scoped_session] = None


@post_db_init
async def _():
    global _session
    session_factory = sessionmaker(
        get_engine(), expire_on_commit=False, class_=AsyncSession
    )
    _session = async_scoped_session(session_factory, scopefunc=current_matcher.get)


@run_postprocessor
async def postprocessor():
    if _session is not None:
        await _session.remove()


def get_session() -> AsyncSession:
    return _session()
