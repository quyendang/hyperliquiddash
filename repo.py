import json
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from models import Wallet, Position, Fill, AccountSummary

async def list_active_wallets(db):
    rows = (await db.execute(select(Wallet).where(Wallet.is_active == True))).scalars().all()
    return rows

async def upsert_wallet(db, address: str, label: str = ""):
    address = address.lower().strip()
    stmt = pg_insert(Wallet).values(address=address, label=label, is_active=True)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Wallet.address],
        set_={"label": label, "is_active": True},
    )
    await db.execute(stmt)
    await db.commit()

async def deactivate_wallet(db, address: str):
    address = address.lower().strip()
    w = (await db.execute(select(Wallet).where(Wallet.address == address))).scalar_one_or_none()
    if w:
        w.is_active = False
        await db.commit()

async def upsert_account_summary(db, wallet: str, account_value: float, margin_used: float, unrealized_pnl: float):
    wallet = wallet.lower()
    stmt = pg_insert(AccountSummary).values(
        wallet=wallet,
        account_value=account_value,
        margin_used=margin_used,
        unrealized_pnl=unrealized_pnl,
    ).on_conflict_do_update(
        index_elements=[AccountSummary.wallet],
        set_={
            "account_value": account_value,
            "margin_used": margin_used,
            "unrealized_pnl": unrealized_pnl,
        },
    )
    await db.execute(stmt)
    await db.commit()

async def upsert_position(db, wallet: str, coin: str, data: dict):
    wallet = wallet.lower()
    stmt = pg_insert(Position).values(
        wallet=wallet,
        coin=coin,
        side=data.get("side",""),
        size=float(data.get("size",0) or 0),
        entry_px=float(data.get("entry_px",0) or 0),
        mark_px=float(data.get("mark_px",0) or 0),
        liq_px=float(data.get("liq_px",0) or 0),
        leverage=float(data.get("leverage",0) or 0),
        unrealized_pnl=float(data.get("unrealized_pnl",0) or 0),
    ).on_conflict_do_update(
        index_elements=[Position.wallet, Position.coin],
        set_={
            "side": data.get("side",""),
            "size": float(data.get("size",0) or 0),
            "entry_px": float(data.get("entry_px",0) or 0),
            "mark_px": float(data.get("mark_px",0) or 0),
            "liq_px": float(data.get("liq_px",0) or 0),
            "leverage": float(data.get("leverage",0) or 0),
            "unrealized_pnl": float(data.get("unrealized_pnl",0) or 0),
        },
    )
    await db.execute(stmt)
    await db.commit()

async def insert_fill(db, wallet: str, fill: dict):
    wallet = wallet.lower()
    # cố gắng tạo fill_id ổn định
    fill_id = str(fill.get("hash") or fill.get("oid") or fill.get("tid") or f'{fill.get("time")}-{fill.get("coin")}-{fill.get("px")}-{fill.get("sz")}')
    stmt = pg_insert(Fill).values(
        wallet=wallet,
        ts=int(fill.get("time") or fill.get("ts") or 0),
        coin=str(fill.get("coin") or ""),
        side=str(fill.get("side") or fill.get("dir") or ""),
        px=float(fill.get("px") or 0),
        sz=float(fill.get("sz") or 0),
        fee=float(fill.get("fee") or 0),
        fill_id=fill_id,
        raw=json.dumps(fill, ensure_ascii=False),
    ).on_conflict_do_nothing(
        index_elements=[Fill.wallet, Fill.fill_id]
    )
    await db.execute(stmt)
    await db.commit()
