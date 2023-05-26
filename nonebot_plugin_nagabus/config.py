from typing import Dict, Union, List, Optional
from urllib.parse import urlparse

from nonebot import get_driver
from pydantic import BaseSettings, root_validator


class Config(BaseSettings):
    naga_cookies: Dict[str, str]
    naga_fake_api: bool = False
    naga_allow_group: Union[bool, List[int]] = True
    naga_allow_private: Union[bool, List[int]] = True

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


conf = Config(**get_driver().config.dict())
