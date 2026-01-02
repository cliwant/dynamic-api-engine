"""
관리자 라우터
API 정의 관리를 위한 엔드포인트

🔒 Immutable 정책:
- API Route와 Version은 추가만 가능 (수정/삭제 불가)
- 상태 변경(활성화/비활성화)과 현재 버전 설정만 허용
- 모든 변경 이력은 감사 로그에 기록됨
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.config import get_settings
from app.schemas.api_route import (
    ApiRouteCreate,
    ApiRouteResponse,
    ApiRouteListResponse,
)
from app.schemas.api_version import (
    ApiVersionCreate,
    ApiVersionResponse,
    ApiVersionListResponse,
)
from app.schemas.common import ResponseBase, PaginatedResponse
from app.services.api_route_service import ApiRouteService
from app.services.api_version_service import ApiVersionService
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


async def verify_api_key(x_api_key: str = Header(..., description="관리자 API 키")):
    """API 키 검증"""
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "message": "유효하지 않은 API 키입니다."}
        )
    return x_api_key


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ==================== 상태 변경 스키마 ====================

class StatusChangeRequest(BaseModel):
    """상태 변경 요청"""
    is_active: bool
    reason: Optional[str] = None


# ==================== 공개 API 목록 (인증 불필요) ====================

@router.get(
    "/routes",
    response_model=PaginatedResponse[ApiRouteListResponse],
    summary="API 라우트 목록 조회",
    description="API 키 없이 조회 가능한 공개 엔드포인트입니다.",
)
async def list_routes(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    include_inactive: bool = Query(False, description="비활성화된 API 포함"),
    db: AsyncSession = Depends(get_db),
):
    """API 라우트 목록을 조회합니다."""
    routes, total = await ApiRouteService.list_routes(
        db, page, size, include_inactive, include_deleted=False
    )
    
    # 각 라우트의 현재 버전 조회
    route_list = []
    for route in routes:
        current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
        route_data = ApiRouteListResponse(
            id=route.ROUTE_ID,
            path=route.API_PATH,
            method=route.HTTP_MTHD,
            name=route.API_NAME,
            is_active=route.USE_YN == 'Y',
            require_auth=route.AUTH_YN == 'Y',
            created_at=route.CREA_DT,
            current_version=current_version.VERSION_NO if current_version else None,
        )
        route_list.append(route_data)
    
    total_pages = (total + size - 1) // size
    
    return PaginatedResponse(
        data=route_list,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/routes/{route_id}",
    response_model=ResponseBase[ApiRouteResponse],
    summary="API 라우트 상세 조회",
    description="API 키 없이 조회 가능한 공개 엔드포인트입니다.",
)
async def get_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 API 라우트의 상세 정보를 조회합니다."""
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    
    if not route:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "API를 찾을 수 없습니다."}
        )
    
    current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
    
    return ResponseBase(
        data=ApiRouteResponse(
            id=route.ROUTE_ID,
            path=route.API_PATH,
            method=route.HTTP_MTHD,
            name=route.API_NAME,
            description=route.API_DESC,
            tags=route.TAGS,
            is_active=route.USE_YN == 'Y',
            is_deleted=route.DEL_YN == 'Y',
            require_auth=route.AUTH_YN == 'Y',
            allowed_origins=route.ALWD_ORGNS,
            rate_limit=int(route.RATE_LMT) if route.RATE_LMT else 100,
            created_at=route.CREA_DT,
            updated_at=route.UPDT_DT,
            created_by=route.CREA_BY,
            current_version=current_version.VERSION_NO if current_version else None,
        )
    )


# ==================== API 라우트 관리 (Immutable: 추가만 가능) ====================

@router.post(
    "/routes",
    response_model=ResponseBase[ApiRouteResponse],
    summary="API 라우트 생성 (추가 전용)",
    description="🔒 Immutable: 한 번 생성된 라우트는 수정/삭제할 수 없습니다. 상태 변경만 가능합니다.",
)
async def create_route(
    data: ApiRouteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    새로운 API 라우트를 생성합니다.
    
    🔒 Immutable 정책:
    - 생성 후 수정/삭제 불가
    - USE_YN을 통한 활성화/비활성화만 가능
    - 로직 변경 시 새 버전 추가
    """
    try:
        route = await ApiRouteService.create(
            db=db,
            data=data,
            actor="admin",
            actor_ip=get_client_ip(request),
        )
        
        return ResponseBase(
            message="API 라우트가 생성되었습니다. (Immutable: 수정/삭제 불가)",
            data=ApiRouteResponse(
                id=route.ROUTE_ID,
                path=route.API_PATH,
                method=route.HTTP_MTHD,
                name=route.API_NAME,
                description=route.API_DESC,
                tags=route.TAGS,
                is_active=route.USE_YN == 'Y',
                is_deleted=route.DEL_YN == 'Y',
                require_auth=route.AUTH_YN == 'Y',
                allowed_origins=route.ALWD_ORGNS,
                rate_limit=int(route.RATE_LMT) if route.RATE_LMT else 100,
                created_at=route.CREA_DT,
                updated_at=route.UPDT_DT,
                created_by=route.CREA_BY,
                current_version=None,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "VALIDATION_ERROR", "message": str(e)}
        )


@router.patch(
    "/routes/{route_id}/status",
    response_model=ResponseBase[ApiRouteResponse],
    summary="API 라우트 상태 변경",
    description="활성화(USE_YN) 상태만 변경합니다. 데이터 자체는 변경되지 않습니다.",
)
async def change_route_status(
    route_id: str,
    data: StatusChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    API 라우트의 활성화 상태를 변경합니다.
    
    ⚠️ 이 작업은 USE_YN 플래그만 변경하며, 원본 데이터는 보존됩니다.
    """
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    if not route:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "API를 찾을 수 없습니다."}
        )
    
    # 상태 변경
    route.USE_YN = 'Y' if data.is_active else 'N'
    await db.commit()
    await db.refresh(route)
    
    # 감사 로그
    action = "ACTIVATE" if data.is_active else "DEACTIVATE"
    audit = AuditLog(
        ROUTE_ID=route_id,
        ACTION=action,
        DETAILS={"reason": data.reason} if data.reason else None,
        ACTOR="admin",
        ACTOR_IP=get_client_ip(request),
    )
    db.add(audit)
    await db.commit()
    
    current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
    
    return ResponseBase(
        message=f"API 라우트가 {'활성화' if data.is_active else '비활성화'}되었습니다.",
        data=ApiRouteResponse(
            id=route.ROUTE_ID,
            path=route.API_PATH,
            method=route.HTTP_MTHD,
            name=route.API_NAME,
            description=route.API_DESC,
            tags=route.TAGS,
            is_active=route.USE_YN == 'Y',
            is_deleted=route.DEL_YN == 'Y',
            require_auth=route.AUTH_YN == 'Y',
            allowed_origins=route.ALWD_ORGNS,
            rate_limit=int(route.RATE_LMT) if route.RATE_LMT else 100,
            created_at=route.CREA_DT,
            updated_at=route.UPDT_DT,
            created_by=route.CREA_BY,
            current_version=current_version.VERSION_NO if current_version else None,
        )
    )


# ==================== API 버전 관리 (Immutable: 추가만 가능) ====================

@router.get(
    "/routes/{route_id}/versions",
    response_model=ResponseBase[list[ApiVersionListResponse]],
    summary="API 버전 목록 조회",
    description="API 키 없이 조회 가능한 공개 엔드포인트입니다.",
)
async def list_versions(
    route_id: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 API 라우트의 모든 버전을 조회합니다."""
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    if not route:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "API를 찾을 수 없습니다."}
        )
    
    versions = await ApiVersionService.list_versions(db, route_id)
    
    return ResponseBase(
        data=[
            ApiVersionListResponse(
                id=v.VERSION_ID,
                route_id=v.ROUTE_ID,
                version=v.VERSION_NO,
                is_current=v.CRNT_YN == 'Y',
                logic_type=v.LOGIC_TYPE,
                change_note=v.CHG_NOTE,
                created_at=v.CREA_DT,
                created_by=v.CREA_BY,
            )
            for v in versions
        ]
    )


@router.get(
    "/routes/{route_id}/versions/{version_number}",
    response_model=ResponseBase[ApiVersionResponse],
    summary="특정 버전 상세 조회",
    description="API 키 없이 조회 가능한 공개 엔드포인트입니다.",
)
async def get_version(
    route_id: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
):
    """특정 버전의 상세 정보를 조회합니다."""
    version = await ApiVersionService.get_version_by_number(db, route_id, version_number)
    
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "버전을 찾을 수 없습니다."}
        )
    
    return ResponseBase(
        data=ApiVersionResponse(
            id=version.VERSION_ID,
            route_id=version.ROUTE_ID,
            version=version.VERSION_NO,
            is_current=version.CRNT_YN == 'Y',
            request_spec=version.REQ_SPEC,
            logic_type=version.LOGIC_TYPE,
            logic_body=version.LOGIC_BODY,
            logic_config=version.LOGIC_CFG,
            response_spec=version.RESP_SPEC,
            status_codes=version.STATUS_CDS,
            change_note=version.CHG_NOTE,
            sample_params=version.SMPL_PARAMS,
            created_at=version.CREA_DT,
            created_by=version.CREA_BY,
        )
    )


@router.post(
    "/routes/{route_id}/versions",
    response_model=ResponseBase[ApiVersionResponse],
    summary="새 버전 생성 (추가 전용)",
    description="🔒 Immutable: 기존 버전은 수정되지 않고 새 버전이 추가됩니다.",
)
async def create_version(
    route_id: str,
    data: ApiVersionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    새로운 API 버전을 생성합니다.
    
    🔒 Immutable 정책:
    - 기존 버전은 수정/삭제 불가
    - 새 버전이 자동으로 현재 버전이 됨
    - 버전 번호는 자동 증가 (정수)
    """
    # route_id 확인
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    if not route:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "API를 찾을 수 없습니다."}
        )
    
    try:
        # route_id를 data에 설정
        data.route_id = route_id
        
        version = await ApiVersionService.create(
            db=db,
            data=data,
            actor="admin",
            actor_ip=get_client_ip(request),
        )
        
        return ResponseBase(
            message=f"버전 {version.VERSION_NO}이 생성되었습니다. (Immutable: 수정/삭제 불가)",
            data=ApiVersionResponse(
                id=version.VERSION_ID,
                route_id=version.ROUTE_ID,
                version=version.VERSION_NO,
                is_current=version.CRNT_YN == 'Y',
                request_spec=version.REQ_SPEC,
                logic_type=version.LOGIC_TYPE,
                logic_body=version.LOGIC_BODY,
                logic_config=version.LOGIC_CFG,
                response_spec=version.RESP_SPEC,
                status_codes=version.STATUS_CDS,
                change_note=version.CHG_NOTE,
                sample_params=version.SMPL_PARAMS,
                created_at=version.CREA_DT,
                created_by=version.CREA_BY,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "VALIDATION_ERROR", "message": str(e)}
        )


@router.patch(
    "/routes/{route_id}/versions/{version_number}/activate",
    response_model=ResponseBase[ApiVersionResponse],
    summary="현재 버전 설정",
    description="특정 버전을 현재 활성 버전으로 설정합니다. (기존 버전은 보존됨)",
)
async def activate_version(
    route_id: str,
    version_number: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    특정 버전을 현재 활성 버전으로 설정합니다.
    
    ⚠️ 이 작업은 CRNT_YN 플래그만 변경하며, 모든 버전 데이터는 보존됩니다.
    """
    version = await ApiVersionService.set_current_version(
        db=db,
        route_id=route_id,
        version_number=version_number,
        actor="admin",
        actor_ip=get_client_ip(request),
    )
    
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "버전을 찾을 수 없습니다."}
        )
    
    return ResponseBase(
        message=f"버전 {version_number}이 현재 버전으로 설정되었습니다.",
        data=ApiVersionResponse(
            id=version.VERSION_ID,
            route_id=version.ROUTE_ID,
            version=version.VERSION_NO,
            is_current=version.CRNT_YN == 'Y',
            request_spec=version.REQ_SPEC,
            logic_type=version.LOGIC_TYPE,
            logic_body=version.LOGIC_BODY,
            logic_config=version.LOGIC_CFG,
            response_spec=version.RESP_SPEC,
            status_codes=version.STATUS_CDS,
            change_note=version.CHG_NOTE,
            sample_params=version.SMPL_PARAMS,
            created_at=version.CREA_DT,
            created_by=version.CREA_BY,
        )
    )


# ==================== 감사 로그 조회 (공개) ====================

@router.get(
    "/routes/{route_id}/audit-logs",
    summary="API 감사 로그 조회",
    description="특정 API의 변경 이력을 조회합니다. API 키 없이 조회 가능합니다.",
)
async def get_audit_logs(
    route_id: str,
    limit: int = Query(20, ge=1, le=100, description="조회 개수"),
    db: AsyncSession = Depends(get_db),
):
    """특정 API 라우트의 감사 로그를 조회합니다."""
    # 라우트 존재 여부 확인
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    if not route:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "API를 찾을 수 없습니다."}
        )
    
    # 감사 로그 조회
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.ROUTE_ID == route_id)
        .order_by(desc(AuditLog.CREA_DT))
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return ResponseBase(
        data=[
            {
                "id": log.AUDIT_ID,
                "route_id": log.ROUTE_ID,
                "version_id": log.VERSION_ID,
                "action": log.ACTION,
                "details": log.DETAILS,
                "actor": log.ACTOR,
                "actor_ip": log.ACTOR_IP,
                "created_at": log.CREA_DT.isoformat() if log.CREA_DT else None,
            }
            for log in logs
        ]
    )


# ==================== Immutable 정책 안내 ====================

@router.get(
    "/policy",
    summary="API 관리 정책 조회",
    description="Immutable 정책에 대한 설명을 반환합니다.",
)
async def get_policy():
    """API 관리 정책을 반환합니다."""
    return ResponseBase(
        data={
            "policy": "IMMUTABLE",
            "description": "API 정의 데이터는 추가만 가능하며 수정/삭제할 수 없습니다.",
            "rules": [
                {
                    "resource": "APP_API_ROUTE_L",
                    "allowed": ["CREATE", "ACTIVATE", "DEACTIVATE"],
                    "forbidden": ["UPDATE", "DELETE"],
                    "note": "라우트 생성 후 USE_YN 상태만 변경 가능",
                },
                {
                    "resource": "APP_API_VERSION_H",
                    "allowed": ["CREATE", "SET_CURRENT"],
                    "forbidden": ["UPDATE", "DELETE"],
                    "note": "버전 생성 후 CRNT_YN 플래그만 변경 가능",
                },
                {
                    "resource": "APP_API_AUDIT_H",
                    "allowed": ["CREATE"],
                    "forbidden": ["UPDATE", "DELETE"],
                    "note": "감사 로그는 자동 생성되며 변경 불가",
                },
            ],
            "version_numbering": "정수 자동 증가 (1, 2, 3, ...)",
            "benefits": [
                "실수로 인한 API 삭제 방지",
                "모든 변경 이력 보존",
                "언제든 이전 버전으로 복원 가능",
                "감사 추적 용이",
            ],
        }
    )
