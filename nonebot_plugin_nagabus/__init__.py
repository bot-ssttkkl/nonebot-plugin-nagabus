"""
nonebot-plugin-nagabus

@Author         : ssttkkl
@License        : AGPLv3
@GitHub         : https://github.com/bot-ssttkkl/nonebot-plugin-nagabus
"""

from nonebot import require

require("nonebot_plugin_access_control_api")
require("nonebot_plugin_datastore")
require("nonebot_plugin_majsoul")
require("nonebot_plugin_saa")
require("nonebot_plugin_session")
require("nonebot_plugin_session_orm")
require("ssttkkl_nonebot_utils")

from nonebot import logger
from nonebot.plugin import PluginMetadata
from ssttkkl_nonebot_utils.nonebot import default_command_start

from .config import Config
from .errors import ConfigError

__usage__ = f"""
牌谱分析：
{default_command_start}naga <雀魂牌谱链接> <东/南x局x本场>：消耗10NP解析雀魂小局
{default_command_start}naga <天凤牌谱链接>：消耗50NP解析天凤半庄

使用情况：
{default_command_start}naga本月使用情况
{default_command_start}naga上月使用情况

以上命令格式中，以<>包裹的表示一个参数。

详细说明：参见https://github.com/bot-ssttkkl/nonebot-plugin-nagabus
""".strip()

__plugin_meta__ = PluginMetadata(
    name="NAGA公交车",
    description="为群友提供NAGA拼车服务",
    usage=__usage__,
    type="application",
    homepage="https://github.com/bot-ssttkkl/nonebot-plugin-nagabus",
    config=Config,
    supported_adapters={
        "~onebot.v11",
        "~onebot.v12",
        "~qqguild",
        "~kaiheila",
        "~telegram",
    },
)

try:
    from . import matchers  # noqa
except ConfigError as e:
    logger.exception(e)
