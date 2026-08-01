from datetime import datetime

from sqlalchemy import BigInteger, BigInteger, DateTime, Integer, func
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import JSONB

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=lambda: {
        "platform": [], 
        "type": [], 
        "device": []
    })
    is_active: Mapped[bool] = mapped_column(default=True)
    timezone_offset: Mapped[int] = mapped_column(Integer, default=0)


class SentGame(Base):
    __tablename__ = "sent_games"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    game_id: Mapped[int] = mapped_column(Integer)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )