import pytest
import pytest_asyncio
from nonebug import NONEBOT_INIT_KWARGS


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "log_level": "DEBUG",
        "datastore_database_url": "sqlite+aiosqlite:///:memory:",
        "datastore_database_echo": True,
        "sqlalchemy_database_url": "sqlite+aiosqlite:///:memory:",
        "alembic_startup_check": False,
        "naga_fake_api": True,
    }


@pytest.fixture(scope="session", autouse=True)
def _prepare_nonebot():
    import nonebot
    from nonebot.adapters.onebot.v11 import Adapter

    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)

    nonebot.require("nonebot_plugin_nagabus")


_orm_inited = False


@pytest_asyncio.fixture(autouse=True)
async def _init_dep_plugins(_prepare_nonebot):
    from nonebot_plugin_orm import init_orm
    from nonebot_plugin_datastore.db import init_db

    global _orm_inited

    if not _orm_inited:
        await init_orm()
        await init_db()
        _orm_inited = True
