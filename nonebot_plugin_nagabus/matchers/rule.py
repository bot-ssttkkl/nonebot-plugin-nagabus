from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent

from ..config import conf


def naga_rule(event: MessageEvent):
    if isinstance(event, GroupMessageEvent):
        return isinstance(conf.naga_allow_group, list) and event.group_id in conf.naga_allow_group or \
               isinstance(conf.naga_allow_group, bool) and conf.naga_allow_group
    else:
        return isinstance(conf.naga_allow_private, list) and event.user_id in conf.naga_allow_private or \
               isinstance(conf.naga_allow_private, bool) and conf.naga_allow_private
