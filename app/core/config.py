"""
애플리케이션 설정 관리
환경 변수 및 기본 설정을 관리합니다.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Database (기존 .env 형식에 맞춤)
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_db: str = os.getenv("MYSQL_DB", "cliwant")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_pool_size: int = int(os.getenv("MYSQL_POOL_SIZE", "10"))
    
    # 읽기 전용 DB 계정 (자연어 SQL 쿼리 실행용)
    # 설정되지 않으면 기본 계정 사용 (경고 로그 출력)
    mysql_readonly_user: str = os.getenv("MYSQL_READONLY_USER", "")
    mysql_readonly_password: str = os.getenv("MYSQL_READONLY_PASSWORD", "")
    
    @property
    def database_url(self) -> str:
        """SQLAlchemy 비동기 연결 URL 생성 (기본 - 전체 권한)"""
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
    @property
    def readonly_database_url(self) -> str:
        """읽기 전용 DB 연결 URL (자연어 SQL 쿼리용)"""
        # 읽기 전용 계정이 설정되어 있으면 사용, 아니면 기본 계정 사용
        user = self.mysql_readonly_user or self.mysql_user
        password = self.mysql_readonly_password or self.mysql_password
        return f"mysql+aiomysql://{user}:{password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
    @property
    def has_readonly_account(self) -> bool:
        """읽기 전용 계정이 설정되어 있는지 확인"""
        return bool(self.mysql_readonly_user and self.mysql_readonly_password)
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    api_key: str = os.getenv("API_KEY", "your-admin-api-key")
    
    # CORS 설정 (쉼표로 구분된 도메인 목록)
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS 허용 도메인 목록 반환"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    # Application
    app_name: str = "Prompt API Engine"
    debug: bool = os.getenv("ENV", "dev") == "dev"
    
    # API Engine 설정
    max_query_timeout: int = 30  # 쿼리 타임아웃 (초)
    enable_audit_log: bool = True  # 감사 로그 활성화
    soft_delete_only: bool = True  # 삭제 대신 비활성화만 허용
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환"""
    return Settings()
