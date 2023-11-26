from enum import IntEnum
from typing import Optional
from datetime import datetime, timezone

from nonebot import logger
from nonebot_plugin_orm import AsyncSession
from sqlalchemy import ForeignKey, select, update
from sqlalchemy.orm import Mapped, relationship, mapped_column

from nonebot_plugin_nagabus.data.utils.pydantic import PydanticModel

from .base import SqlModel
from .utils import UTCDateTime
from ..naga.model import NagaReport, NagaGameRule, NagaOrderStatus


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
    naga_report: Mapped[Optional[NagaReport]] = mapped_column(PydanticModel(NagaReport))
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


class NagaRepository:
    def __init__(self, sess: AsyncSession):
        self.sess = sess

    async def get_orders(
        self, t_begin: datetime, t_end: datetime
    ) -> list[NagaOrderOrm]:
        stmt = select(NagaOrderOrm).where(
            NagaOrderOrm.create_time >= t_begin,
            NagaOrderOrm.create_time < t_end,
            NagaOrderOrm.status == NagaOrderStatus.ok,
        )
        return list((await self.sess.execute(stmt)).scalars())

    async def get_local_majsoul_order(
        self, majsoul_uuid: str, kyoku: int, honba: int, model_type: str
    ) -> Optional[NagaOrderOrm]:
        stmt = select(MajsoulOrderOrm).where(
            MajsoulOrderOrm.paipu_uuid == majsoul_uuid,
            MajsoulOrderOrm.kyoku == kyoku,
            MajsoulOrderOrm.honba == honba,
            MajsoulOrderOrm.model_type == model_type,
        )

        order_orm: Optional[MajsoulOrderOrm] = (
            await self.sess.execute(stmt)
        ).scalar_one_or_none()
        if order_orm is not None:
            if (
                order_orm.order.status == NagaOrderStatus.ok
                or datetime.now(tz=timezone.utc).timestamp()
                - order_orm.order.update_time.timestamp()
                < 90
            ):
                return order_orm.order
            else:  # 超过90s仍未分析完成则删除重来
                logger.opt(colors=True).info(
                    f"Delete majsoul paipu <y>{majsoul_uuid} "
                    f"(kyoku: {kyoku}, honba: {honba})</y> "
                    f"analyze order: {order_orm.naga_haihu_id}, "
                    f"because it takes over 90 seconds and still not done"
                )
                await self.sess.delete(order_orm.order)
                await self.sess.delete(order_orm)
                await self.sess.commit()
                return None

    async def new_local_majsoul_order(
        self,
        haihu_id: str,
        customer_id: int,
        majsoul_uuid: str,
        kyoku: int,
        honba: int,
        model_type: str,
    ):
        order_orm = NagaOrderOrm(
            haihu_id=haihu_id,
            customer_id=customer_id,
            cost_np=10,
            source=NagaOrderSource.majsoul,
            model_type=model_type,
            status=NagaOrderStatus.analyzing,
            create_time=datetime.now(tz=timezone.utc),
            update_time=datetime.now(tz=timezone.utc),
        )

        majsoul_order_orm = MajsoulOrderOrm(
            naga_haihu_id=haihu_id,
            paipu_uuid=majsoul_uuid,
            kyoku=kyoku,
            honba=honba,
            model_type=model_type,
            order=order_orm,
        )

        self.sess.add(order_orm)
        self.sess.add(majsoul_order_orm)
        await self.sess.commit()

    async def get_local_order(
        self, haihu_id: str, model_type: str
    ) -> Optional[NagaOrderOrm]:
        stmt = select(NagaOrderOrm).where(
            NagaOrderOrm.haihu_id == haihu_id,
            NagaOrderOrm.model_type == model_type,
        )

        order_orm: Optional[NagaOrderOrm] = (
            await self.sess.execute(stmt)
        ).scalar_one_or_none()
        if order_orm is not None:
            if (
                order_orm.status == NagaOrderStatus.ok
                or datetime.now(tz=timezone.utc).timestamp()
                - order_orm.update_time.timestamp()
                < 300
            ):
                return order_orm
            else:  # 超过90s仍未分析完成则删除重来
                logger.opt(colors=True).info(
                    f"Delete tenhou paipu <y>{haihu_id}</y> analyze order "
                    f"because it takes over 90 seconds and still not done"
                )
                await self.sess.delete(order_orm)
                await self.sess.commit()
                return None

    async def new_local_order(
        self, haihu_id: str, customer_id: int, rule: NagaGameRule, model_type: str
    ):
        order_orm = NagaOrderOrm(
            haihu_id=haihu_id,
            customer_id=customer_id,
            cost_np=50 if rule == NagaGameRule.hanchan else 30,
            source=NagaOrderSource.tenhou,
            model_type=model_type,
            status=NagaOrderStatus.analyzing,
            create_time=datetime.now(tz=timezone.utc),
            update_time=datetime.now(tz=timezone.utc),
        )

        self.sess.add(order_orm)
        await self.sess.commit()

    async def update_local_order(self, haihu_id: str, report: NagaReport):
        stmt = (
            update(NagaOrderOrm)
            .where(NagaOrderOrm.haihu_id == haihu_id)
            .values(
                status=NagaOrderStatus.ok,
                naga_report=report,
                update_time=datetime.now(timezone.utc),
            )
        )
        await self.sess.execute(stmt)
        await self.sess.commit()
