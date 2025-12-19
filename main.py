import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import select, desc
from .config import APP_TITLE, UI_POLL_SECONDS
from .db import engine, SessionLocal
from .models import Base, Wallet, Position, Fill, AccountSummary
from .repo import list_active_wallets, upsert_wallet, deactivate_wallet
from .hl_ws import ws_worker
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def get_wallets():
        async with SessionLocal() as db:
            return await list_active_wallets(db)

    asyncio.create_task(ws_worker(get_wallets))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with SessionLocal() as db:
        wallets = (await db.execute(select(Wallet).where(Wallet.is_active == True).order_by(Wallet.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": APP_TITLE,
        "wallets": wallets,
        "ui_poll": UI_POLL_SECONDS,
    })

@app.post("/wallets/add")
async def add_wallet(address: str = Form(...), label: str = Form("")):
    async with SessionLocal() as db:
        await upsert_wallet(db, address, label)
    return HTMLResponse(status_code=204, content="")

@app.post("/wallets/remove")
async def remove_wallet(address: str = Form(...)):
    async with SessionLocal() as db:
        await deactivate_wallet(db, address)
    return HTMLResponse(status_code=204, content="")

@app.get("/wallet/{addr}", response_class=HTMLResponse)
async def wallet_page(request: Request, addr: str):
    addr = addr.lower()
    return templates.TemplateResponse("wallet.html", {
        "request": request,
        "title": APP_TITLE,
        "addr": addr,
        "ui_poll": UI_POLL_SECONDS,
    })

# ---- HTMX partials ----

@app.get("/partials/{addr}/summary", response_class=HTMLResponse)
async def partial_summary(request: Request, addr: str):
    addr = addr.lower()
    async with SessionLocal() as db:
        s = (await db.execute(select(AccountSummary).where(AccountSummary.wallet==addr))).scalar_one_or_none()
    return templates.TemplateResponse("_summary.html", {"request": request, "s": s})

@app.get("/partials/{addr}/positions", response_class=HTMLResponse)
async def partial_positions(request: Request, addr: str):
    addr = addr.lower()
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(Position).where(Position.wallet==addr).order_by(desc(Position.updated_at))
        )).scalars().all()
    return templates.TemplateResponse("_positions.html", {"request": request, "rows": rows})

@app.get("/partials/{addr}/fills", response_class=HTMLResponse)
async def partial_fills(request: Request, addr: str):
    addr = addr.lower()
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(Fill).where(Fill.wallet==addr).order_by(desc(Fill.ts)).limit(50)
        )).scalars().all()
    return templates.TemplateResponse("_fills.html", {"request": request, "rows": rows})
