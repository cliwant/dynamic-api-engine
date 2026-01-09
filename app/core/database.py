"""
데이터베이스 연결 및 세션 관리
비동기 SQLAlchemy를 사용한 MySQL 연결

보안 기능:
- 기본 연결: 전체 권한 (API 정의 관리용)
- 읽기 전용 연결: SELECT만 허용 (자연어 SQL 쿼리용)
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ========================================
# 기본 DB 연결 (전체 권한)
# ========================================
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ========================================
# 읽기 전용 DB 연결 (SELECT만 허용)
# 자연어 SQL 쿼리, 스키마 조회 등에 사용
# ========================================
readonly_engine = create_async_engine(
    settings.readonly_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,  # 읽기 전용은 작은 풀 사용
    max_overflow=10,
)

readonly_session_maker = async_sessionmaker(
    readonly_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 읽기 전용 계정 설정 여부 경고
if not settings.has_readonly_account:
    logger.warning(
        "⚠️ 읽기 전용 DB 계정이 설정되지 않았습니다. "
        "자연어 SQL 쿼리 기능은 기본 계정을 사용합니다. "
        "보안을 위해 MYSQL_READONLY_USER, MYSQL_READONLY_PASSWORD 환경변수를 설정하세요."
    )
else:
    logger.info(f"✅ 읽기 전용 DB 계정 활성화: {settings.mysql_readonly_user}")

# Base 클래스
Base = declarative_base()


async def get_db() -> AsyncSession:
    """의존성 주입용 DB 세션 제공 (전체 권한)"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_readonly_db() -> AsyncSession:
    """
    읽기 전용 DB 세션 제공
    
    사용 목적:
    - 자연어 SQL 쿼리 실행
    - 스키마 조회
    - 데이터 조회 API
    
    보안 특징:
    - commit()이 호출되지 않음
    - DDL/DML 실행 불가 (DB 계정 권한으로 제한)
    """
    async with readonly_session_maker() as session:
        try:
            yield session
            # 읽기 전용이므로 commit하지 않음
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """데이터베이스 테이블 초기화"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

