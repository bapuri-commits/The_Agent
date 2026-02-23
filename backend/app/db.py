"""
The Agent — 데이터베이스 설정
SQLAlchemy async 엔진 + 세션 관리.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# 비동기 엔진 생성
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",  # 개발 중에만 SQL 로그
    pool_pre_ping=True,
)

# 세션 팩토리
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """모든 ORM 모델의 베이스 클래스."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 의존성 주입용 DB 세션 제공."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """DB 테이블 생성 + 초기 데이터 삽입."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data
    async with async_session() as session:
        from app.models import UserProfile, Project

        # user_profile (id=1) 존재 확인
        existing_profile = await session.get(UserProfile, 1)
        if not existing_profile:
            session.add(UserProfile(id=1))

        # "미분류" 프로젝트 존재 확인
        from sqlalchemy import select
        result = await session.execute(
            select(Project).where(Project.name == "미분류")
        )
        if not result.scalar_one_or_none():
            session.add(Project(name="미분류", type="personal"))

        await session.commit()
