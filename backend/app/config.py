"""
The Agent — 설정 관리
환경변수에서 설정을 로드. .env 파일 또는 시스템 환경변수 모두 지원.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """앱 전체 설정. 환경변수에서 자동 로드."""

    # --- App ---
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"
    allowed_origins: str = "http://localhost:5173"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://theagent:devpassword@localhost:5432/theagent"

    # --- LLM API Keys ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # --- LLM Models (4-Model Architecture) ---
    llm_worker_model: str = "gpt-4o-mini"                   # [M1] Worker: 파싱, 구조화 (OpenAI)
    llm_stabilizer_model: str = "claude-3-5-sonnet-latest"  # [M2] Stabilizer: 정리, 분해 (Anthropic)
    llm_judge_model: str = "claude-sonnet-4-6-opus-latest"  # [M3] Judge: 판단, 개입 (Anthropic)
    llm_distiller_model: str = "claude-3-5-sonnet-latest"   # [M4] Distiller: 기억 정제 (Anthropic)

    # --- Judge 호출 제한 ---
    judge_max_calls_per_day: int = 3

    # --- Obsidian (Phase 2) ---
    obsidian_vault_path: str = ""

    # --- Telegram (Phase 3) ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 앱 전체에서 공유."""
    return Settings()
