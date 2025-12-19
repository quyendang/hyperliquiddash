import asyncio
import json
import websockets
from .hl_http import get_clearinghouse_state
from .repo import upsert_account_summary, upsert_position, insert_fill
from .config import REFRESH_SNAPSHOT_SECONDS
from .db import SessionLocal

HL_WS_URL = "wss://api.hyperliquid.xyz/ws"

def _safe_float(x, default=0.0):
    try: return float(x)
    except: return default

async def apply_snapshot(wallet: str):
    async with SessionLocal() as db:
        st = await get_clearinghouse_state(wallet)
        # Schema có thể thay đổi; nên parse “best-effort”
        summary = st.get("marginSummary") or st.get("crossMarginSummary") or {}
        account_value = _safe_float(summary.get("accountValue") or summary.get("totalNtlPos") or 0)
        margin_used = _safe_float(summary.get("marginUsed") or 0)
        unrealized = 0.0

        # positions thường nằm trong "assetPositions"
        asset_positions = st.get("assetPositions") or []
        for ap in asset_positions:
            pos = ap.get("position") or ap.get("pos") or {}
            coin = str(pos.get("coin") or ap.get("coin") or "")
            szi = _safe_float(pos.get("szi") or pos.get("size") or 0)  # HL hay dùng szi signed
            side = "LONG" if szi > 0 else ("SHORT" if szi < 0 else "")
            size = abs(szi)
            entry = _safe_float(pos.get("entryPx") or pos.get("entry_px") or 0)
            mark = _safe_float(pos.get("markPx") or pos.get("mark_px") or 0)
            liq = _safe_float(pos.get("liqPx") or pos.get("liq_px") or 0)
            lev = _safe_float(pos.get("leverage") or pos.get("lev") or 0)
            upnl = _safe_float(pos.get("unrealizedPnl") or pos.get("upnl") or 0)
            unrealized += upnl

            await upsert_position(db, wallet, coin, {
                "side": side, "size": size, "entry_px": entry, "mark_px": mark,
                "liq_px": liq, "leverage": lev, "unrealized_pnl": upnl
            })

        await upsert_account_summary(db, wallet, account_value, margin_used, unrealized)

async def ws_worker(get_wallets_callable):
    backoff = 1
    while True:
        try:
            wallets = [w.address.lower() for w in await get_wallets_callable()]
            if not wallets:
                await asyncio.sleep(2)
                continue

            # snapshot ban đầu
            for w in wallets:
                await apply_snapshot(w)

            async with websockets.connect(HL_WS_URL, ping_interval=20, ping_timeout=20) as ws:
                backoff = 1

                # subscribe userFills + userEvents cho từng ví
                for w in wallets:
                    await ws.send(json.dumps({"method":"subscribe","subscription":{"type":"userFills","user":w}}))
                    await ws.send(json.dumps({"method":"subscribe","subscription":{"type":"userEvents","user":w}}))

                async def periodic_snapshots():
                    while True:
                        await asyncio.sleep(REFRESH_SNAPSHOT_SECONDS)
                        wallets2 = [x.address.lower() for x in await get_wallets_callable()]
                        for w2 in wallets2:
                            await apply_snapshot(w2)

                snap_task = asyncio.create_task(periodic_snapshots())

                try:
                    async for raw in ws:
                        msg = json.loads(raw)

                        # docs nói có isSnapshot trong một số stream; bỏ qua nếu muốn :contentReference[oaicite:5]{index=5}
                        if isinstance(msg, dict) and msg.get("isSnapshot") is True:
                            continue

                        # message thường dạng {"channel": "...", "data": ...}
                        if not isinstance(msg, dict):
                            continue
                        data = msg.get("data")

                        # userFills: insert fills
                        if msg.get("channel") == "userFills" and isinstance(data, list):
                            async with SessionLocal() as db:
                                for f in data:
                                    wallet = (f.get("user") or f.get("address") or "").lower()
                                    if wallet:
                                        await insert_fill(db, wallet, f)

                        # userEvents: khi có event -> snapshot lại để cập nhật positions nhanh
                        if msg.get("channel") == "userEvents":
                            # data có thể là dict/list; cứ trigger snapshot nhẹ
                            # (tối ưu sau: parse event để chỉ update coin liên quan)
                            wallets3 = [x.address.lower() for x in await get_wallets_callable()]
                            for w3 in wallets3:
                                await apply_snapshot(w3)

                finally:
                    snap_task.cancel()

        except Exception:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
