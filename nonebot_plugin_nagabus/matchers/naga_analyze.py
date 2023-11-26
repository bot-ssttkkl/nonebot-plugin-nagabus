import re
from urllib.parse import parse_qs, urlparse

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.internal.params import Depends
from nonebot_plugin_saa import MessageFactory
from ssttkkl_nonebot_utils.integer import decode_integer
from nonebot_plugin_session import Session, extract_session
from ssttkkl_nonebot_utils.errors.errors import BadRequestError
from ssttkkl_nonebot_utils.nonebot import default_command_start
from ssttkkl_nonebot_utils.interceptor.handle_error import handle_error
from nonebot_plugin_access_control_api.service.contextvars import (
    current_rate_limit_token,
)
from ssttkkl_nonebot_utils.interceptor.with_graceful_shutdown import (
    with_graceful_shutdown,
)
from ssttkkl_nonebot_utils.interceptor.with_handling_reaction import (
    with_handling_reaction,
)

from ..ac import ac
from ..naga import naga
from .errors import error_handlers
from ..naga.errors import InvalidKyokuHonbaError

analyze_srv = ac.create_subservice("analyze")


async def _retire_token():
    try:
        token = current_rate_limit_token.get()
        await token.retire()
    except LookupError:
        pass


async def analyze_majsoul(session: Session, uuid: str, kyoku: int, honba: int):
    try:
        report, cost_np = await naga.analyze_majsoul(uuid, kyoku, honba, session)
        await MessageFactory(
            f"https://naga.dmv.nico/htmls/{report.report_id}.html?tw=0"
        ).send(reply=True)

        if cost_np == 0:
            await _retire_token()
            await MessageFactory("由于此前已解析过该局，本次解析消耗0NP").send(reply=True)
        else:
            await MessageFactory(f"本次解析消耗{cost_np}NP").send(reply=True)
    except InvalidKyokuHonbaError as e:
        kyoku_honba = []
        for kyoku, honba in e.available_kyoku_honba:
            if kyoku <= 3:
                kyoku_honba.append(f"东{kyoku + 1}局{honba}本场")
            elif kyoku <= 7:
                kyoku_honba.append(f"南{kyoku - 3}局{honba}本场")
            else:
                kyoku_honba.append(f"西{kyoku - 7}局{honba}本场")

        raise BadRequestError(f"请输入正确的场次与本场（{'、'.join(kyoku_honba)}）") from e


async def analyze_tenhou(session: Session, haihu_id: str, seat: int):
    report, cost_np = await naga.analyze_tenhou(haihu_id, seat, session)
    await MessageFactory(
        f"https://naga.dmv.nico/htmls/{report.report_id}.html?tw={seat}"
    ).send(reply=True)

    if cost_np == 0:
        await _retire_token()
        await MessageFactory("由于此前已解析过该局，本次解析消耗0NP").send(reply=True)
    else:
        await MessageFactory(f"本次解析消耗{cost_np}NP").send(reply=True)


naga_analyze_matcher = on_command("naga", priority=10)

uuid_reg = re.compile(
    r"\d{6}-[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}"
)

kyoku_honba_reg = re.compile(
    r"([东南西])([一二三四1234])局(([0123456789零一两二三四五六七八九十百千万亿]+)本场)?"
)


@naga_analyze_matcher.handle()
@with_graceful_shutdown()
@handle_error(error_handlers)
@analyze_srv.patch_handler(retire_on_throw=True)
@with_handling_reaction()
async def naga_analyze(
    cmd_args=CommandArg(), session: Session = Depends(extract_session)
):
    args = cmd_args.extract_plain_text().split(" ")
    if "maj-soul" in args[0]:
        mat = uuid_reg.search(args[0])
        if not mat:
            raise BadRequestError("不正确的雀魂牌谱")

        uuid = mat.group(0)

        kyoku = -1
        honba = -1

        if len(args) >= 2:
            mat = kyoku_honba_reg.search(args[1])
            if mat:
                raw_wind, raw_kyoku, _, raw_honba = mat.groups()

                try:
                    kyoku = decode_integer(raw_kyoku) - 1
                    if raw_wind == "南":
                        kyoku += 4
                    elif raw_wind == "西":
                        kyoku += 8

                    if raw_honba is not None:
                        honba = decode_integer(raw_honba)
                except ValueError:
                    pass

        # 如果未指定场次本场，则让其发送该局的场次本场信息
        await analyze_majsoul(session, uuid, kyoku, honba)
    elif "tenhou" in args[0]:
        tenhou_url = args[0].strip()

        _, _, _, _, tenhou_query, _ = urlparse(tenhou_url)
        tenhou_query = parse_qs(tenhou_query)

        haihu_id = tenhou_query["log"][0]
        seat = 0
        if "tw" in tenhou_query and len(tenhou_query["tw"]) > 0:
            seat = int(tenhou_query["tw"][0])

        await analyze_tenhou(session, haihu_id, seat)
    else:
        await MessageFactory(
            "用法：\n"
            f"{default_command_start}naga <雀魂牌谱链接> <东/南x局x本场>：消耗10NP解析雀魂小局\n"
            f"{default_command_start}naga <天凤牌谱链接>：消耗50NP解析天凤半庄"
        ).send(reply=True)
