-- ============================================
-- Prompt API Engine - Database Schema
-- 기존 cliwant DB 네이밍 규칙 준수
-- ============================================
-- 테이블 접두사: APP_
-- 접미사: _L (List), _H (History), _M (Master)
-- 컬럼명: 대문자 스네이크 케이스
-- ID: varchar(50) UUID
-- Y/N 플래그: char(1)
-- 날짜: CREA_DT, UPDT_DT, DEL_DT

USE cliwant;

-- ============================================
-- 1. APP_API_ROUTE_L (API 라우트 리스트)
-- ============================================
CREATE TABLE IF NOT EXISTS APP_API_ROUTE_L (
    ROUTE_ID VARCHAR(50) NOT NULL PRIMARY KEY COMMENT '라우트 고유 ID',
    
    -- API 식별 정보
    API_PATH VARCHAR(255) NOT NULL COMMENT 'API 경로 (예: user-info, products)',
    HTTP_MTHD VARCHAR(10) NOT NULL COMMENT 'HTTP 메서드 (GET, POST, PUT, DELETE)',
    
    -- 메타데이터
    API_NAME VARCHAR(255) NULL COMMENT 'API 이름',
    API_DESC TEXT NULL COMMENT 'API 설명',
    TAGS VARCHAR(500) NULL COMMENT '태그 (쉼표로 구분)',
    
    -- 상태 관리
    USE_YN CHAR(1) NOT NULL DEFAULT 'Y' COMMENT '사용 여부 (Y/N)',
    DEL_YN CHAR(1) NOT NULL DEFAULT 'N' COMMENT '삭제 여부 (Y/N)',
    
    -- 보안 설정
    AUTH_YN CHAR(1) NOT NULL DEFAULT 'N' COMMENT '인증 필요 여부 (Y/N)',
    ALWD_ORGNS TEXT NULL COMMENT '허용된 Origin (CORS)',
    RATE_LMT VARCHAR(10) DEFAULT '100' COMMENT '분당 요청 제한',
    
    -- 타임스탬프
    CREA_DT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    UPDT_DT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    DEL_DT TIMESTAMP NULL COMMENT '삭제일시',
    
    -- 생성자/수정자
    CREA_BY VARCHAR(100) NULL COMMENT '생성자',
    UPDT_BY VARCHAR(100) NULL COMMENT '수정자',
    
    -- 인덱스
    INDEX IDX_API_ROUTE_PATH_MTHD (API_PATH, HTTP_MTHD),
    INDEX IDX_API_ROUTE_USE_YN (USE_YN),
    INDEX IDX_API_ROUTE_DEL_YN (DEL_YN)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='API 라우트 정의 테이블';


-- ============================================
-- 2. APP_API_VERSION_H (API 버전 히스토리)
-- ============================================
CREATE TABLE IF NOT EXISTS APP_API_VERSION_H (
    VERSION_ID VARCHAR(50) NOT NULL PRIMARY KEY COMMENT '버전 고유 ID',
    
    -- Foreign Key
    ROUTE_ID VARCHAR(50) NOT NULL COMMENT '라우트 ID',
    
    -- 버전 정보
    VERSION_NO INT NOT NULL COMMENT '버전 번호',
    CRNT_YN CHAR(1) NOT NULL DEFAULT 'Y' COMMENT '현재 활성 버전 여부 (Y/N)',
    
    -- Request 스펙 (JSON)
    REQ_SPEC JSON NULL COMMENT '요청 파라미터 검증 규칙',
    
    -- 실행 로직
    LOGIC_TYPE VARCHAR(50) NOT NULL DEFAULT 'SQL' COMMENT '로직 타입: SQL, PYTHON_EXPR, HTTP_CALL, STATIC_RESPONSE',
    LOGIC_BODY TEXT NOT NULL COMMENT '실행할 로직',
    LOGIC_CFG JSON NULL COMMENT '로직 추가 설정',
    
    -- Response 스펙 (JSON)
    RESP_SPEC JSON NULL COMMENT '응답 데이터 매핑 규칙',
    STATUS_CDS JSON NULL COMMENT '상태 코드 매핑',
    
    -- 메타데이터
    CHG_NOTE TEXT NULL COMMENT '변경 사유',
    
    -- 타임스탬프
    CREA_DT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    
    -- 생성자
    CREA_BY VARCHAR(100) NULL COMMENT '생성자',
    
    -- Foreign Key 제약
    CONSTRAINT FK_API_VERSION_ROUTE FOREIGN KEY (ROUTE_ID)
        REFERENCES APP_API_ROUTE_L(ROUTE_ID) ON DELETE RESTRICT ON UPDATE CASCADE,
    
    -- 인덱스
    INDEX IDX_API_VERSION_ROUTE (ROUTE_ID, VERSION_NO),
    INDEX IDX_API_VERSION_CRNT (ROUTE_ID, CRNT_YN),
    
    -- 유니크 제약
    UNIQUE KEY UK_ROUTE_VERSION (ROUTE_ID, VERSION_NO)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='API 버전 히스토리 테이블';


-- ============================================
-- 3. APP_API_AUDIT_H (API 감사 로그)
-- ============================================
CREATE TABLE IF NOT EXISTS APP_API_AUDIT_H (
    AUDIT_ID VARCHAR(50) NOT NULL PRIMARY KEY COMMENT '감사로그 고유 ID',
    
    -- 대상 정보
    TRGT_TYPE VARCHAR(50) NOT NULL COMMENT '대상 타입: API_ROUTE, API_VERSION',
    TRGT_ID VARCHAR(50) NOT NULL COMMENT '대상 ID',
    
    -- 작업 정보
    ACTION VARCHAR(50) NOT NULL COMMENT '작업 타입: CREATE, UPDATE, DELETE, RESTORE, ROLLBACK 등',
    
    -- 변경 전후 데이터
    OLD_VAL JSON NULL COMMENT '변경 전 값',
    NEW_VAL JSON NULL COMMENT '변경 후 값',
    
    -- 설명
    `DESC` TEXT NULL COMMENT '변경 설명',
    
    -- 실행자 정보
    ACTOR VARCHAR(100) NULL COMMENT '실행자',
    ACTOR_IP VARCHAR(45) NULL COMMENT '실행자 IP',
    
    -- 타임스탬프
    CREA_DT TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
    
    -- 인덱스
    INDEX IDX_API_AUDIT_TRGT (TRGT_TYPE, TRGT_ID),
    INDEX IDX_API_AUDIT_ACTION (ACTION),
    INDEX IDX_API_AUDIT_CREA_DT (CREA_DT),
    INDEX IDX_API_AUDIT_ACTOR (ACTOR)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='API 감사 로그 테이블';


-- ============================================
-- 샘플 데이터 (선택사항)
-- ============================================

-- 샘플 API 1: Hello World
INSERT INTO APP_API_ROUTE_L (ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME, API_DESC, TAGS, USE_YN, DEL_YN, CREA_BY)
VALUES (
    UUID(),
    'hello',
    'GET',
    'Hello World API',
    '간단한 인사 API입니다.',
    'sample,hello',
    'Y',
    'N',
    'system'
);

SET @hello_route_id = (SELECT ROUTE_ID FROM APP_API_ROUTE_L WHERE API_PATH = 'hello' AND HTTP_MTHD = 'GET' LIMIT 1);

INSERT INTO APP_API_VERSION_H (VERSION_ID, ROUTE_ID, VERSION_NO, CRNT_YN, REQ_SPEC, LOGIC_TYPE, LOGIC_BODY, RESP_SPEC, CHG_NOTE, CREA_BY)
VALUES (
    UUID(),
    @hello_route_id,
    1,
    'Y',
    '{"name": {"type": "string", "required": false, "default": "World", "description": "인사할 이름"}}',
    'STATIC_RESPONSE',
    '{"message": "Hello, World!", "timestamp": "2024-01-01T00:00:00"}',
    '{"success": true, "data": "$result"}',
    '초기 버전',
    'system'
);

-- 샘플 API 2: Echo
INSERT INTO APP_API_ROUTE_L (ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME, API_DESC, TAGS, USE_YN, DEL_YN, CREA_BY)
VALUES (
    UUID(),
    'echo',
    'POST',
    'Echo API',
    '입력받은 데이터를 그대로 반환합니다.',
    'sample,echo',
    'Y',
    'N',
    'system'
);

SET @echo_route_id = (SELECT ROUTE_ID FROM APP_API_ROUTE_L WHERE API_PATH = 'echo' AND HTTP_MTHD = 'POST' LIMIT 1);

INSERT INTO APP_API_VERSION_H (VERSION_ID, ROUTE_ID, VERSION_NO, CRNT_YN, REQ_SPEC, LOGIC_TYPE, LOGIC_BODY, RESP_SPEC, CHG_NOTE, CREA_BY)
VALUES (
    UUID(),
    @echo_route_id,
    1,
    'Y',
    '{"message": {"type": "string", "required": true, "min_length": 1, "max_length": 1000, "description": "에코할 메시지"}}',
    'PYTHON_EXPR',
    '{"echo": params["message"], "length": len(params["message"])}',
    '{"success": true, "data": "$result"}',
    '초기 버전',
    'system'
);

-- ============================================
-- 완료 메시지
-- ============================================
SELECT 'Database schema created successfully!' AS message;
SELECT COUNT(*) AS route_count FROM APP_API_ROUTE_L;
SELECT COUNT(*) AS version_count FROM APP_API_VERSION_H;
