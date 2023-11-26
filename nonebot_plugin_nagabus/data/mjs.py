import json

from nonebot import logger
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_majsoul.paipu import download_paipu

from .base import SqlModel
from ..data.utils import insert
from ..data.session import get_session


class MajsoulPaipuOrm(SqlModel):
    __tablename__ = "nonebot_plugin_nagabus_majsoul_paipu"
    __table_args__ = {"extend_existing": True}

    paipu_uuid: Mapped[str] = mapped_column(primary_key=True)
    content: Mapped[str]


async def get_majsoul_paipu(uuid: str):
    sess = get_session()

    stmt = select(MajsoulPaipuOrm).where(MajsoulPaipuOrm.paipu_uuid == uuid).limit(1)
    res = (await sess.execute(stmt)).scalar_one_or_none()

    if res is not None:
        logger.opt(colors=True).info(f"Use cached majsoul paipu <y>{uuid}</y>")
        return json.loads(res.content)

    logger.opt(colors=True).info(f"Downloading majsoul paipu <y>{uuid}</y> ...")
    data = await download_paipu(uuid)

    stmt = (
        insert(MajsoulPaipuOrm)
        .values(paipu_uuid=uuid, content=json.dumps(data))
        .on_conflict_do_nothing(index_elements=[MajsoulPaipuOrm.paipu_uuid])
    )

    await sess.execute(stmt)
    await sess.commit()

    return data
