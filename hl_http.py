import httpx

HL_INFO_URL = "https://api.hyperliquid.xyz/info"

async def hl_info(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(HL_INFO_URL, json=payload)
        r.raise_for_status()
        return r.json()

async def get_clearinghouse_state(wallet: str) -> dict:
    # Perp account summary + positions
    return await hl_info({"type": "clearinghouseState", "user": wallet})

async def get_user_fills(wallet: str, start_time_ms: int | None = None) -> dict:
    body = {"type": "userFills", "user": wallet}
    if start_time_ms is not None:
        body["startTime"] = start_time_ms
    return await hl_info(body)
