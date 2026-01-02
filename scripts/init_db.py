"""
데이터베이스 초기화 스크립트

이 스크립트는 데이터베이스 테이블을 생성하고 초기 데이터를 삽입합니다.
"""
import asyncio
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, async_session_maker
from app.models import ApiRoute, ApiVersion, AuditLog


async def create_tables():
    """테이블 생성"""
    print("📦 테이블 생성 중...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 테이블 생성 완료")


async def create_sample_api():
    """샘플 API 생성"""
    print("📝 샘플 API 생성 중...")
    
    async with async_session_maker() as db:
        # 샘플 라우트 1: 헬로 월드
        route1 = ApiRoute(
            path="hello",
            method="GET",
            name="Hello World API",
            description="간단한 인사 API입니다.",
            tags="sample,hello",
            is_active=True,
            created_by="system",
        )
        db.add(route1)
        await db.flush()
        
        # 버전 1
        version1 = ApiVersion(
            route_id=route1.id,
            version=1,
            is_current=True,
            request_spec={
                "name": {
                    "type": "string",
                    "required": False,
                    "default": "World",
                    "description": "인사할 이름"
                }
            },
            logic_type="STATIC_RESPONSE",
            logic_body='{"message": "Hello, $params.name!", "timestamp": "2024-01-01T00:00:00"}',
            response_spec={
                "success": True,
                "data": "$result"
            },
            change_note="초기 버전",
            created_by="system",
        )
        db.add(version1)
        
        # 샘플 라우트 2: 에코 API
        route2 = ApiRoute(
            path="echo",
            method="POST",
            name="Echo API",
            description="입력받은 데이터를 그대로 반환합니다.",
            tags="sample,echo",
            is_active=True,
            created_by="system",
        )
        db.add(route2)
        await db.flush()
        
        # 버전 1
        version2 = ApiVersion(
            route_id=route2.id,
            version=1,
            is_current=True,
            request_spec={
                "message": {
                    "type": "string",
                    "required": True,
                    "min_length": 1,
                    "max_length": 1000,
                    "description": "에코할 메시지"
                }
            },
            logic_type="PYTHON_EXPR",
            logic_body='{"echo": params["message"], "length": len(params["message"])}',
            response_spec={
                "success": True,
                "data": "$result"
            },
            change_note="초기 버전",
            created_by="system",
        )
        db.add(version2)
        
        await db.commit()
    
    print("✅ 샘플 API 생성 완료")
    print("   - GET /api/hello?name=World")
    print("   - POST /api/echo {\"message\": \"Hello\"}")


async def main():
    """메인 함수"""
    print("=" * 50)
    print("🚀 Prompt API Engine - 데이터베이스 초기화")
    print("=" * 50)
    
    await create_tables()
    
    # 샘플 데이터 생성 여부 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--with-sample":
        await create_sample_api()
    
    print("=" * 50)
    print("✅ 초기화 완료!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

