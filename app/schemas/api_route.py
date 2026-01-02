"""
API 라우트 스키마 정의
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re


class ApiRouteBase(BaseModel):
    """API 라우트 기본 스키마"""
    path: str = Field(..., min_length=1, max_length=255, description="API 경로")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(..., description="HTTP 메서드")
    name: Optional[str] = Field(None, max_length=255, description="API 이름")
    description: Optional[str] = Field(None, description="API 설명")
    tags: Optional[str] = Field(None, max_length=500, description="태그 (쉼표로 구분)")
    require_auth: bool = Field(default=False, description="인증 필요 여부")
    allowed_origins: Optional[str] = Field(None, description="허용된 Origin")
    rate_limit: int = Field(default=100, ge=1, le=10000, description="분당 요청 제한")
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """경로 유효성 검사: 영문, 숫자, 하이픈, 언더스코어, 슬래시만 허용"""
        if not re.match(r'^[a-zA-Z0-9/_-]+$', v):
            raise ValueError("경로는 영문, 숫자, 하이픈(-), 언더스코어(_), 슬래시(/)만 사용할 수 있습니다.")
        # 선행/후행 슬래시 제거
        return v.strip("/")
    
    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """메서드 대문자 변환"""
        return v.upper()


class ApiRouteCreate(ApiRouteBase):
    """API 라우트 생성 스키마"""
    pass


class ApiRouteUpdate(BaseModel):
    """API 라우트 수정 스키마 (부분 업데이트 지원)"""
    name: Optional[str] = Field(None, max_length=255, description="API 이름")
    description: Optional[str] = Field(None, description="API 설명")
    tags: Optional[str] = Field(None, max_length=500, description="태그")
    require_auth: Optional[bool] = Field(None, description="인증 필요 여부")
    allowed_origins: Optional[str] = Field(None, description="허용된 Origin")
    rate_limit: Optional[int] = Field(None, ge=1, le=10000, description="분당 요청 제한")
    is_active: Optional[bool] = Field(None, description="활성화 여부")


class ApiRouteResponse(BaseModel):
    """API 라우트 응답 스키마"""
    id: str
    path: str
    method: str
    name: Optional[str]
    description: Optional[str]
    tags: Optional[str]
    is_active: bool
    is_deleted: bool
    require_auth: bool
    allowed_origins: Optional[str]
    rate_limit: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    current_version: Optional[int] = None  # 현재 활성 버전
    
    class Config:
        from_attributes = True


class ApiRouteListResponse(BaseModel):
    """API 라우트 목록 응답 스키마"""
    id: str
    path: str
    method: str
    name: Optional[str]
    is_active: bool
    require_auth: bool
    created_at: datetime
    current_version: Optional[int] = None
    
    class Config:
        from_attributes = True
