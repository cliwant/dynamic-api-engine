"""
API 버전 모델
API의 실제 동작 로직을 버전별로 관리합니다.
수정 시 기존 행을 업데이트하지 않고 새 버전을 INSERT합니다.

테이블명: APP_API_VERSION_H (히스토리 테이블)
네이밍 규칙: 기존 cliwant DB 패턴 준수
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApiVersion(Base):
    """
    API 버전 테이블
    
    각 API의 상세 로직을 버전별로 관리합니다.
    - REQ_SPEC: 입력 파라미터 검증 규칙
    - LOGIC_TYPE: 실행 로직 타입 (SQL, PYTHON_EXPR, HTTP_CALL 등)
    - LOGIC_BODY: 실제 실행할 로직
    - RESP_SPEC: 응답 데이터 매핑 규칙
    
    ⚠️ 보안 주의사항:
    - LOGIC_BODY의 SQL은 반드시 파라미터 바인딩(:param)을 사용해야 합니다.
    - 직접 문자열 연결은 SQL Injection 위험이 있습니다.
    """
    __tablename__ = "APP_API_VERSION_H"
    
    # Primary Key
    VERSION_ID = Column(String(50), primary_key=True, comment="버전 고유 ID")
    
    # Foreign Key
    ROUTE_ID = Column(String(50), ForeignKey("APP_API_ROUTE_L.ROUTE_ID", ondelete="RESTRICT"), nullable=False)
    
    # 버전 정보
    VERSION_NO = Column(Integer, nullable=False, comment="버전 번호 (자동 증가)")
    CRNT_YN = Column(String(1), default='Y', nullable=False, comment="현재 활성 버전 여부 (Y/N)")
    
    # Request 스펙 (JSON)
    # 예: {"user_id": {"type": "int", "required": true}, "name": {"type": "string", "max_length": 100}}
    REQ_SPEC = Column(JSON, nullable=True, comment="요청 파라미터 검증 규칙")
    
    # 실행 로직
    LOGIC_TYPE = Column(
        String(50), 
        default="SQL", 
        nullable=False,
        comment="로직 타입: SQL, PYTHON_EXPR, HTTP_CALL, STATIC_RESPONSE"
    )
    
    # 로직 본문
    LOGIC_BODY = Column(Text, nullable=False, comment="실행할 로직 (SQL 쿼리 또는 표현식)")
    
    # 로직 설정 (추가 옵션)
    LOGIC_CFG = Column(JSON, nullable=True, comment="로직 추가 설정 (타임아웃, 재시도 등)")
    
    # Response 스펙 (JSON)
    RESP_SPEC = Column(JSON, nullable=True, comment="응답 데이터 매핑 규칙")
    
    # 상태 코드 매핑
    STATUS_CDS = Column(JSON, nullable=True, comment="상태 코드 매핑")
    
    # 샘플 파라미터 (테스트용 예시 값)
    SMPL_PARAMS = Column(JSON, nullable=True, comment="테스트용 샘플 파라미터 값")
    
    # 메타데이터
    CHG_NOTE = Column(Text, nullable=True, comment="변경 사유 (버전 히스토리용)")
    
    # 타임스탬프
    CREA_DT = Column(DateTime, default=datetime.utcnow, nullable=False, comment="생성일시")
    
    # 생성자 정보
    CREA_BY = Column(String(100), nullable=True, comment="생성자")
    
    # Relationships
    route = relationship("ApiRoute", back_populates="versions")
    
    # Indexes
    __table_args__ = (
        Index("IDX_API_VERSION_ROUTE", "ROUTE_ID", "VERSION_NO"),
        Index("IDX_API_VERSION_CRNT", "ROUTE_ID", "CRNT_YN"),
    )
    
    # Python 속성으로 접근 편의성 제공
    @property
    def id(self):
        return self.VERSION_ID
    
    @property
    def route_id(self):
        return self.ROUTE_ID
    
    @property
    def version(self):
        return self.VERSION_NO
    
    @property
    def is_current(self):
        return self.CRNT_YN == 'Y'
    
    @property
    def request_spec(self):
        return self.REQ_SPEC
    
    @property
    def logic_type(self):
        return self.LOGIC_TYPE
    
    @property
    def logic_body(self):
        return self.LOGIC_BODY
    
    @property
    def logic_config(self):
        return self.LOGIC_CFG
    
    @property
    def response_spec(self):
        return self.RESP_SPEC
    
    @property
    def status_codes(self):
        return self.STATUS_CDS
    
    @property
    def sample_params(self):
        return self.SMPL_PARAMS
    
    @property
    def change_note(self):
        return self.CHG_NOTE
    
    @property
    def created_at(self):
        return self.CREA_DT
    
    @property
    def created_by(self):
        return self.CREA_BY
    
    def __repr__(self):
        return f"<ApiVersion(id={self.VERSION_ID}, route_id={self.ROUTE_ID}, version={self.VERSION_NO})>"
