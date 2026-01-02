"""
API 버전 서비스
API 버전의 CRUD 작업을 처리합니다.
"""
from typing import Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_version import ApiVersion
from app.models.api_route import ApiRoute
from app.schemas.api_version import ApiVersionCreate
from app.services.audit_service import AuditService, generate_id


class ApiVersionService:
    """API 버전 서비스"""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, version_id: str) -> Optional[ApiVersion]:
        """ID로 버전 조회"""
        result = await db.execute(
            select(ApiVersion).where(ApiVersion.VERSION_ID == version_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_current_version(db: AsyncSession, route_id: str) -> Optional[ApiVersion]:
        """
        라우트의 현재(최신) 버전 조회
        
        CRNT_YN='Y'인 버전을 우선 반환하고,
        없으면 가장 높은 VERSION_NO를 가진 버전 반환
        """
        # CRNT_YN='Y'인 버전 먼저 확인
        result = await db.execute(
            select(ApiVersion).where(
                and_(
                    ApiVersion.ROUTE_ID == route_id,
                    ApiVersion.CRNT_YN == 'Y',
                )
            )
        )
        version = result.scalar_one_or_none()
        
        if version:
            return version
        
        # 없으면 최신 버전 반환
        result = await db.execute(
            select(ApiVersion)
            .where(ApiVersion.ROUTE_ID == route_id)
            .order_by(ApiVersion.VERSION_NO.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_version_by_number(
        db: AsyncSession,
        route_id: str,
        version_number: int,
    ) -> Optional[ApiVersion]:
        """특정 버전 번호로 조회"""
        result = await db.execute(
            select(ApiVersion).where(
                and_(
                    ApiVersion.ROUTE_ID == route_id,
                    ApiVersion.VERSION_NO == version_number,
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_versions(
        db: AsyncSession,
        route_id: str,
    ) -> list[ApiVersion]:
        """라우트의 모든 버전 목록 조회"""
        result = await db.execute(
            select(ApiVersion)
            .where(ApiVersion.ROUTE_ID == route_id)
            .order_by(ApiVersion.VERSION_NO.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_next_version_number(db: AsyncSession, route_id: str) -> int:
        """다음 버전 번호 계산"""
        result = await db.execute(
            select(func.max(ApiVersion.VERSION_NO))
            .where(ApiVersion.ROUTE_ID == route_id)
        )
        max_version = result.scalar()
        return (max_version or 0) + 1
    
    @staticmethod
    async def create(
        db: AsyncSession,
        data: ApiVersionCreate,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> ApiVersion:
        """
        새 버전 생성
        
        ⚠️ 기존 버전을 수정하지 않고 항상 새 버전을 생성합니다.
        이를 통해 완전한 변경 이력을 유지합니다.
        """
        route_id = str(data.route_id)
        
        # 라우트 존재 확인
        route_result = await db.execute(
            select(ApiRoute).where(
                and_(
                    ApiRoute.ROUTE_ID == route_id,
                    ApiRoute.DEL_YN == 'N',
                )
            )
        )
        route = route_result.scalar_one_or_none()
        if not route:
            raise ValueError(f"존재하지 않는 라우트입니다: {route_id}")
        
        # 모든 기존 버전의 CRNT_YN을 'N'으로
        existing_versions = await db.execute(
            select(ApiVersion).where(ApiVersion.ROUTE_ID == route_id)
        )
        for v in existing_versions.scalars():
            v.CRNT_YN = 'N'
        
        # 새 버전 번호 계산
        next_version = await ApiVersionService.get_next_version_number(db, route_id)
        
        # 새 버전 생성
        version = ApiVersion(
            VERSION_ID=generate_id(),
            ROUTE_ID=route_id,
            VERSION_NO=next_version,
            CRNT_YN='Y',
            REQ_SPEC=data.request_spec,
            LOGIC_TYPE=data.logic_type,
            LOGIC_BODY=data.logic_body,
            LOGIC_CFG=data.logic_config,
            RESP_SPEC=data.response_spec,
            STATUS_CDS=data.status_codes,
            SMPL_PARAMS=data.sample_params,
            CHG_NOTE=data.change_note,
            CREA_BY=actor,
        )
        db.add(version)
        await db.flush()
        
        # 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_VERSION",
            target_id=version.VERSION_ID,
            action="VERSION_CREATE",
            new_value=AuditService.model_to_dict(version),
            description=f"새 버전 생성: {route.API_PATH} v{next_version}",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return version
    
    @staticmethod
    async def rollback_to_version(
        db: AsyncSession,
        route_id: str,
        target_version: int,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> Optional[ApiVersion]:
        """
        특정 버전으로 롤백
        
        ⚠️ 실제로 이전 버전의 내용을 복사하여 새 버전을 생성합니다.
        기존 버전은 보존됩니다.
        """
        # 대상 버전 조회
        target = await ApiVersionService.get_version_by_number(db, route_id, target_version)
        if not target:
            return None
        
        # 현재 최신 버전 정보
        current = await ApiVersionService.get_current_version(db, route_id)
        
        # 롤백 버전 데이터로 새 버전 생성
        new_data = ApiVersionCreate(
            route_id=route_id,
            request_spec=target.REQ_SPEC,
            logic_type=target.LOGIC_TYPE,
            logic_body=target.LOGIC_BODY,
            logic_config=target.LOGIC_CFG,
            response_spec=target.RESP_SPEC,
            status_codes=target.STATUS_CDS,
            sample_params=target.SMPL_PARAMS,
            change_note=f"버전 {target_version}으로 롤백 (이전: v{current.VERSION_NO if current else 'N/A'})",
        )
        
        new_version = await ApiVersionService.create(db, new_data, actor, actor_ip)
        
        # 롤백 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_VERSION",
            target_id=new_version.VERSION_ID,
            action="ROLLBACK",
            old_value={"from_version": current.VERSION_NO if current else None},
            new_value={"to_version": target_version, "new_version": new_version.VERSION_NO},
            description=f"버전 롤백: v{target_version} -> v{new_version.VERSION_NO}",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return new_version
    
    @staticmethod
    async def set_current_version(
        db: AsyncSession,
        route_id: str,
        version_number: int,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> Optional[ApiVersion]:
        """특정 버전을 현재 버전으로 설정"""
        # 대상 버전 확인
        target = await ApiVersionService.get_version_by_number(db, route_id, version_number)
        if not target:
            return None
        
        # 모든 버전의 CRNT_YN을 'N'으로
        all_versions = await db.execute(
            select(ApiVersion).where(ApiVersion.ROUTE_ID == route_id)
        )
        for v in all_versions.scalars():
            v.CRNT_YN = 'N'
        
        # 대상 버전을 current로
        target.CRNT_YN = 'Y'
        await db.flush()
        
        # 감사 로그
        await AuditService.log(
            db=db,
            target_type="API_VERSION",
            target_id=target.VERSION_ID,
            action="SET_CURRENT",
            new_value={"version": version_number},
            description=f"현재 버전 변경: v{version_number}",
            actor=actor,
            actor_ip=actor_ip,
        )
        
        return target
