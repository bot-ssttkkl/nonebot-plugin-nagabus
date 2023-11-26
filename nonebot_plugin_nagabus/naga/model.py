from enum import IntEnum
from typing import NamedTuple


class NagaGameRule(IntEnum):
    hanchan = 0
    tonpuu = 1


class NagaTonpuuModelType(IntEnum):
    nu = 0
    sigma = 1


class NagaHanchanModelType(IntEnum):
    omega = 0
    gamma = 1
    nishiki = 2
    hibakari = 3
    kagashi = 4


class NagaReportPlayer(NamedTuple):
    nickname: str
    pt: int


class NagaModel(NamedTuple):
    major: int
    minor: int
    old_type: int  # 新版本恒为0，旧版本为NagaHanchanModelType/NagaTonpuuModelType的枚举值
    type: str  # NagaHanchanModelType/NagaTonpuuModelType的枚举值，逗号分隔


class NagaReport(NamedTuple):
    haihu_id: str
    players: list[NagaReportPlayer]
    report_id: str
    seat: int
    model: NagaModel
    rule: NagaGameRule


class NagaOrderStatus(IntEnum):
    ok = 0
    pending = 1
    analyzing = 2
    failed = 3
    failed2 = 4


class NagaOrder(NamedTuple):
    haihu_id: str
    status: NagaOrderStatus
    model: NagaModel
    rule: NagaGameRule


class NagaServiceOrder(NamedTuple):
    report: NagaReport
    cost_np: int


class NagaServiceUserStatistic(NamedTuple):
    customer_id: int
    cost_np: int
