"""
헬스체크 라우터
서버 상태 확인용 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "service": "Prompt API Engine"}


@router.get("/db")
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """데이터베이스 연결 상태 확인"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

