from typing import Dict
from urllib.parse import urlparse

from nonebot import get_driver
from pydantic import BaseSettings, root_validator, ValidationError

from .errors import ConfigError


class Config(BaseSettings):
    naga_cookies: Dict[str, str]
    naga_fake_api: bool = False
    naga_timeout: float = 60*10

    datastore_database_dialect: str

    @root_validator(pre=True, allow_reuse=True)
    def detect_sql_dialect(cls, values):
        if "datastore_database_url" in values:
            url = urlparse(values["datastore_database_url"])
            if '+' in url.scheme:
                sql_dialect = url.scheme.split('+')[0]
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
        try:
            _conf = Config(**get_driver().config.dict())
        except ValidationError as e:
            for err in e.errors():
                if err["loc"] == ("naga_cookies",) and err["type"] == "value_error.missing":
                    raise ConfigError("Please configure naga_cookies in your .env file!") from e
            else:
                raise e

    return _conf
