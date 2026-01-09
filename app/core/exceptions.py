"""
사용자 정의 예외 클래스 및 에러 핸들링

이 모듈은 API에서 발생할 수 있는 다양한 예외를 정의하고
사용자 친화적인 에러 메시지를 제공합니다.
"""
from typing import Optional, Any
from fastapi import HTTPException


class ApiEngineError(Exception):
    """API 엔진 기본 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """에러를 딕셔너리로 변환"""
        result = {
            "success": False,
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(ApiEngineError):
    """유효성 검증 오류"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field, **(details or {})} if field else details,
        )


class NotFoundError(ApiEngineError):
    """리소스를 찾을 수 없음"""
    
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource}을(를) 찾을 수 없습니다."
        if identifier:
            message = f"{resource} '{identifier}'을(를) 찾을 수 없습니다."
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier) if identifier else None},
        )


class DuplicateError(ApiEngineError):
    """중복 데이터 오류"""
    
    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            message=f"이미 존재하는 {resource}입니다: {field}={value}",
            error_code="DUPLICATE_ERROR",
            status_code=409,
            details={"resource": resource, "field": field, "value": str(value)},
        )


class AuthenticationError(ApiEngineError):
    """인증 오류"""
    
    def __init__(self, message: str = "인증이 필요합니다."):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(ApiEngineError):
    """권한 오류"""
    
    def __init__(self, message: str = "이 작업을 수행할 권한이 없습니다."):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class ExecutionError(ApiEngineError):
    """로직 실행 오류"""
    
    def __init__(self, message: str, logic_type: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="EXECUTION_ERROR",
            status_code=500,
            details={"logic_type": logic_type, **(details or {})} if logic_type else details,
        )


class SecurityError(ApiEngineError):
    """보안 오류 (SQL Injection 등)"""
    
    def __init__(self, message: str, threat_type: str = "UNKNOWN"):
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            status_code=400,
            details={"threat_type": threat_type},
        )


class DatabaseError(ApiEngineError):
    """데이터베이스 오류"""
    
    def __init__(self, message: str = "데이터베이스 오류가 발생했습니다.", details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )


class ExternalServiceError(ApiEngineError):
    """외부 서비스 오류"""
    
    def __init__(self, service: str, message: str, details: Optional[dict] = None):
        super().__init__(
            message=f"{service} 서비스 오류: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service, **(details or {})},
        )


class RateLimitError(ApiEngineError):
    """요청 제한 오류"""
    
    def __init__(self, message: str = "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=429,
        )


class ImmutablePolicyError(ApiEngineError):
    """불변 정책 위반 오류"""
    
    def __init__(self, action: str, resource: str):
        super().__init__(
            message=f"불변 정책: {resource}에 대해 '{action}' 작업은 허용되지 않습니다.",
            error_code="IMMUTABLE_POLICY_VIOLATION",
            status_code=403,
            details={"action": action, "resource": resource},
        )


# 에러 코드 → 사용자 친화적 메시지 매핑
ERROR_MESSAGES = {
    "INTERNAL_ERROR": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    "VALIDATION_ERROR": "입력값이 올바르지 않습니다.",
    "NOT_FOUND": "요청한 리소스를 찾을 수 없습니다.",
    "DUPLICATE_ERROR": "이미 존재하는 데이터입니다.",
    "AUTHENTICATION_ERROR": "인증이 필요합니다. 로그인 후 다시 시도해주세요.",
    "AUTHORIZATION_ERROR": "이 작업을 수행할 권한이 없습니다.",
    "EXECUTION_ERROR": "요청을 처리하는 중 오류가 발생했습니다.",
    "SECURITY_ERROR": "보안 정책에 의해 요청이 차단되었습니다.",
    "DATABASE_ERROR": "데이터베이스 오류가 발생했습니다.",
    "EXTERNAL_SERVICE_ERROR": "외부 서비스 연동 중 오류가 발생했습니다.",
    "RATE_LIMIT_ERROR": "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
    "IMMUTABLE_POLICY_VIOLATION": "불변 정책에 의해 이 작업은 허용되지 않습니다.",
}


def get_user_friendly_message(error_code: str) -> str:
    """에러 코드에 대한 사용자 친화적 메시지 반환"""
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["INTERNAL_ERROR"])
