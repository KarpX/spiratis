from sqlalchemy.orm import Mapped, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import JSONB

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=lambda: {
        "platform": [], 
        "type": [], 
        "device": []
    })
    is_active: Mapped[bool] = mapped_column(default=True)


class SentGame(Base):
    __tablename__ = "sent_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column()
    game_id: Mapped[int] = mapped_column()
    sent_at: Mapped[str] = mapped_column()