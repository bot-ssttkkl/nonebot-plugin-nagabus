from nonebot import get_driver

from .service import NagaService

naga = NagaService()

get_driver().on_startup(naga.start)
get_driver().on_shutdown(naga.close)
