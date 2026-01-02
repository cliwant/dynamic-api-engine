"""
API 라우트 모델
API의 기본 정보(경로, 메서드, 활성 상태)를 관리합니다.

테이블명: APP_API_ROUTE_L
네이밍 규칙: 기존 cliwant DB 패턴 준수
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApiRoute(Base):
    """
    API 라우트 정의 테이블
    
    각 API의 기본 정보를 저장합니다.
    실제 동작 로직은 ApiVersion에서 관리됩니다.
    """
    __tablename__ = "APP_API_ROUTE_L"
    
    # Primary Key (기존 패턴: varchar(50))
    ROUTE_ID = Column(String(50), primary_key=True, comment="라우트 고유 ID")
    
    # API 식별 정보
    API_PATH = Column(String(255), nullable=False, comment="API 경로 (예: user-info, products)")
    HTTP_MTHD = Column(String(10), nullable=False, comment="HTTP 메서드 (GET, POST, PUT, DELETE)")
    
    # 메타데이터
    API_NAME = Column(String(255), nullable=True, comment="API 이름 (사람이 읽기 쉬운 이름)")
    API_DESC = Column(Text, nullable=True, comment="API 설명")
    TAGS = Column(String(500), nullable=True, comment="태그 (쉼표로 구분)")
    
    # 상태 관리 (기존 패턴: char(1) Y/N)
    USE_YN = Column(String(1), default='Y', nullable=False, comment="사용 여부 (Y/N)")
    DEL_YN = Column(String(1), default='N', nullable=False, comment="삭제 여부 (Y/N)")
    
    # 보안 설정
    AUTH_YN = Column(String(1), default='N', nullable=False, comment="인증 필요 여부 (Y/N)")
    ALWD_ORGNS = Column(Text, nullable=True, comment="허용된 Origin (CORS)")
    RATE_LMT = Column(String(10), default='100', comment="분당 요청 제한")
    
    # 타임스탬프 (기존 패턴: CREA_DT, UPDT_DT)
    CREA_DT = Column(DateTime, default=datetime.utcnow, nullable=False, comment="생성일시")
    UPDT_DT = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="수정일시")
    DEL_DT = Column(DateTime, nullable=True, comment="삭제일시")
    
    # 생성자/수정자 정보
    CREA_BY = Column(String(100), nullable=True, comment="생성자")
    UPDT_BY = Column(String(100), nullable=True, comment="수정자")
    
    # Relationships
    versions = relationship("ApiVersion", back_populates="route", lazy="dynamic")
    
    # Indexes
    __table_args__ = (
        Index("IDX_API_ROUTE_PATH_MTHD", "API_PATH", "HTTP_MTHD"),
        Index("IDX_API_ROUTE_USE_YN", "USE_YN"),
        Index("IDX_API_ROUTE_DEL_YN", "DEL_YN"),
    )
    
    # Python 속성으로 접근 편의성 제공
    @property
    def id(self):
        return self.ROUTE_ID
    
    @property
    def path(self):
        return self.API_PATH
    
    @property
    def method(self):
        return self.HTTP_MTHD
    
    @property
    def name(self):
        return self.API_NAME
    
    @property
    def description(self):
        return self.API_DESC
    
    @property
    def tags(self):
        return self.TAGS
    
    @property
    def is_active(self):
        return self.USE_YN == 'Y'
    
    @property
    def is_deleted(self):
        return self.DEL_YN == 'Y'
    
    @property
    def require_auth(self):
        return self.AUTH_YN == 'Y'
    
    @property
    def allowed_origins(self):
        return self.ALWD_ORGNS
    
    @property
    def rate_limit(self):
        return int(self.RATE_LMT) if self.RATE_LMT else 100
    
    @property
    def created_at(self):
        return self.CREA_DT
    
    @property
    def updated_at(self):
        return self.UPDT_DT
    
    @property
    def deleted_at(self):
        return self.DEL_DT
    
    @property
    def created_by(self):
        return self.CREA_BY
    
    def __repr__(self):
        return f"<ApiRoute(id={self.ROUTE_ID}, path='{self.API_PATH}', method='{self.HTTP_MTHD}')>"
