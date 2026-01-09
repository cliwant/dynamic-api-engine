"""
관리자 라우터
API 정의 관리를 위한 엔드포인트

🔒 Immutable 정책:
- API Route와 Version은 추가만 가능 (수정/삭제 불가)
- 상태 변경(활성화/비활성화)과 현재 버전 설정만 허용
- 모든 변경 이력은 감사 로그에 기록됨
"""
import json
from typing import Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text

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
from app.models.api_route import ApiRoute
from app.models.api_version import ApiVersion

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


# ==================== API 카테고리/그룹 관리 ====================

@router.get(
    "/categories",
    summary="API 카테고리 목록 조회",
    description="모든 API 카테고리와 해당 카테고리의 API 수를 반환합니다.",
)
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    """API 카테고리 목록을 조회합니다."""
    # 태그 기반 카테고리 추출 (태그의 첫 번째 부분을 카테고리로 사용)
    result = await db.execute(
        select(ApiRoute.TAGS)
        .where(ApiRoute.DEL_YN == 'N')
        .where(ApiRoute.TAGS.isnot(None))
    )
    tags_list = result.scalars().all()
    
    # 카테고리별 API 수 집계
    categories = {}
    for tags in tags_list:
        if tags:
            primary_tag = tags.split(',')[0].strip()
            categories[primary_tag] = categories.get(primary_tag, 0) + 1
    
    # 전체 API 수
    total_result = await db.execute(
        select(func.count(ApiRoute.ROUTE_ID))
        .where(ApiRoute.DEL_YN == 'N')
    )
    total_count = total_result.scalar() or 0
    
    # 카테고리 없는 API 수
    uncategorized_result = await db.execute(
        select(func.count(ApiRoute.ROUTE_ID))
        .where(ApiRoute.DEL_YN == 'N')
        .where(ApiRoute.TAGS.is_(None) | (ApiRoute.TAGS == ''))
    )
    uncategorized_count = uncategorized_result.scalar() or 0
    
    return ResponseBase(
        data={
            "total_apis": total_count,
            "categories": [
                {"name": name, "count": count}
                for name, count in sorted(categories.items())
            ],
            "uncategorized_count": uncategorized_count,
        }
    )


@router.get(
    "/categories/{category_name}/apis",
    summary="카테고리별 API 목록",
    description="특정 카테고리에 속한 API 목록을 반환합니다.",
)
async def list_apis_by_category(
    category_name: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 카테고리의 API 목록을 조회합니다."""
    result = await db.execute(
        select(ApiRoute)
        .where(ApiRoute.DEL_YN == 'N')
        .where(ApiRoute.TAGS.like(f"{category_name}%"))
    )
    routes = result.scalars().all()
    
    api_list = []
    for route in routes:
        current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
        api_list.append({
            "id": route.ROUTE_ID,
            "path": route.API_PATH,
            "method": route.HTTP_MTHD,
            "name": route.API_NAME,
            "tags": route.TAGS,
            "is_active": route.USE_YN == 'Y',
            "current_version": current_version.VERSION_NO if current_version else None,
        })
    
    return ResponseBase(
        data={
            "category": category_name,
            "count": len(api_list),
            "apis": api_list,
        }
    )


# ==================== API 문서 자동 생성 (OpenAPI) ====================

@router.get(
    "/openapi-spec",
    summary="동적 OpenAPI 스펙 생성",
    description="등록된 모든 API에 대한 OpenAPI 3.0 스펙을 자동 생성합니다.",
)
async def generate_openapi_spec(
    db: AsyncSession = Depends(get_db),
):
    """동적 API에 대한 OpenAPI 스펙을 생성합니다."""
    # 활성화된 모든 라우트 조회
    result = await db.execute(
        select(ApiRoute)
        .where(ApiRoute.DEL_YN == 'N')
        .where(ApiRoute.USE_YN == 'Y')
    )
    routes = result.scalars().all()
    
    paths = {}
    tags_set = set()
    
    for route in routes:
        current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
        if not current_version:
            continue
        
        path = f"/api/{route.API_PATH}"
        method = route.HTTP_MTHD.lower()
        
        # 태그 추출
        api_tags = [route.TAGS.split(',')[0].strip()] if route.TAGS else ["default"]
        tags_set.update(api_tags)
        
        # 파라미터 정의
        parameters = []
        request_body = None
        
        if current_version.REQ_SPEC:
            req_spec = current_version.REQ_SPEC
            if isinstance(req_spec, str):
                req_spec = json.loads(req_spec)
            
            for param_name, param_info in req_spec.items():
                if method in ['get', 'delete']:
                    parameters.append({
                        "name": param_name,
                        "in": "query",
                        "required": param_info.get("required", False),
                        "schema": {
                            "type": param_info.get("type", "string"),
                            "default": param_info.get("default"),
                        },
                        "description": param_info.get("description", ""),
                    })
                else:
                    if not request_body:
                        request_body = {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {},
                                        "required": [],
                                    }
                                }
                            }
                        }
                    props = request_body["content"]["application/json"]["schema"]["properties"]
                    props[param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", ""),
                    }
                    if param_info.get("required"):
                        request_body["content"]["application/json"]["schema"]["required"].append(param_name)
        
        # 경로 엔트리 생성
        if path not in paths:
            paths[path] = {}
        
        operation = {
            "tags": api_tags,
            "summary": route.API_NAME or route.API_PATH,
            "description": route.API_DESC or "",
            "operationId": f"{method}_{route.ROUTE_ID}",
            "responses": {
                "200": {
                    "description": "성공",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                },
                "400": {"description": "잘못된 요청"},
                "500": {"description": "서버 오류"},
            },
        }
        
        if parameters:
            operation["parameters"] = parameters
        if request_body:
            operation["requestBody"] = request_body
        
        paths[path][method] = operation
    
    # OpenAPI 스펙 조립
    openapi_spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Dynamic API Engine",
            "description": "MySQL 테이블 기반 동적 API 엔진 - 자동 생성된 API 문서",
            "version": "1.7.0",
            "contact": {
                "name": "API Support",
            },
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "Local Development Server",
            }
        ],
        "tags": [{"name": tag, "description": f"{tag} 관련 API"} for tag in sorted(tags_set)],
        "paths": paths,
    }
    
    return JSONResponse(content=openapi_spec)


@router.get(
    "/routes/{route_id}/openapi",
    summary="개별 API OpenAPI 스펙",
    description="특정 API의 OpenAPI 스펙을 반환합니다.",
)
async def get_route_openapi(
    route_id: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 API의 OpenAPI 스펙을 반환합니다."""
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    if not route:
        raise HTTPException(status_code=404, detail="API를 찾을 수 없습니다.")
    
    current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
    if not current_version:
        raise HTTPException(status_code=404, detail="활성화된 버전이 없습니다.")
    
    return ResponseBase(
        data={
            "path": f"/api/{route.API_PATH}",
            "method": route.HTTP_MTHD,
            "summary": route.API_NAME,
            "description": route.API_DESC,
            "tags": route.TAGS.split(',') if route.TAGS else [],
            "request_spec": current_version.REQ_SPEC,
            "response_spec": current_version.RESP_SPEC,
            "logic_type": current_version.LOGIC_TYPE,
        }
    )


# ==================== 사용량 분석/대시보드 ====================

@router.get(
    "/stats/overview",
    summary="API 통계 개요",
    description="전체 API 통계 (총 개수, 활성/비활성, 카테고리별 등)를 반환합니다.",
)
async def get_stats_overview(
    db: AsyncSession = Depends(get_db),
):
    """API 통계 개요를 반환합니다."""
    # 총 API 수
    total_result = await db.execute(
        select(func.count(ApiRoute.ROUTE_ID))
        .where(ApiRoute.DEL_YN == 'N')
    )
    total_count = total_result.scalar() or 0
    
    # 활성화된 API 수
    active_result = await db.execute(
        select(func.count(ApiRoute.ROUTE_ID))
        .where(ApiRoute.DEL_YN == 'N')
        .where(ApiRoute.USE_YN == 'Y')
    )
    active_count = active_result.scalar() or 0
    
    # HTTP 메서드별 API 수
    method_result = await db.execute(
        select(ApiRoute.HTTP_MTHD, func.count(ApiRoute.ROUTE_ID))
        .where(ApiRoute.DEL_YN == 'N')
        .group_by(ApiRoute.HTTP_MTHD)
    )
    methods = {row[0]: row[1] for row in method_result.fetchall()}
    
    # 로직 타입별 API 수
    logic_result = await db.execute(
        select(ApiVersion.LOGIC_TYPE, func.count(ApiVersion.VERSION_ID))
        .where(ApiVersion.CRNT_YN == 'Y')
        .group_by(ApiVersion.LOGIC_TYPE)
    )
    logic_types = {row[0]: row[1] for row in logic_result.fetchall()}
    
    # 최근 생성된 API (7일)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count(ApiRoute.ROUTE_ID))
        .where(ApiRoute.DEL_YN == 'N')
        .where(ApiRoute.CREA_DT >= week_ago)
    )
    recent_count = recent_result.scalar() or 0
    
    # 버전 통계
    version_result = await db.execute(
        select(func.count(ApiVersion.VERSION_ID))
    )
    total_versions = version_result.scalar() or 0
    
    avg_version_result = await db.execute(
        select(func.avg(func.count(ApiVersion.VERSION_ID)))
        .group_by(ApiVersion.ROUTE_ID)
    )
    
    return ResponseBase(
        data={
            "total_apis": total_count,
            "active_apis": active_count,
            "inactive_apis": total_count - active_count,
            "total_versions": total_versions,
            "recent_apis_7d": recent_count,
            "by_method": methods,
            "by_logic_type": logic_types,
        }
    )


@router.get(
    "/stats/audit-summary",
    summary="감사 로그 요약",
    description="최근 감사 로그 통계를 반환합니다.",
)
async def get_audit_summary(
    days: int = Query(7, ge=1, le=30, description="조회할 일수"),
    db: AsyncSession = Depends(get_db),
):
    """감사 로그 요약을 반환합니다."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 액션별 집계
    action_result = await db.execute(
        select(AuditLog.ACTION, func.count(AuditLog.AUDIT_ID))
        .where(AuditLog.CREA_DT >= start_date)
        .group_by(AuditLog.ACTION)
    )
    actions = {row[0]: row[1] for row in action_result.fetchall()}
    
    # 일별 활동 집계
    daily_result = await db.execute(
        text("""
            SELECT DATE(CREA_DT) as date, COUNT(*) as count
            FROM APP_API_AUDIT_H
            WHERE CREA_DT >= :start_date
            GROUP BY DATE(CREA_DT)
            ORDER BY date DESC
        """),
        {"start_date": start_date}
    )
    daily_activity = [{"date": str(row[0]), "count": row[1]} for row in daily_result.fetchall()]
    
    # 최근 활동
    recent_result = await db.execute(
        select(AuditLog)
        .order_by(desc(AuditLog.CREA_DT))
        .limit(10)
    )
    recent_logs = recent_result.scalars().all()
    
    return ResponseBase(
        data={
            "period_days": days,
            "by_action": actions,
            "daily_activity": daily_activity,
            "recent_activity": [
                {
                    "id": log.AUDIT_ID,
                    "action": log.ACTION,
                    "route_id": log.ROUTE_ID,
                    "actor": log.ACTOR,
                    "created_at": log.CREA_DT.isoformat() if log.CREA_DT else None,
                }
                for log in recent_logs
            ],
        }
    )


# ==================== API Import/Export ====================

class ImportRequest(BaseModel):
    """API 가져오기 요청"""
    apis: list[dict[str, Any]] = Field(..., description="가져올 API 정의 목록")
    overwrite: bool = Field(False, description="기존 API 덮어쓰기 여부")


@router.get(
    "/export",
    summary="전체 API 내보내기",
    description="모든 API 정의를 JSON으로 내보냅니다.",
)
async def export_apis(
    include_inactive: bool = Query(False, description="비활성화된 API 포함"),
    db: AsyncSession = Depends(get_db),
):
    """모든 API를 JSON으로 내보냅니다."""
    query = select(ApiRoute).where(ApiRoute.DEL_YN == 'N')
    if not include_inactive:
        query = query.where(ApiRoute.USE_YN == 'Y')
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    export_data = {
        "version": "1.7.0",
        "exported_at": datetime.utcnow().isoformat(),
        "total_apis": len(routes),
        "apis": [],
    }
    
    for route in routes:
        # 현재 버전 조회
        current_version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
        
        # 모든 버전 조회
        versions_result = await db.execute(
            select(ApiVersion)
            .where(ApiVersion.ROUTE_ID == route.ROUTE_ID)
            .order_by(ApiVersion.VERSION_NO)
        )
        versions = versions_result.scalars().all()
        
        api_data = {
            "route": {
                "id": route.ROUTE_ID,
                "path": route.API_PATH,
                "method": route.HTTP_MTHD,
                "name": route.API_NAME,
                "description": route.API_DESC,
                "tags": route.TAGS,
                "is_active": route.USE_YN == 'Y',
                "require_auth": route.AUTH_YN == 'Y',
                "rate_limit": route.RATE_LMT,
                "created_at": route.CREA_DT.isoformat() if route.CREA_DT else None,
            },
            "versions": [
                {
                    "version": v.VERSION_NO,
                    "is_current": v.CRNT_YN == 'Y',
                    "request_spec": v.REQ_SPEC,
                    "logic_type": v.LOGIC_TYPE,
                    "logic_body": v.LOGIC_BODY,
                    "logic_config": v.LOGIC_CFG,
                    "response_spec": v.RESP_SPEC,
                    "sample_params": v.SMPL_PARAMS,
                    "change_note": v.CHG_NOTE,
                    "created_at": v.CREA_DT.isoformat() if v.CREA_DT else None,
                }
                for v in versions
            ],
        }
        export_data["apis"].append(api_data)
    
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=api-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        }
    )


@router.get(
    "/export/{route_id}",
    summary="개별 API 내보내기",
    description="특정 API 정의를 JSON으로 내보냅니다.",
)
async def export_single_api(
    route_id: str,
    db: AsyncSession = Depends(get_db),
):
    """특정 API를 JSON으로 내보냅니다."""
    route = await ApiRouteService.get_by_id(db, route_id, include_deleted=False)
    if not route:
        raise HTTPException(status_code=404, detail="API를 찾을 수 없습니다.")
    
    # 모든 버전 조회
    versions_result = await db.execute(
        select(ApiVersion)
        .where(ApiVersion.ROUTE_ID == route.ROUTE_ID)
        .order_by(ApiVersion.VERSION_NO)
    )
    versions = versions_result.scalars().all()
    
    export_data = {
        "version": "1.7.0",
        "exported_at": datetime.utcnow().isoformat(),
        "route": {
            "id": route.ROUTE_ID,
            "path": route.API_PATH,
            "method": route.HTTP_MTHD,
            "name": route.API_NAME,
            "description": route.API_DESC,
            "tags": route.TAGS,
            "is_active": route.USE_YN == 'Y',
            "require_auth": route.AUTH_YN == 'Y',
            "rate_limit": route.RATE_LMT,
        },
        "versions": [
            {
                "version": v.VERSION_NO,
                "is_current": v.CRNT_YN == 'Y',
                "request_spec": v.REQ_SPEC,
                "logic_type": v.LOGIC_TYPE,
                "logic_body": v.LOGIC_BODY,
                "logic_config": v.LOGIC_CFG,
                "response_spec": v.RESP_SPEC,
                "sample_params": v.SMPL_PARAMS,
                "change_note": v.CHG_NOTE,
            }
            for v in versions
        ],
    }
    
    return JSONResponse(content=export_data)


@router.post(
    "/import",
    summary="API 가져오기",
    description="JSON 파일에서 API 정의를 가져옵니다.",
)
async def import_apis(
    data: ImportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """JSON에서 API를 가져옵니다."""
    imported = []
    skipped = []
    errors = []
    
    for api_data in data.apis:
        try:
            route_data = api_data.get("route", {})
            versions_data = api_data.get("versions", [])
            
            # 기존 라우트 확인
            existing = await ApiRouteService.get_by_path_method(
                db, route_data.get("path"), route_data.get("method")
            )
            
            if existing and not data.overwrite:
                skipped.append({
                    "path": route_data.get("path"),
                    "method": route_data.get("method"),
                    "reason": "이미 존재함",
                })
                continue
            
            # 새 라우트 생성 (Immutable이므로 기존 라우트가 있어도 새로 생성)
            new_route = await ApiRouteService.create(
                db=db,
                data=ApiRouteCreate(
                    path=route_data.get("path"),
                    method=route_data.get("method"),
                    name=route_data.get("name"),
                    description=route_data.get("description"),
                    tags=route_data.get("tags"),
                    require_auth=route_data.get("require_auth", False),
                    rate_limit=int(route_data.get("rate_limit", 100)),
                ),
                actor="import",
                actor_ip=get_client_ip(request),
            )
            
            # 버전 생성
            for v_data in versions_data:
                await ApiVersionService.create(
                    db=db,
                    data=ApiVersionCreate(
                        route_id=new_route.ROUTE_ID,
                        request_spec=v_data.get("request_spec"),
                        logic_type=v_data.get("logic_type", "SQL"),
                        logic_body=v_data.get("logic_body"),
                        logic_config=v_data.get("logic_config"),
                        response_spec=v_data.get("response_spec"),
                        sample_params=v_data.get("sample_params"),
                        change_note=v_data.get("change_note", "가져오기로 생성"),
                    ),
                    actor="import",
                    actor_ip=get_client_ip(request),
                )
            
            imported.append({
                "id": new_route.ROUTE_ID,
                "path": new_route.API_PATH,
                "method": new_route.HTTP_MTHD,
                "versions": len(versions_data),
            })
            
        except Exception as e:
            errors.append({
                "path": api_data.get("route", {}).get("path"),
                "error": str(e),
            })
    
    return ResponseBase(
        message=f"가져오기 완료: {len(imported)}개 성공, {len(skipped)}개 건너뜀, {len(errors)}개 오류",
        data={
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }
    )
