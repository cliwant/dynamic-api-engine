"""
감사 로그 서비스
모든 API 정의 변경 사항을 기록합니다.
"""
from typing import Optional, Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


def generate_id() -> str:
    """UUID 기반 ID 생성 (기존 DB 패턴: varchar(50))"""
    return str(uuid.uuid4())


class AuditService:
    """감사 로그 서비스"""
    
    @staticmethod
    async def log(
        db: AsyncSession,
        target_type: str,
        target_id: str,
        action: str,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        description: Optional[str] = None,
        actor: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> AuditLog:
        """
        감사 로그 기록
        
        Args:
            db: 데이터베이스 세션
            target_type: 대상 타입 (API_ROUTE, API_VERSION)
            target_id: 대상 ID
            action: 작업 타입 (CREATE, UPDATE, VERSION_CREATE, ACTIVATE, DEACTIVATE, DELETE, RESTORE, ROLLBACK)
            old_value: 변경 전 값
            new_value: 변경 후 값
            description: 변경 설명
            actor: 실행자
            actor_ip: 실행자 IP
        """
        log_entry = AuditLog(
            AUDIT_ID=generate_id(),
            TRGT_TYPE=target_type,
            TRGT_ID=target_id,
            ACTION=action,
            OLD_VAL=old_value,
            NEW_VAL=new_value,
            DESC=description,
            ACTOR=actor,
            ACTOR_IP=actor_ip,
        )
        db.add(log_entry)
        await db.flush()
        return log_entry
    
    @staticmethod
    def model_to_dict(model: Any) -> dict:
        """모델 객체를 딕셔너리로 변환 (감사 로그용)"""
        if model is None:
            return None
        
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            # datetime 객체는 문자열로 변환
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            result[column.name] = value
        return result
