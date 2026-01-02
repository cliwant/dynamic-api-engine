"""
APP_API_VERSION_H 테이블에 SMPL_PARAMS 컬럼 추가
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def add_column():
    import aiomysql
    
    conn = await aiomysql.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        db=os.getenv('MYSQL_DB'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
    )
    
    async with conn.cursor() as cursor:
        # 컬럼 존재 여부 확인
        await cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'APP_API_VERSION_H'
            AND COLUMN_NAME = 'SMPL_PARAMS'
        """)
        result = await cursor.fetchone()
        
        if result[0] == 0:
            print("SMPL_PARAMS 컬럼 추가 중...")
            await cursor.execute("""
                ALTER TABLE APP_API_VERSION_H
                ADD COLUMN SMPL_PARAMS JSON NULL
                COMMENT '테스트용 샘플 파라미터 값'
                AFTER CHG_NOTE
            """)
            await conn.commit()
            print("✅ SMPL_PARAMS 컬럼 추가 완료")
        else:
            print("✅ SMPL_PARAMS 컬럼이 이미 존재합니다")
    
    conn.close()


if __name__ == "__main__":
    asyncio.run(add_column())

