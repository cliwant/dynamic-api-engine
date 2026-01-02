"""
Prompt API Engine - 메인 애플리케이션

MySQL 테이블 행 추가/수정만으로 API를 생성/수정하는 동적 API 엔진입니다.

주요 기능:
- 코드 배포 없이 DB 설정만으로 API 생성/수정
- 버전 관리를 통한 롤백 지원
- 감사 로그를 통한 변경 이력 추적
- SQL Injection 방지 및 보안 기능
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_db
from app.routers import universal_router, admin_router, health_router
from app.routers.schema_router import router as schema_router

# 정적 파일 경로
STATIC_DIR = Path(__file__).parent / "static"

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    print("🚀 Prompt API Engine 시작 중...")
    await init_db()
    print("✅ 데이터베이스 초기화 완료")
    print(f"📡 서버 준비 완료: {settings.app_name}")
    
    yield
    
    # Shutdown
    print("👋 서버 종료 중...")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    description="""
## Prompt API Engine

MySQL 테이블 행 추가/수정만으로 API를 생성하고 관리하는 동적 API 엔진입니다.

### 주요 기능

- **동적 API 생성**: DB에 행을 추가하면 즉시 새 API 엔드포인트 활성화
- **버전 관리**: 모든 변경 사항을 버전으로 관리, 언제든 롤백 가능
- **감사 로그**: 모든 변경 이력을 자동 기록
- **보안**: SQL Injection 방지, Soft Delete, API 키 인증

### 엔드포인트 구조

- `/api/{path}` - 동적으로 생성된 API 호출
- `/admin/*` - API 정의 관리 (API 키 필요)
- `/health` - 헬스체크
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": str(exc),
                "detail": repr(exc),
            }
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        }
    )


# 라우터 등록
app.include_router(health_router)
app.include_router(admin_router)
app.include_router(schema_router)
app.include_router(universal_router)  # 가장 마지막에 등록 (catch-all)


@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트 - API 테스터 UI로 리디렉트"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/tester", tags=["Root"])
async def api_tester():
    """API 테스터 UI"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/info", tags=["Root"])
async def info():
    """서비스 정보"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "tester": "/tester",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

