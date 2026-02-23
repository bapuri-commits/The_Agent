"""
The Agent — FastAPI 앱 진입점
라이프사이클 관리, 라우터 등록, CORS 설정.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.ws.manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 코드."""
    settings = get_settings()

    # --- Startup ---
    print("🚀 The Agent 시작 중...")
    await init_db()
    print("✅ DB 초기화 완료")

    # TODO: APScheduler 시작 (Phase 1 Step 3.1)

    print(f"✅ The Agent 준비 완료 (env={settings.app_env})")
    print(f"   WebSocket: /ws/chat")

    yield

    # --- Shutdown ---
    print("🛑 The Agent 종료 중...")
    # TODO: APScheduler 종료


# --- App 생성 ---
settings = get_settings()

app = FastAPI(
    title="The Agent",
    description="ADHD-friendly Personal AI Secretary",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes ---
@app.get("/health")
async def health_check():
    """시스템 상태 확인."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "message": "The Agent is running",
    }


# API 라우터 등록
from app.api import inbox, tasks, chat

app.include_router(inbox.router, prefix="/api/v1", tags=["inbox"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])


# --- WebSocket ---
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 연결. Step 3.1 (Enforcement) 알림에서 본격 사용."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.send_personal(websocket, {
                "type": "ack",
                "message": "received",
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
