from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, BigInteger, Float, Boolean, UniqueConstraint, Index, Text
from sqlalchemy import DateTime, func

class Base(DeclarativeBase):
    pass

class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(256), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AccountSummary(Base):
    __tablename__ = "account_summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    wallet: Mapped[str] = mapped_column(String(128), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    account_value: Mapped[float] = mapped_column(Float, default=0.0)
    margin_used: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (UniqueConstraint("wallet", name="uq_account_summary_wallet"),)

class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    wallet: Mapped[str] = mapped_column(String(128), index=True)
    coin: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8), default="")  # LONG/SHORT
    size: Mapped[float] = mapped_column(Float, default=0.0)
    entry_px: Mapped[float] = mapped_column(Float, default=0.0)
    mark_px: Mapped[float] = mapped_column(Float, default=0.0)
    liq_px: Mapped[float] = mapped_column(Float, default=0.0)
    leverage: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("wallet", "coin", name="uq_position_wallet_coin"),
        Index("ix_positions_wallet_updated", "wallet", "updated_at"),
    )

class Fill(Base):
    __tablename__ = "fills"
    id: Mapped[int] = mapped_column(primary_key=True)
    wallet: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[int] = mapped_column(BigInteger, index=True)  # ms
    coin: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8), default="")  # BUY/SELL
    px: Mapped[float] = mapped_column(Float, default=0.0)
    sz: Mapped[float] = mapped_column(Float, default=0.0)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    fill_id: Mapped[str] = mapped_column(String(128), default="")  # best-effort unique key
    raw: Mapped[str] = mapped_column(Text, default="")

    __table_args__ = (
        UniqueConstraint("wallet", "fill_id", name="uq_fill_wallet_fillid"),
        Index("ix_fills_wallet_ts", "wallet", "ts"),
    )
