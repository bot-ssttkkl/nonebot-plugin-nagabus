from typing import Optional
from urllib.parse import urlparse

from nonebot import get_driver
from pydantic import BaseSettings, root_validator


class Config(BaseSettings):
    naga_fake_api: bool = False
    naga_timeout: float = 60 * 10

    access_control_reply_on_permission_denied: Optional[str]
    access_control_reply_on_rate_limited: Optional[str]

    datastore_database_dialect: str

    @root_validator(pre=True, allow_reuse=True)
    def detect_sql_dialect(cls, values):
        if "datastore_database_url" in values:
            url = urlparse(values["datastore_database_url"])
            if "+" in url.scheme:
                sql_dialect = url.scheme.split("+")[0]
            else:
                sql_dialect = url.scheme
        else:
            sql_dialect = "sqlite"

        values["datastore_database_dialect"] = sql_dialect

        return values

    class Config:
        extra = "ignore"


_conf = None


def conf() -> Config:
    global _conf
    if _conf is None:
        _conf = Config(**get_driver().config.dict())
    return _conf
