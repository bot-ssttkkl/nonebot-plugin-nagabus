import re

from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.params import CommandArg
from nonebot_plugin_saa import MessageFactory, Text
from tensoul.downloader import MajsoulDownloadError

from .rule import naga_rule
from ..naga import naga
from ..naga.service import InvalidKyokuHonbaError, UnsupportedGameError
from ..utils.integer import decode_integer
from ..utils.nonebot import default_cmd_start

uuid_reg = re.compile(r"\d{6}-[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}")

kyoku_honba_reg = re.compile(r"([东南])([一二三四1234])局([0123456789零一两二三四五六七八九十百千万亿]+)本场")

naga_analyze_matcher = on_command("naga", priority=10, rule=naga_rule)


@naga_analyze_matcher.handle()
async def naga_analyze(event: MessageEvent, cmd_args=CommandArg()):
    args = cmd_args.extract_plain_text().split(' ')
    if "maj-soul" in args[0]:
        mat = uuid_reg.search(args[0])
        if not mat:
            await MessageFactory(Text("不正确的雀魂牌谱")).send(reply=True)

        uuid = mat.group(0)

        if len(args) < 2:
            await MessageFactory(Text("请指定场次与本场")).send(reply=True)

        kyoku = None
        honba = None

        mat = kyoku_honba_reg.search(args[1])
        if not mat:
            await MessageFactory(Text("请输入正确的场次与本场")).send(reply=True)

        raw_wind, raw_kyoku, raw_honba = mat.groups()

        try:
            kyoku = decode_integer(raw_kyoku) - 1
            if raw_wind == '南':
                kyoku += 4

            honba = decode_integer(raw_honba)
        except ValueError:
            pass

        if kyoku is None or honba is None:
            await MessageFactory(Text("请输入正确的场次与本场")).send(reply=True)

        try:
            report, cost_np = await naga.analyze_majsoul(uuid, kyoku, honba, event.user_id)
            msg = f"https://naga.dmv.nico/htmls/{report.report_id}.html?tw=0\n"

            if cost_np == 0:
                msg += "由于此前已解析过该局，本次解析消耗0NP"
            else:
                msg += f"本次解析消耗{cost_np}NP"
            await MessageFactory(Text(msg)).send(reply=True)
        except MajsoulDownloadError as e:
            logger.opt(colors=True).warning(f"Failed to download paipu <y>{uuid}</y>, code: {e.code}")
            if e.code == 1203:
                await MessageFactory(Text("牌谱不存在")).send(reply=True)
            else:
                raise e
        except InvalidKyokuHonbaError as e:
            kyoku_honba = []
            for kyoku, honba in e.available_kyoku_honba:
                if kyoku <= 3:
                    kyoku_honba.append(f"东{kyoku}局{honba}本场")
                else:
                    kyoku_honba.append(f"南{kyoku - 3}局{honba}本场")

            await MessageFactory(Text(f"请输入正确的场次与本场（{'、'.join(kyoku_honba)}）")).send(reply=True)
        except UnsupportedGameError as e:
            await MessageFactory(Text("只支持四麻牌谱")).send(reply=True)
    else:
        await MessageFactory(Text("用法：\n"
                                  f"{default_cmd_start}naga <雀魂牌谱链接> <东/南x局x本场>")).send(reply=True)
