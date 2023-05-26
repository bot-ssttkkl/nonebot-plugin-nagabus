from sqlalchemy.orm import Mapped, mapped_column

from .base import SqlModel


class MajsoulPaipuOrm(SqlModel):
    __tablename__ = 'nonebot_plugin_nagabus_majsoul_paipu'
    __table_args__ = {"extend_existing": True}

    paipu_uuid: Mapped[str] = mapped_column(primary_key=True)
    content: Mapped[str]
