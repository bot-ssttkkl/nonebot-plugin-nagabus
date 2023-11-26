from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.internal.matcher import Matcher
from ssttkkl_nonebot_utils.nonebot import default_command_start
from ssttkkl_nonebot_utils.interceptor.handle_error import handle_error

from ..ac import ac
from ..naga import naga
from .errors import error_handlers

set_token_srv = ac.create_subservice("set_cookies")

set_token_matcher = on_command(
    "naga-set-cookies", priority=4, block=True, permission=SUPERUSER
)
set_token_srv.patch_matcher(set_token_matcher)


@set_token_matcher.handle()
@handle_error(error_handlers)
async def naga_set_cookies(matcher: Matcher, cmd_args=CommandArg()):
    try:
        cookies = dict(
            [
                tuple(x.strip().split("=", maxsplit=1))
                for x in cmd_args.extract_plain_text().split(";")
            ]
        )

        if "csrftoken" not in cookies or "naga-report-session-id" not in cookies:
            raise ValueError(
                "cookies must contain csrftoken and naga-report-session-id"
            )
    except ValueError:
        await matcher.send(
            f"格式：{default_command_start}naga-set-cookies csrftoken=xxxxxxx; naga-report-session-id=xxxxxxx"
        )
        return

    await naga.set_cookies(cookies)
    await matcher.send("设置成功")
