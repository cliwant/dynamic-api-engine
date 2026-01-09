"""
APP_API_ROUTE_L 테이블에 CATEGORY 컬럼 추가

Usage:
    python scripts/add_category_column.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text
from app.core.database import get_db, engine


async def add_category_column():
    """CATEGORY 컬럼을 APP_API_ROUTE_L 테이블에 추가"""
    async with engine.begin() as conn:
        try:
            # 컬럼 존재 여부 확인
            result = await conn.execute(text("""
                SELECT COLUMN_NAME 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'APP_API_ROUTE_L' 
                AND COLUMN_NAME = 'CATEGORY'
            """))
            existing = result.fetchone()
            
            if existing:
                print("✅ CATEGORY 컬럼이 이미 존재합니다.")
                return
            
            # 컬럼 추가
            await conn.execute(text("""
                ALTER TABLE APP_API_ROUTE_L 
                ADD COLUMN CATEGORY VARCHAR(100) NULL 
                COMMENT 'API 카테고리'
                AFTER API_DESC
            """))
            print("✅ CATEGORY 컬럼이 추가되었습니다.")
            
        except Exception as e:
            print(f"❌ 에러: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(add_category_column())
