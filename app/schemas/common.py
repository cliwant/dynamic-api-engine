"""
공통 스키마 정의
"""
from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """기본 응답 스키마"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    success: bool = False
    error_code: str
    message: str
    detail: Optional[Any] = None
    
    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    """페이지네이션 파라미터"""
    page: int = Field(default=1, ge=1, description="페이지 번호")
    size: int = Field(default=20, ge=1, le=100, description="페이지 크기")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 응답 스키마"""
    success: bool = True
    data: list[T]
    total: int
    page: int
    size: int
    total_pages: int
    
    class Config:
        from_attributes = True

