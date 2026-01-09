"""
구조화된 로깅 및 요청/응답 로깅

JSON 형식의 구조화된 로그와 요청/응답 추적을 제공합니다.
"""
import logging
import json
import time
import uuid
from datetime import datetime
from typing import Any, Optional
from functools import wraps

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# JSON 로그 포매터
class JSONFormatter(logging.Formatter):
    """JSON 형식의 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 추가 필드
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, "user_agent"):
            log_data["user_agent"] = record.user_agent
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


# 로거 설정
def setup_logger(
    name: str = "api_engine",
    level: int = logging.INFO,
    json_format: bool = True,
) -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 기존 핸들러 제거
    logger.handlers.clear()
    
    # 콘솔 핸들러
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
    
    logger.addHandler(handler)
    return logger


# 기본 로거
logger = setup_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or setup_logger("api_engine.request")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 요청 ID 생성
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # 시작 시간
        start_time = time.time()
        
        # 클라이언트 정보
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 요청 로그
        self.logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "extra_data": {
                    "query_params": str(request.query_params) if request.query_params else None,
                }
            }
        )
        
        # 응답 처리
        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # 응답 로그
            level = logging.INFO if response.status_code < 400 else logging.WARNING
            if response.status_code >= 500:
                level = logging.ERROR
            
            self.logger.log(
                level,
                f"← {response.status_code} ({duration_ms}ms)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                }
            )
            
            # 응답 헤더에 요청 ID 추가
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                f"✗ Error: {str(e)} ({duration_ms}ms)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "extra_data": {"error": str(e)}
                },
                exc_info=True,
            )
            raise


class APICallLogger:
    """API 호출 로깅 유틸리티"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or setup_logger("api_engine.api")
    
    def log_api_call(
        self,
        api_path: str,
        method: str,
        logic_type: str,
        params: dict[str, Any],
        result: Optional[dict] = None,
        error: Optional[str] = None,
        duration_ms: float = 0,
        request_id: Optional[str] = None,
    ):
        """API 호출 로그"""
        extra_data = {
            "api_path": api_path,
            "logic_type": logic_type,
            "param_count": len(params),
        }
        
        if result:
            extra_data["result_count"] = result.get("count", result.get("result_count", 0))
            extra_data["success"] = result.get("success", True)
        
        if error:
            extra_data["error"] = error
            self.logger.error(
                f"API 실행 실패: {api_path}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": api_path,
                    "duration_ms": duration_ms,
                    "extra_data": extra_data,
                }
            )
        else:
            self.logger.info(
                f"API 실행 성공: {api_path} ({duration_ms}ms)",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": api_path,
                    "duration_ms": duration_ms,
                    "extra_data": extra_data,
                }
            )
    
    def log_sql_execution(
        self,
        query: str,
        params: dict[str, Any],
        row_count: int,
        duration_ms: float,
        request_id: Optional[str] = None,
    ):
        """SQL 실행 로그"""
        # 쿼리 요약 (첫 100자)
        query_summary = query[:100] + "..." if len(query) > 100 else query
        query_summary = query_summary.replace("\n", " ").strip()
        
        self.logger.debug(
            f"SQL 실행: {query_summary}",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "extra_data": {
                    "query_type": query.strip().split()[0].upper() if query.strip() else "UNKNOWN",
                    "row_count": row_count,
                    "param_count": len(params),
                }
            }
        )


# 전역 API 콜 로거
api_logger = APICallLogger()


def log_execution(func):
    """실행 시간 로깅 데코레이터"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.debug(
                f"{func.__name__} 실행 완료 ({duration_ms}ms)",
                extra={"duration_ms": duration_ms}
            )
            return result
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"{func.__name__} 실행 실패: {str(e)} ({duration_ms}ms)",
                extra={"duration_ms": duration_ms, "extra_data": {"error": str(e)}},
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.debug(
                f"{func.__name__} 실행 완료 ({duration_ms}ms)",
                extra={"duration_ms": duration_ms}
            )
            return result
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"{func.__name__} 실행 실패: {str(e)} ({duration_ms}ms)",
                extra={"duration_ms": duration_ms, "extra_data": {"error": str(e)}},
            )
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
