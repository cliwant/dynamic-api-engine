"""
스키마 서비스
실제 DB의 테이블 목록, 컬럼 정보, 인덱스, 샘플 데이터를 조회합니다.
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_table_list(db: AsyncSession, schema: Optional[str] = None) -> list[dict]:
    """
    DB의 테이블 목록 조회
    """
    # 현재 스키마의 테이블 목록
    query = text("""
        SELECT 
            TABLE_NAME,
            TABLE_COMMENT,
            TABLE_ROWS,
            CREATE_TIME,
            UPDATE_TIME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "table_name": row[0],
            "comment": row[1] or "",
            "row_count": row[2] or 0,
            "created_at": row[3].isoformat() if row[3] else None,
            "updated_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]


async def get_table_columns(db: AsyncSession, table_name: str) -> list[dict]:
    """
    테이블의 컬럼 정보 조회
    """
    query = text("""
        SELECT 
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_KEY,
            COLUMN_DEFAULT,
            COLUMN_COMMENT,
            ORDINAL_POSITION
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = :table_name
        ORDER BY ORDINAL_POSITION
    """)
    
    result = await db.execute(query, {"table_name": table_name})
    rows = result.fetchall()
    
    return [
        {
            "name": row[0],
            "type": row[1],
            "nullable": row[2] == "YES",
            "key": row[3],  # PRI, UNI, MUL
            "default": str(row[4]) if row[4] is not None else None,
            "comment": row[5] or "",
            "position": row[6],
        }
        for row in rows
    ]


async def get_table_indexes(db: AsyncSession, table_name: str) -> list[dict]:
    """
    테이블의 인덱스 정보 조회
    """
    query = text("""
        SELECT 
            INDEX_NAME,
            COLUMN_NAME,
            NON_UNIQUE,
            SEQ_IN_INDEX,
            INDEX_TYPE
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = :table_name
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """)
    
    result = await db.execute(query, {"table_name": table_name})
    rows = result.fetchall()
    
    # 인덱스별로 그룹화
    indexes = {}
    for row in rows:
        index_name = row[0]
        if index_name not in indexes:
            indexes[index_name] = {
                "name": index_name,
                "columns": [],
                "unique": row[2] == 0,
                "type": row[4],
            }
        indexes[index_name]["columns"].append(row[1])
    
    return list(indexes.values())


# 민감 컬럼 패턴 (마스킹 대상)
SENSITIVE_COLUMN_PATTERNS = [
    r".*password.*",
    r".*passwd.*",
    r".*secret.*",
    r".*token.*",
    r".*api_key.*",
    r".*apikey.*",
    r".*private.*",
    r".*credential.*",
    r".*ssn.*",               # 주민등록번호
    r".*social_security.*",
    r".*credit_card.*",
    r".*card_num.*",
    r".*cvv.*",
    r".*cvc.*",
    r".*pin.*",
    r".*salt.*",
    r".*hash.*",
]


def _is_sensitive_column(column_name: str) -> bool:
    """컬럼명이 민감 정보 패턴에 매칭되는지 확인"""
    import re
    column_lower = column_name.lower()
    for pattern in SENSITIVE_COLUMN_PATTERNS:
        if re.match(pattern, column_lower):
            return True
    return False


def _mask_value(value, column_name: str):
    """
    민감 컬럼 값 마스킹
    
    - 문자열: 앞 2자만 보이고 나머지 *
    - 숫자: ****
    - 기타: [MASKED]
    """
    if value is None:
        return None
    
    if isinstance(value, str):
        if len(value) <= 2:
            return "***"
        return value[:2] + "*" * min(len(value) - 2, 8)
    elif isinstance(value, (int, float)):
        return "****"
    else:
        return "[MASKED]"


async def get_table_sample_data(
    db: AsyncSession, 
    table_name: str, 
    limit: int = 5,
    mask_sensitive: bool = True  # 민감 컬럼 마스킹 활성화
) -> list[dict]:
    """
    테이블의 샘플 데이터 조회 (최대 5행)
    
    ⚠️ 보안: 
    - 테이블명 검증 후 사용
    - 민감 컬럼 자동 마스킹 (기본 활성화)
    """
    # 테이블명 검증 (SQL Injection 방지)
    safe_table_name = table_name.replace("`", "").replace("'", "").replace('"', "")
    
    # 테이블 존재 여부 확인
    check_query = text("""
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
    """)
    result = await db.execute(check_query, {"table_name": safe_table_name})
    if result.scalar() == 0:
        return []
    
    # 샘플 데이터 조회 (동적 쿼리이지만 테이블명이 검증됨)
    try:
        sample_query = text(f"SELECT * FROM `{safe_table_name}` LIMIT :limit")
        result = await db.execute(sample_query, {"limit": limit})
        rows = result.fetchall()
        columns = list(result.keys())
        
        # 민감 컬럼 마스킹 처리
        masked_data = []
        for row in rows:
            row_dict = {}
            for col, val in zip(columns, row):
                serialized_val = _serialize_value(val)
                # 민감 컬럼이면 마스킹
                if mask_sensitive and _is_sensitive_column(col):
                    row_dict[col] = _mask_value(serialized_val, col)
                else:
                    row_dict[col] = serialized_val
            masked_data.append(row_dict)
        
        return masked_data
    except Exception:
        return []


def _serialize_value(val):
    """값 직렬화 (datetime, bytes 등 처리)"""
    from datetime import datetime, date
    from decimal import Decimal
    
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


async def get_table_full_schema(
    db: AsyncSession, 
    table_name: str,
    sample_limit: int = 5
) -> dict:
    """
    테이블의 전체 스키마 정보 (컬럼 + 인덱스 + 샘플 데이터)
    
    Args:
        db: 데이터베이스 세션
        table_name: 테이블명
        sample_limit: 샘플 데이터 최대 개수 (기본 5개)
    """
    columns = await get_table_columns(db, table_name)
    indexes = await get_table_indexes(db, table_name)
    sample_data = await get_table_sample_data(db, table_name, limit=sample_limit)
    
    return {
        "table_name": table_name,
        "columns": columns,
        "indexes": indexes,
        "sample_data": sample_data,
    }

