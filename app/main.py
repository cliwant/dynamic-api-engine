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
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import (
    ApiEngineError,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ExecutionError,
    SecurityError,
    DatabaseError,
    get_user_friendly_message,
)
from app.core.logging import RequestLoggingMiddleware, logger
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

# 요청/응답 로깅 미들웨어
app.add_middleware(RequestLoggingMiddleware)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================
# 예외 핸들러
# ==================================

@app.exception_handler(ApiEngineError)
async def api_engine_error_handler(request: Request, exc: ApiEngineError):
    """API 엔진 커스텀 예외 처리"""
    logger.warning(
        f"API Error: {exc.error_code} - {exc.message}",
        extra={
            "extra_data": {
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI 요청 유효성 검증 오류 처리"""
    errors = exc.errors()
    
    # 첫 번째 오류의 상세 정보
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "입력값이 올바르지 않습니다.")
    
    logger.warning(
        f"Validation Error: {field} - {message}",
        extra={"extra_data": {"errors": errors}}
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": f"입력값 오류: {message}",
            "details": {
                "field": field,
                "errors": [
                    {
                        "field": ".".join(str(loc) for loc in err.get("loc", [])),
                        "message": err.get("msg"),
                        "type": err.get("type"),
                    }
                    for err in errors
                ],
            },
        },
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_handler(request: Request, exc: PydanticValidationError):
    """Pydantic 유효성 검증 오류 처리"""
    errors = exc.errors()
    
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "데이터 형식이 올바르지 않습니다.")
    
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": f"데이터 형식 오류: {message}",
            "details": {"field": field},
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """SQLAlchemy 데이터베이스 오류 처리"""
    logger.error(
        f"Database Error: {str(exc)}",
        extra={"extra_data": {"error_type": type(exc).__name__}},
        exc_info=True,
    )
    
    message = "데이터베이스 오류가 발생했습니다."
    if settings.debug:
        message = f"데이터베이스 오류: {str(exc)[:200]}"
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "DATABASE_ERROR",
            "message": message,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리 (catch-all)"""
    logger.error(
        f"Unhandled Error: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
    )
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": str(exc),
                "detail": repr(exc),
                "type": type(exc).__name__,
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": get_user_friendly_message("INTERNAL_ERROR"),
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

