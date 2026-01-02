"""
스키마 라우터
DB 테이블 스키마 조회, API 테스트, LLM 기반 API 생성
"""
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import ResponseBase
from app.services import schema_service
from app.services.llm_service import (
    get_supported_models,
    get_auth_methods,
    get_providers,
    check_llm_availability,
    generate_api_spec,
    ApiGenerationRequest,
    TableSchema,
    LLMConfig,
    GeneratedApiSpec,
)

router = APIRouter(prefix="/schema", tags=["Schema & LLM"])


# ==================== 테이블 스키마 조회 ====================

@router.get(
    "/tables",
    summary="테이블 목록 조회",
    description="현재 DB의 모든 테이블 목록을 조회합니다.",
)
async def list_tables(
    db: AsyncSession = Depends(get_db),
):
    """DB 테이블 목록 조회"""
    tables = await schema_service.get_table_list(db)
    return ResponseBase(data=tables)


@router.get(
    "/tables/{table_name}",
    summary="테이블 상세 스키마 조회",
    description="특정 테이블의 컬럼, 인덱스, 샘플 데이터를 조회합니다.",
)
async def get_table_schema(
    table_name: str,
    sample_limit: int = Query(5, ge=1, le=20, description="샘플 데이터 행 수"),
    db: AsyncSession = Depends(get_db),
):
    """테이블 상세 스키마 조회 (컬럼, 인덱스, 샘플 데이터)"""
    columns = await schema_service.get_table_columns(db, table_name)
    if not columns:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"테이블 '{table_name}'을 찾을 수 없습니다."}
        )
    
    indexes = await schema_service.get_table_indexes(db, table_name)
    sample_data = await schema_service.get_table_sample_data(db, table_name, sample_limit)
    
    # 각 컬럼별 샘플 값 추출
    column_samples = {}
    for col in columns:
        col_name = col["name"]
        column_samples[col_name] = [row.get(col_name) for row in sample_data if row.get(col_name) is not None][:5]
    
    return ResponseBase(data={
        "table_name": table_name,
        "columns": columns,
        "indexes": indexes,
        "sample_data": sample_data,
        "column_samples": column_samples,
    })


@router.get(
    "/tables/{table_name}/columns",
    summary="테이블 컬럼 조회",
)
async def get_table_columns(
    table_name: str,
    db: AsyncSession = Depends(get_db),
):
    """테이블 컬럼 정보 조회"""
    columns = await schema_service.get_table_columns(db, table_name)
    return ResponseBase(data=columns)


@router.get(
    "/tables/{table_name}/indexes",
    summary="테이블 인덱스 조회",
)
async def get_table_indexes(
    table_name: str,
    db: AsyncSession = Depends(get_db),
):
    """테이블 인덱스 정보 조회"""
    indexes = await schema_service.get_table_indexes(db, table_name)
    return ResponseBase(data=indexes)


@router.get(
    "/tables/{table_name}/sample",
    summary="테이블 샘플 데이터 조회",
)
async def get_table_sample(
    table_name: str,
    limit: int = Query(5, ge=1, le=20, description="조회 행 수"),
    db: AsyncSession = Depends(get_db),
):
    """테이블 샘플 데이터 조회"""
    sample = await schema_service.get_table_sample_data(db, table_name, limit)
    return ResponseBase(data=sample)


# ==================== SQL 테스트 ====================

class TestSqlRequest(BaseModel):
    """SQL 테스트 요청"""
    logic_type: str = "SQL"
    logic_body: str
    params: dict[str, Any] = {}


@router.post(
    "/test-sql",
    summary="SQL 테스트 실행",
    description="API 생성 전 SQL 쿼리가 정상 동작하는지 테스트합니다.",
)
async def test_sql(
    request: TestSqlRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SQL 테스트 실행
    
    - 실제 DB에서 쿼리 실행
    - 결과 및 실행 시간 반환
    - 오류 발생 시 상세 에러 메시지 반환
    """
    import time
    from datetime import datetime, date
    from decimal import Decimal
    
    # 위험한 쿼리 차단
    dangerous_patterns = ["DROP ", "TRUNCATE ", "DELETE ", "ALTER ", "CREATE ", "INSERT ", "UPDATE "]
    logic_upper = request.logic_body.upper()
    for pattern in dangerous_patterns:
        if pattern in logic_upper:
            raise HTTPException(
                status_code=400,
                detail={"error": "FORBIDDEN_QUERY", "message": f"테스트에서는 {pattern.strip()} 쿼리를 실행할 수 없습니다."}
            )
    
    start_time = time.time()
    
    try:
        # SQL 실행
        result = await db.execute(text(request.logic_body), request.params)
        rows = result.fetchall()
        columns = list(result.keys())
        
        # 데이터 직렬화
        def serialize_value(val):
            if val is None:
                return None
            if isinstance(val, (datetime, date)):
                return val.isoformat()
            if isinstance(val, Decimal):
                return float(val)
            if isinstance(val, bytes):
                try:
                    return val.decode("utf-8")
                except:
                    return f"<bytes: {len(val)} bytes>"
            return val
        
        data = [
            {col: serialize_value(val) for col, val in zip(columns, row)}
            for row in rows
        ]
        
        execution_time = round((time.time() - start_time) * 1000, 2)
        
        return ResponseBase(
            message="테스트 성공",
            data={
                "success": True,
                "columns": columns,
                "data": data,
                "row_count": len(data),
                "execution_time_ms": execution_time,
            }
        )
        
    except Exception as e:
        execution_time = round((time.time() - start_time) * 1000, 2)
        return ResponseBase(
            message="테스트 실패",
            data={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time_ms": execution_time,
            }
        )


class GetSampleValuesRequest(BaseModel):
    """샘플 값 조회 요청"""
    table_name: str
    columns: list[str]
    count: int = 5


@router.post(
    "/sample-values",
    summary="파라미터 샘플 값 조회",
    description="특정 테이블의 컬럼에서 실제 데이터 샘플을 조회합니다.",
)
async def get_sample_values(
    request: GetSampleValuesRequest,
    db: AsyncSession = Depends(get_db),
):
    """파라미터에 사용할 수 있는 샘플 값 조회"""
    from datetime import datetime, date
    from decimal import Decimal
    
    # 테이블명 검증
    safe_table = request.table_name.replace("`", "").replace("'", "").replace('"', "")
    
    samples = {}
    for col in request.columns:
        safe_col = col.replace("`", "").replace("'", "").replace('"', "")
        try:
            query = text(f"SELECT DISTINCT `{safe_col}` FROM `{safe_table}` WHERE `{safe_col}` IS NOT NULL LIMIT :limit")
            result = await db.execute(query, {"limit": request.count})
            rows = result.fetchall()
            
            values = []
            for row in rows:
                val = row[0]
                if isinstance(val, (datetime, date)):
                    val = val.isoformat()
                elif isinstance(val, Decimal):
                    val = float(val)
                elif isinstance(val, bytes):
                    continue
                values.append(val)
            
            samples[col] = values
        except Exception as e:
            samples[col] = {"error": str(e)}
    
    return ResponseBase(data=samples)


# ==================== LLM 관련 ====================

@router.get(
    "/llm/models",
    summary="지원 LLM 모델 목록",
    description="사용 가능한 LLM 모델과 인증 방식 정보를 반환합니다.",
)
async def list_llm_models():
    """지원되는 LLM 모델 목록 및 인증 정보"""
    return ResponseBase(
        data={
            "models": get_supported_models(),
            "providers": get_providers(),
            "auth_methods": get_auth_methods(),
            "availability": check_llm_availability(),
        }
    )


@router.get(
    "/llm/status",
    summary="LLM 사용 가능 여부",
)
async def check_llm_status():
    """LLM 사용 가능 여부 확인"""
    return ResponseBase(data=check_llm_availability())


class GenerateApiRequest(BaseModel):
    """API 생성 요청 (확장)"""
    user_intent: str
    table_names: list[str]
    method: str = "GET"
    # LLM 모델 설정
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    # 인증
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    vertex_credentials: Optional[str] = None


@router.post(
    "/llm/generate-api",
    summary="LLM으로 API 생성",
    description="LLM을 사용하여 사용자 의도에 맞는 API 정의를 자동 생성합니다.",
)
async def generate_api_with_llm(
    request: GenerateApiRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    LLM 기반 API 자동 생성
    
    1. 선택한 테이블들의 스키마 조회
    2. 사용자 의도와 함께 LLM에 전달
    3. API 정의 JSON 생성
    """
    # 테이블 스키마 조회
    tables = []
    for table_name in request.table_names:
        columns = await schema_service.get_table_columns(db, table_name)
        if not columns:
            continue
        indexes = await schema_service.get_table_indexes(db, table_name)
        sample_data = await schema_service.get_table_sample_data(db, table_name, 5)
        
        tables.append(TableSchema(
            table_name=table_name,
            columns=columns,
            indexes=indexes,
            sample_data=sample_data,
        ))
    
    if not tables:
        raise HTTPException(
            status_code=400,
            detail={"error": "VALIDATION_ERROR", "message": "유효한 테이블을 선택해주세요."}
        )
    
    # LLM 호출
    try:
        api_request = ApiGenerationRequest(
            user_intent=request.user_intent,
            tables=tables,
            method=request.method,
        )
        
        config = LLMConfig(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            api_key=request.api_key,
            api_base=request.api_base,
            vertex_credentials=request.vertex_credentials,
        )
        
        generated_spec = await generate_api_spec(api_request, config)
        
        return ResponseBase(
            message="API 스펙이 생성되었습니다.",
            data=generated_spec.model_dump(),
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "SERVICE_UNAVAILABLE", "message": str(e)}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "PARSING_ERROR", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "LLM_ERROR", "message": str(e)}
        )
