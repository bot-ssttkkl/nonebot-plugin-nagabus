from enum import IntEnum
from typing import List, NamedTuple


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
    type: int


class NagaReport(NamedTuple):
    haihu_id: str
    players: List[NagaReportPlayer]
    report_id: str
    seat: int
    model: NagaModel
    rule: NagaGameRule


class NagaOrderStatus(IntEnum):
    ok = 0
    analyzing = 1


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
