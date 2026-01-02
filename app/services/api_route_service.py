"""
API 라우트 서비스
API 라우트의 CRUD 작업을 처리합니다.
"""
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_route import ApiRoute
from app.models.api_version import ApiVersion
from app.schemas.api_route import ApiRouteCreate, ApiRouteUpdate
from app.services.audit_service import AuditService, generate_id
from app.core.config import get_settings

settings = get_settings()


class ApiRouteService:
    """API 라우트 서비스"""
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        route_id: str,
        include_deleted: bool = False,
    ) -> Optional[ApiRoute]:
        """ID로 라우트 조회"""
        query = select(ApiRoute).where(ApiRoute.ROUTE_ID == route_id)
        if not include_deleted:
            query = query.where(ApiRoute.DEL_YN == 'N')
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_path_method(
        db: AsyncSession,
        path: str,
        method: str,
        include_deleted: bool = False,
    ) -> Optional[ApiRoute]:
        """경로와 메서드로 라우트 조회"""
        query = select(ApiRoute).where(
            and_(
                ApiRoute.API_PATH == path,
                ApiRoute.HTTP_MTHD == method.upper(),
            )
        )
        if not include_deleted:
            query = query.where(ApiRoute.DEL_YN == 'N')
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_routes(
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        include_inactive: bool = False,
        include_deleted: bool = False,
    ) -> tuple[list[ApiRoute], int]:
        """라우트 목록 조회"""
        query = select(ApiRoute)
        count_query = select(func.count(ApiRoute.ROUTE_ID))
        
        if not include_inactive:
            query = query.where(ApiRoute.USE_YN == 'Y')
            count_query = count_query.where(ApiRoute.USE_YN == 'Y')
        
        if not include_deleted:
            query = query.where(ApiRoute.DEL_YN == 'N')
            count_query = count_query.where(ApiRoute.DEL_YN == 'N')
        
        # 페이지네이션
        offset = (page - 1) * size
        query = query.order_by(ApiRoute.CREA_DT.desc()).offset(offset).limit(size)
        
        result = await db.execute(query)
        routes = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return routes, total
    
    @staticmethod
    async def create(
        db: AsyncSession,
        data: ApiRouteCreate,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> ApiRoute:
        """새 라우트 생성"""
        # 중복 검사
        existing = await ApiRouteService.get_by_path_method(
            db, data.path, data.method, include_deleted=True
        )
        if existing:
            if existing.DEL_YN == 'Y':
                # 삭제된 라우트가 있으면 복원
                existing.DEL_YN = 'N'
                existing.DEL_DT = None
                existing.USE_YN = 'Y'
                existing.UPDT_DT = datetime.utcnow()
                existing.UPDT_BY = actor
                await db.flush()
                
                # 감사 로그
                await AuditService.log(
                    db=db,
                    target_type="API_ROUTE",
                    target_id=existing.ROUTE_ID,
                    action="RESTORE",
                    new_value=AuditService.model_to_dict(existing),
                    description=f"라우트 복원: {data.path} [{data.method}]",
                    actor=actor,
                    actor_ip=actor_ip,
                )
                return existing
            else:
                raise ValueError(f"이미 존재하는 API입니다: {data.path} [{data.method}]")
        
        # 새 라우트 생성
        route = ApiRoute(
            ROUTE_ID=generate_id(),
            API_PATH=data.path,
            HTTP_MTHD=data.method.upper(),
            API_NAME=data.name,
            API_DESC=data.description,
            TAGS=data.tags,
            AUTH_YN='Y' if data.require_auth else 'N',
            ALWD_ORGNS=data.allowed_origins,
            RATE_LMT=str(data.rate_limit),
            USE_YN='Y',
            DEL_YN='N',
            CREA_BY=actor,
            UPDT_BY=actor,
        )
        db.add(route)
        await db.flush()
        
        # 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_ROUTE",
            target_id=route.ROUTE_ID,
            action="CREATE",
            new_value=AuditService.model_to_dict(route),
            description=f"새 라우트 생성: {data.path} [{data.method}]",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return route
    
    @staticmethod
    async def update(
        db: AsyncSession,
        route_id: str,
        data: ApiRouteUpdate,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> Optional[ApiRoute]:
        """라우트 업데이트"""
        route = await ApiRouteService.get_by_id(db, route_id)
        if not route:
            return None
        
        old_value = AuditService.model_to_dict(route)
        
        # 변경 사항 적용
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "name":
                route.API_NAME = value
            elif field == "description":
                route.API_DESC = value
            elif field == "tags":
                route.TAGS = value
            elif field == "require_auth":
                route.AUTH_YN = 'Y' if value else 'N'
            elif field == "allowed_origins":
                route.ALWD_ORGNS = value
            elif field == "rate_limit":
                route.RATE_LMT = str(value)
            elif field == "is_active":
                route.USE_YN = 'Y' if value else 'N'
        
        route.UPDT_DT = datetime.utcnow()
        route.UPDT_BY = actor
        await db.flush()
        
        # 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_ROUTE",
            target_id=route.ROUTE_ID,
            action="UPDATE",
            old_value=old_value,
            new_value=AuditService.model_to_dict(route),
            description=f"라우트 업데이트: {route.API_PATH} [{route.HTTP_MTHD}]",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return route
    
    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        route_id: str,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> bool:
        """
        라우트 소프트 삭제
        
        ⚠️ 실제 데이터는 삭제하지 않고 DEL_YN 플래그만 설정합니다.
        복원이 필요할 경우를 대비합니다.
        """
        route = await ApiRouteService.get_by_id(db, route_id)
        if not route:
            return False
        
        old_value = AuditService.model_to_dict(route)
        
        route.DEL_YN = 'Y'
        route.USE_YN = 'N'
        route.DEL_DT = datetime.utcnow()
        route.UPDT_DT = datetime.utcnow()
        route.UPDT_BY = actor
        await db.flush()
        
        # 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_ROUTE",
            target_id=route.ROUTE_ID,
            action="DELETE",
            old_value=old_value,
            new_value=AuditService.model_to_dict(route),
            description=f"라우트 삭제: {route.API_PATH} [{route.HTTP_MTHD}]",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return True
    
    @staticmethod
    async def restore(
        db: AsyncSession,
        route_id: str,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> Optional[ApiRoute]:
        """삭제된 라우트 복원"""
        route = await ApiRouteService.get_by_id(db, route_id, include_deleted=True)
        if not route or route.DEL_YN != 'Y':
            return None
        
        old_value = AuditService.model_to_dict(route)
        
        route.DEL_YN = 'N'
        route.DEL_DT = None
        route.USE_YN = 'Y'
        route.UPDT_DT = datetime.utcnow()
        route.UPDT_BY = actor
        await db.flush()
        
        # 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_ROUTE",
            target_id=route.ROUTE_ID,
            action="RESTORE",
            old_value=old_value,
            new_value=AuditService.model_to_dict(route),
            description=f"라우트 복원: {route.API_PATH} [{route.HTTP_MTHD}]",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return route
