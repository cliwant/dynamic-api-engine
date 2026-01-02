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
    
    @property
    def database_url(self) -> str:
        """SQLAlchemy 비동기 연결 URL 생성"""
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    api_key: str = os.getenv("API_KEY", "your-admin-api-key")
    
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
