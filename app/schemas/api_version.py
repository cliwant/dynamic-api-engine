"""
API 버전 스키마 정의
"""
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re


class RequestFieldSpec(BaseModel):
    """요청 필드 스펙"""
    type: Literal["string", "int", "float", "bool", "array", "object"] = Field(..., description="필드 타입")
    required: bool = Field(default=False, description="필수 여부")
    default: Optional[Any] = Field(None, description="기본값")
    min_length: Optional[int] = Field(None, description="최소 길이 (string)")
    max_length: Optional[int] = Field(None, description="최대 길이 (string)")
    min_value: Optional[float] = Field(None, description="최소값 (int, float)")
    max_value: Optional[float] = Field(None, description="최대값 (int, float)")
    pattern: Optional[str] = Field(None, description="정규표현식 패턴 (string)")
    enum: Optional[list] = Field(None, description="허용 값 목록")
    description: Optional[str] = Field(None, description="필드 설명")


class ApiVersionBase(BaseModel):
    """API 버전 기본 스키마"""
    request_spec: Optional[dict[str, Any]] = Field(
        None, 
        description="요청 파라미터 검증 규칙 (예: {'user_id': {'type': 'int', 'required': true}})"
    )
    logic_type: Literal["SQL", "PYTHON_EXPR", "HTTP_CALL", "STATIC_RESPONSE"] = Field(
        default="SQL",
        description="로직 타입"
    )
    logic_body: str = Field(
        ..., 
        min_length=1,
        description="실행할 로직 (SQL 쿼리, Python 표현식 등)"
    )
    logic_config: Optional[dict[str, Any]] = Field(
        None,
        description="로직 추가 설정 (타임아웃, 재시도 등)"
    )
    response_spec: Optional[dict[str, Any]] = Field(
        None,
        description="응답 데이터 매핑 규칙 (예: {'data': '$result', 'count': '$result_count'})"
    )
    status_codes: Optional[dict[str, int]] = Field(
        None,
        description="상태 코드 매핑 (예: {'success': 200, 'not_found': 404})"
    )
    change_note: Optional[str] = Field(
        None,
        description="변경 사유"
    )
    sample_params: Optional[dict[str, Any]] = Field(
        None,
        description="테스트용 샘플 파라미터 값 (예: {'user_id': 1, 'limit': 10})"
    )
    
    @field_validator("logic_body")
    @classmethod
    def validate_logic_body(cls, v: str, info) -> str:
        """로직 본문 유효성 검사 (SQL Injection 위험 패턴 감지)"""
        # 위험한 SQL 패턴 감지
        dangerous_patterns = [
            r'\bDROP\s+', r'\bTRUNCATE\s+', r'\bDELETE\s+FROM\s+',
            r'\bALTER\s+TABLE\s+', r'\bCREATE\s+TABLE\s+',
            r';\s*--', r'/\*.*\*/',  # SQL 주석
            r'\bEXEC\s*\(', r'\bEXECUTE\s*\(',  # 동적 SQL 실행
        ]
        v_upper = v.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, v_upper, re.IGNORECASE):
                raise ValueError(f"보안 위험: 허용되지 않는 SQL 패턴이 감지되었습니다.")
        return v


class ApiVersionCreate(ApiVersionBase):
    """API 버전 생성 스키마"""
    route_id: str = Field(..., description="API 라우트 ID")


class ApiVersionResponse(BaseModel):
    """API 버전 응답 스키마"""
    id: str
    route_id: str
    version: int
    is_current: bool
    request_spec: Optional[dict[str, Any]]
    logic_type: str
    logic_body: str
    logic_config: Optional[dict[str, Any]]
    response_spec: Optional[dict[str, Any]]
    status_codes: Optional[dict[str, int]]
    change_note: Optional[str]
    sample_params: Optional[dict[str, Any]]
    created_at: datetime
    created_by: Optional[str]
    
    class Config:
        from_attributes = True


class ApiVersionListResponse(BaseModel):
    """API 버전 목록 응답 스키마"""
    id: str
    route_id: str
    version: int
    is_current: bool
    logic_type: str
    change_note: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    
    class Config:
        from_attributes = True
