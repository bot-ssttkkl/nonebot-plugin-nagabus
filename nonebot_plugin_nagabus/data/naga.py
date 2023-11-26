from enum import IntEnum
from typing import Optional
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .base import SqlModel
from .utils import UTCDateTime
from ..naga.model import NagaOrderStatus


class NagaOrderSource(IntEnum):
    tenhou = 0
    majsoul = 1


class NagaOrderOrm(SqlModel):
    __tablename__ = "nonebot_plugin_nagabus_order"
    __table_args__ = {"extend_existing": True}

    haihu_id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[int]
    cost_np: Mapped[int]
    source: Mapped[NagaOrderSource]
    model_type: Mapped[str]
    status: Mapped[NagaOrderStatus]
    naga_report: Mapped[Optional[str]]  # json of NagaReport
    create_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    update_time: Mapped[datetime] = mapped_column(UTCDateTime)


class MajsoulOrderOrm(SqlModel):
    __tablename__ = "nonebot_plugin_nagabus_majsoul_order"
    __table_args__ = {"extend_existing": True}

    naga_haihu_id: Mapped[str] = mapped_column(
        ForeignKey("nonebot_plugin_nagabus_order.haihu_id", ondelete="cascade"),
        primary_key=True,
    )
    paipu_uuid: Mapped[str] = mapped_column(index=True)
    kyoku: Mapped[int]
    honba: Mapped[int]
    model_type: Mapped[str]

    order: Mapped[NagaOrderOrm] = relationship(
        foreign_keys="MajsoulOrderOrm.naga_haihu_id",
        cascade="save-update, delete",
        passive_deletes=True,
        lazy="joined",
    )
