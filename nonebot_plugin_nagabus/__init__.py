"""
nonebot-plugin-nagabus

@Author         : ssttkkl
@License        : AGPLv3
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-nagabus
"""

from nonebot import require

from .utils.nonebot import default_cmd_start

require("nonebot_plugin_access_control")
require("nonebot_plugin_majsoul")
require("nonebot_plugin_datastore")

from . import matchers

help_text = f"""
牌谱分析：
{default_cmd_start}naga <雀魂牌谱链接> <东/南x局x本场>：消耗10NP解析雀魂小局
{default_cmd_start}naga <天凤牌谱链接>：消耗50NP解析天凤半庄

使用情况：
{default_cmd_start}naga本月使用情况
{default_cmd_start}naga上月使用情况

以上命令格式中，以<>包裹的表示一个参数。

详细说明：参见https://github.com/ssttkkl/nonebot-plugin-nagabus
""".strip()

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='NAGA公交车',
    description='为群友提供NAGA拼车服务',
    usage=help_text
)
