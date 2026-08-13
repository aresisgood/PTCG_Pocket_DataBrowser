"""FastAPI 應用組裝。

啟動時建立資料表,掛載牌組路由,並以 StaticFiles 直接服務 web/ 前端
(讓前端與 API 同源,免除 CORS 問題)。
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from project_config import DATA_DIR, ROOT

from .db import create_db_engine, get_database_url, init_db
from .routers import decks, predict
from .schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db(app.state.db_engine)
        yield
    finally:
        app.state.db_engine.dispose()


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="PTCG Pocket Deck Lab", lifespan=lifespan)
    app.state.db_engine = create_db_engine(database_url or get_database_url())
    app.include_router(decks.router)
    app.include_router(predict.router)

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse()

    cards_path = DATA_DIR / "cards.json"

    @app.get("/data/cards.json", include_in_schema=False)
    def get_cards_data() -> FileResponse:
        if not cards_path.is_file():
            raise HTTPException(status_code=404, detail="cards data not found")
        return FileResponse(cards_path, media_type="application/json")

    # 前端靜態檔掛在最後,避免蓋掉 /api 與 /data。
    web_dir = ROOT / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


app = create_app()
