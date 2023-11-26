from typing import Union
from collections.abc import Sequence

from nonebot_plugin_nagabus.naga.model import NagaTonpuuModelType, NagaHanchanModelType


def model_type_to_str(
    model_type: Union[
        Sequence[NagaHanchanModelType], Sequence[NagaTonpuuModelType]
    ] = None
):
    return ",".join(str(x.value) for x in model_type)
