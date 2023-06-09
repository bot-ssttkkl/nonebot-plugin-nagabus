from typing import Sequence, Union

from nonebot_plugin_nagabus.naga.model import NagaHanchanModelType, NagaTonpuuModelType


def model_type_to_str(model_type: Union[Sequence[NagaHanchanModelType],
                                        Sequence[NagaTonpuuModelType]] = None):
    return ",".join(map(lambda x: str(x.value), model_type))
