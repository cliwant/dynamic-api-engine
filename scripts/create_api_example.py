"""
API 생성 예제 스크립트

이 스크립트는 코드 없이 DB에 직접 API를 추가하는 예제입니다.
실제 운영에서는 Admin API를 사용하거나 직접 MySQL에 INSERT하면 됩니다.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models import ApiRoute, ApiVersion
from app.services.audit_service import AuditService


async def create_products_api():
    """
    상품 목록 API 생성 예제
    
    이 예제는 다음과 같은 API를 생성합니다:
    GET /api/products?min_price=1000&category=electronics
    
    ⚠️ 실제로 사용하려면 product_table 테이블이 DB에 있어야 합니다.
    """
    async with async_session_maker() as db:
        # 1. API 라우트 생성
        route = ApiRoute(
            path="products",
            method="GET",
            name="상품 목록 조회",
            description="가격 필터링이 가능한 상품 목록 API",
            tags="products,shop",
            is_active=True,
            created_by="example_script",
        )
        db.add(route)
        await db.flush()
        
        # 2. API 버전 생성 (실제 로직 정의)
        version = ApiVersion(
            route_id=route.id,
            version=1,
            is_current=True,
            
            # 입력 파라미터 정의
            request_spec={
                "min_price": {
                    "type": "int",
                    "required": False,
                    "default": 0,
                    "min_value": 0,
                    "description": "최소 가격"
                },
                "max_price": {
                    "type": "int",
                    "required": False,
                    "description": "최대 가격"
                },
                "category": {
                    "type": "string",
                    "required": False,
                    "description": "카테고리 필터"
                },
                "limit": {
                    "type": "int",
                    "required": False,
                    "default": 20,
                    "min_value": 1,
                    "max_value": 100,
                    "description": "최대 조회 개수"
                }
            },
            
            # 실행할 SQL (파라미터 바인딩 사용)
            logic_type="SQL",
            logic_body="""
                SELECT id, name, price, category, stock
                FROM product_table
                WHERE price >= :min_price
                ORDER BY created_at DESC
                LIMIT :limit
            """,
            
            # 응답 포맷
            response_spec={
                "success": True,
                "products": "$result",
                "total": "$result_count"
            },
            
            # 상태 코드 매핑
            status_codes={
                "success": 200,
                "not_found": 200
            },
            
            change_note="상품 목록 API 초기 버전",
            created_by="example_script",
        )
        db.add(version)
        
        # 3. 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_ROUTE",
            target_id=route.id,
            action="CREATE",
            new_value=AuditService.model_to_dict(route),
            description="예제 스크립트로 상품 API 생성",
            actor="example_script",
        )
        
        await db.commit()
        
        print(f"✅ 상품 API 생성 완료: GET /api/products")
        print(f"   Route ID: {route.id}")
        print(f"   Version: {version.version}")


async def create_user_registration_api():
    """
    회원가입 API 생성 예제
    
    POST /api/users/register
    """
    async with async_session_maker() as db:
        route = ApiRoute(
            path="users/register",
            method="POST",
            name="회원가입",
            description="새 사용자 등록 API",
            tags="users,auth",
            is_active=True,
            created_by="example_script",
        )
        db.add(route)
        await db.flush()
        
        version = ApiVersion(
            route_id=route.id,
            version=1,
            is_current=True,
            
            request_spec={
                "email": {
                    "type": "string",
                    "required": True,
                    "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
                    "description": "이메일 주소"
                },
                "password": {
                    "type": "string",
                    "required": True,
                    "min_length": 8,
                    "max_length": 100,
                    "description": "비밀번호 (8자 이상)"
                },
                "name": {
                    "type": "string",
                    "required": True,
                    "min_length": 2,
                    "max_length": 50,
                    "description": "사용자 이름"
                }
            },
            
            logic_type="SQL",
            logic_body="""
                INSERT INTO users (email, password, name, created_at)
                VALUES (:email, :password, :name, NOW())
            """,
            
            response_spec={
                "success": True,
                "message": "회원가입이 완료되었습니다.",
                "data": "$result"
            },
            
            status_codes={
                "success": 201
            },
            
            change_note="회원가입 API 초기 버전",
            created_by="example_script",
        )
        db.add(version)
        
        await db.commit()
        
        print(f"✅ 회원가입 API 생성 완료: POST /api/users/register")


async def main():
    print("=" * 50)
    print("📝 API 생성 예제")
    print("=" * 50)
    
    print("\n1. 상품 목록 API 생성...")
    await create_products_api()
    
    print("\n2. 회원가입 API 생성...")
    await create_user_registration_api()
    
    print("\n" + "=" * 50)
    print("✅ 모든 예제 API가 생성되었습니다!")
    print("=" * 50)
    print("\n⚠️ 참고: 실제 SQL이 작동하려면 해당 테이블이 DB에 있어야 합니다.")


if __name__ == "__main__":
    asyncio.run(main())

