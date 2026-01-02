"""
감사 로그 모델
모든 API 정의 변경 사항을 추적합니다.
실수로 인한 데이터 손실을 방지하고 변경 이력을 관리합니다.

테이블명: APP_API_AUDIT_H (히스토리 테이블)
네이밍 규칙: 기존 cliwant DB 패턴 준수
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from app.core.database import Base


class AuditLog(Base):
    """
    감사 로그 테이블
    
    API 정의의 모든 변경 사항을 기록합니다.
    - CREATE: 새 API 생성
    - UPDATE: API 설정 변경
    - VERSION_CREATE: 새 버전 생성
    - ACTIVATE/DEACTIVATE: 활성화/비활성화
    - DELETE: 삭제 (soft delete)
    - RESTORE: 복원
    - ROLLBACK: 버전 롤백
    
    ⚠️ 이 테이블의 데이터는 절대 삭제하지 않습니다.
    """
    __tablename__ = "APP_API_AUDIT_H"
    
    # Primary Key
    AUDIT_ID = Column(String(50), primary_key=True, comment="감사로그 고유 ID")
    
    # 대상 정보
    TRGT_TYPE = Column(String(50), nullable=False, comment="대상 타입: API_ROUTE, API_VERSION")
    TRGT_ID = Column(String(50), nullable=False, comment="대상 ID")
    
    # 작업 정보
    ACTION = Column(
        String(50), 
        nullable=False,
        comment="작업 타입: CREATE, UPDATE, VERSION_CREATE, ACTIVATE, DEACTIVATE, DELETE, RESTORE, ROLLBACK"
    )
    
    # 변경 전후 데이터 (JSON)
    OLD_VAL = Column(JSON, nullable=True, comment="변경 전 값")
    NEW_VAL = Column(JSON, nullable=True, comment="변경 후 값")
    
    # 변경 설명
    DESC = Column(Text, nullable=True, comment="변경 설명")
    
    # 실행자 정보
    ACTOR = Column(String(100), nullable=True, comment="실행자 (사용자 ID 또는 시스템)")
    ACTOR_IP = Column(String(45), nullable=True, comment="실행자 IP 주소")
    
    # 타임스탬프
    CREA_DT = Column(DateTime, default=datetime.utcnow, nullable=False, comment="생성일시")
    
    # Indexes
    __table_args__ = (
        Index("IDX_API_AUDIT_TRGT", "TRGT_TYPE", "TRGT_ID"),
        Index("IDX_API_AUDIT_ACTION", "ACTION"),
        Index("IDX_API_AUDIT_CREA_DT", "CREA_DT"),
        Index("IDX_API_AUDIT_ACTOR", "ACTOR"),
    )
    
    # Python 속성으로 접근 편의성 제공
    @property
    def id(self):
        return self.AUDIT_ID
    
    @property
    def target_type(self):
        return self.TRGT_TYPE
    
    @property
    def target_id(self):
        return self.TRGT_ID
    
    @property
    def action(self):
        return self.ACTION
    
    @property
    def old_value(self):
        return self.OLD_VAL
    
    @property
    def new_value(self):
        return self.NEW_VAL
    
    @property
    def description(self):
        return self.DESC
    
    @property
    def actor(self):
        return self.ACTOR
    
    @property
    def actor_ip(self):
        return self.ACTOR_IP
    
    @property
    def created_at(self):
        return self.CREA_DT
    
    def __repr__(self):
        return f"<AuditLog(id={self.AUDIT_ID}, action='{self.ACTION}', target={self.TRGT_TYPE}:{self.TRGT_ID})>"
