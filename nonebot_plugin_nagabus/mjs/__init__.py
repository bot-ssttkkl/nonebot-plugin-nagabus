import json

from nonebot import logger
from nonebot_plugin_majsoul.paipu import download_paipu
from sqlalchemy import select

from ..data.mjs import MajsoulPaipuOrm
from ..data.session import get_session
from ..data.utils import insert


async def get_majsoul_paipu(uuid: str):
    sess = get_session()

    stmt = select(MajsoulPaipuOrm).where(MajsoulPaipuOrm.paipu_uuid == uuid).limit(1)
    res = (await sess.execute(stmt)).scalar_one_or_none()

    if res is not None:
        logger.opt(colors=True).info(f"Use cached majsoul paipu <y>{uuid}</y>")
        return json.loads(res.content)

    logger.opt(colors=True).info(f"Downloading majsoul paipu <y>{uuid}</y> ...")
    data = await download_paipu(uuid)

    stmt = (insert(MajsoulPaipuOrm)
            .values(paipu_uuid=uuid, content=json.dumps(data))
            .on_conflict_do_nothing(index_elements=[MajsoulPaipuOrm.paipu_uuid]))

    await sess.execute(stmt)
    await sess.commit()

    return data
