from nonebot import get_driver

from .service import NagaService
from ..config import conf

naga = NagaService(conf().naga_cookies)

get_driver().on_shutdown(naga.close)
