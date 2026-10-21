from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="vendedor")  # admin | vendedor
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CostItem(Base):
    """Costos operativos y administrativos USA (USD/mes). share_pct = % que paga HERMOIT."""
    __tablename__ = "cost_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    usd: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    share_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=100)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Setting(Base):
    """Parámetros globales: params (fx, margen, comisión, costo variable), tf (factores por territorio), checks (campaña)."""
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[dict] = mapped_column(JsonType)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid generado por el cliente
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    company: Mapped[str] = mapped_column(String(200))
    contact: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    vertical: Mapped[str] = mapped_column(String(20), default="pyme")
    territory: Mapped[str] = mapped_column(String(10), default="valle")
    plan: Mapped[int] = mapped_column(Integer, default=1)
    users: Mapped[int] = mapped_column(Integer, default=10)
    filial: Mapped[str] = mapped_column(String(40), default="")
    stage: Mapped[int] = mapped_column(Integer, default=0)
    next_step: Mapped[str] = mapped_column(String(300), default="")
    next_date: Mapped[str] = mapped_column(String(10), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="app")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Assessment(Base):
    """Network Assessment en curso por usuario (data = respuestas del formulario, prop = ajustes de la propuesta)."""
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    data: Mapped[dict] = mapped_column(JsonType, default=dict)
    prop: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
