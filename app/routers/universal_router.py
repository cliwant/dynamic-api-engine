"""
유니버설 라우터 (동적 API 엔진)

이 라우터는 모든 동적 API 요청을 처리합니다.
DB에 정의된 API 설정을 읽어와 동적으로 실행합니다.

⚠️ 이 파일이 시스템의 핵심입니다.
"""
from typing import Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.api_route_service import ApiRouteService
from app.services.api_version_service import ApiVersionService
from app.services.validator_service import ValidatorService, ValidationError
from app.services.executor_service import ExecutorService, ExecutorError

router = APIRouter(prefix="/api", tags=["Dynamic API"])


async def get_request_params(request: Request) -> dict[str, Any]:
    """
    요청에서 파라미터 추출
    
    - GET: Query Parameters
    - POST/PUT/PATCH: JSON Body
    - DELETE: Query Parameters
    """
    method = request.method.upper()
    
    if method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body
            return {"_body": body}
        except Exception:
            return {}
    else:
        return dict(request.query_params)


def format_response(
    execution_result: dict[str, Any],
    response_spec: Optional[dict[str, Any]],
    status_codes: Optional[dict[str, int]],
) -> tuple[dict[str, Any], int]:
    """
    실행 결과를 response_spec에 따라 포맷팅
    
    response_spec 예시:
    {
        "data": "$result",
        "count": "$result_count",
        "success": true
    }
    
    특수 변수:
    - $result: 실행 결과 데이터
    - $result_count: 결과 개수
    """
    result = execution_result.get("result")
    result_count = execution_result.get("result_count", 0)
    
    # response_spec이 없으면 기본 형식으로 반환
    if not response_spec:
        return {
            "success": True,
            "data": result,
            "count": result_count,
        }, 200
    
    # response_spec에 따라 포맷팅
    formatted = {}
    for key, value in response_spec.items():
        if isinstance(value, str):
            if value == "$result":
                formatted[key] = result
            elif value == "$result_count":
                formatted[key] = result_count
            elif value.startswith("$result.") and isinstance(result, dict):
                # $result.field 형식 지원
                field = value[8:]
                formatted[key] = result.get(field)
            else:
                formatted[key] = value
        else:
            formatted[key] = value
    
    # 상태 코드 결정
    status_code = 200
    if status_codes:
        if result_count > 0:
            status_code = status_codes.get("success", 200)
        else:
            status_code = status_codes.get("not_found", 200)
    
    return formatted, status_code


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    summary="동적 API 엔드포인트",
    description="DB에 정의된 API를 동적으로 실행합니다.",
)
async def universal_endpoint(
    request: Request,
    path: str,
    db: AsyncSession = Depends(get_db),
    _version: Optional[int] = Query(None, description="특정 버전 지정 (기본: 최신 버전)"),
):
    """
    유니버설 API 엔드포인트
    
    모든 동적 API 요청을 처리합니다.
    1. DB에서 해당 path + method의 API 정의를 조회
    2. 최신 버전의 설정을 로드
    3. 입력 파라미터 검증
    4. 로직 실행
    5. 응답 포맷팅 후 반환
    """
    method = request.method.upper()
    
    # 1. API 라우트 조회
    route = await ApiRouteService.get_by_path_method(db, path, method)
    
    if not route:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "API_NOT_FOUND",
                "message": f"API를 찾을 수 없습니다: {method} /api/{path}",
            }
        )
    
    # 비활성화된 API 체크
    if route.USE_YN != 'Y':
        raise HTTPException(
            status_code=503,
            detail={
                "error": "API_DISABLED",
                "message": "이 API는 현재 비활성화되어 있습니다.",
            }
        )
    
    # 2. API 버전 조회
    if _version:
        version = await ApiVersionService.get_version_by_number(db, route.ROUTE_ID, _version)
        if not version:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "VERSION_NOT_FOUND",
                    "message": f"버전을 찾을 수 없습니다: v{_version}",
                }
            )
    else:
        version = await ApiVersionService.get_current_version(db, route.ROUTE_ID)
        if not version:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "NO_VERSION",
                    "message": "이 API에 정의된 버전이 없습니다.",
                }
            )
    
    # 3. 요청 파라미터 추출
    params = await get_request_params(request)
    
    # 4. 파라미터 검증
    try:
        validated_params = ValidatorService.validate(params, version.REQ_SPEC)
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "VALIDATION_ERROR",
                "message": e.message,
                "field": e.field,
            }
        )
    
    # 5. 로직 실행
    try:
        execution_result = await ExecutorService.execute(
            db=db,
            logic_type=version.LOGIC_TYPE,
            logic_body=version.LOGIC_BODY,
            params=validated_params,
            config=version.LOGIC_CFG,
        )
    except ExecutorError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": e.error_type,
                "message": e.message,
            }
        )
    
    # 6. 응답 포맷팅
    response_data, status_code = format_response(
        execution_result,
        version.RESP_SPEC,
        version.STATUS_CDS,
    )
    
    return JSONResponse(content=response_data, status_code=status_code)
