"""FastAPI 應用組裝。

啟動時建立資料表,掛載牌組路由,並以 StaticFiles 直接服務 web/ 前端
(讓前端與 API 同源,免除 CORS 問題)。
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from scraper.config import DATA_DIR, ROOT

from .db import init_db
from .routers import decks, predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PTCG Pocket Deck Lab", lifespan=lifespan)
    app.include_router(decks.router)
    app.include_router(predict.router)
    # 提供資料檔(cards.json 等)給前端;單人本機使用。
    if DATA_DIR.exists():
        app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
    # 前端靜態檔掛在最後,避免蓋掉 /api 與 /data。
    web_dir = ROOT / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


app = create_app()
