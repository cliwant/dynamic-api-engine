-- ============================================
-- 읽기 전용 DB 계정 생성 스크립트
-- 자연어 SQL 쿼리 실행용 보안 계정
-- ============================================

-- 주의: 이 스크립트는 MySQL 관리자 권한으로 실행해야 합니다.
-- 실행 전 READONLY_PASSWORD를 안전한 비밀번호로 변경하세요.

-- 1. 읽기 전용 사용자 생성
-- 비밀번호를 안전한 값으로 변경하세요!
CREATE USER IF NOT EXISTS 'api_readonly'@'%' 
IDENTIFIED BY 'CHANGE_THIS_PASSWORD_TO_SECURE_ONE';

-- 2. 읽기 전용 권한 부여 (SELECT만 허용)
-- 데이터베이스 이름(cliwant)을 실제 DB명으로 변경하세요.
GRANT SELECT ON cliwant.* TO 'api_readonly'@'%';

-- 3. 권한 적용
FLUSH PRIVILEGES;

-- ============================================
-- 환경변수 설정 (.env 파일에 추가)
-- ============================================
-- MYSQL_READONLY_USER=api_readonly
-- MYSQL_READONLY_PASSWORD=CHANGE_THIS_PASSWORD_TO_SECURE_ONE

-- ============================================
-- 권한 확인
-- ============================================
-- SHOW GRANTS FOR 'api_readonly'@'%';

-- ============================================
-- 추가 보안 권장사항
-- ============================================
-- 
-- 1. 민감 테이블 접근 제한 (선택적)
--    특정 민감 테이블에 대한 접근을 차단하려면:
--    REVOKE SELECT ON cliwant.sensitive_table FROM 'api_readonly'@'%';
--
-- 2. 특정 컬럼만 허용 (더 엄격한 제한)
--    GRANT SELECT (col1, col2) ON cliwant.user_table TO 'api_readonly'@'%';
--
-- 3. 접속 IP 제한
--    프로덕션에서는 '%' 대신 특정 IP로 제한:
--    CREATE USER 'api_readonly'@'10.0.0.%' ...
--
-- 4. 연결 수 제한
--    ALTER USER 'api_readonly'@'%' WITH MAX_USER_CONNECTIONS 10;
--
-- 5. 계정 삭제 (필요시)
--    DROP USER 'api_readonly'@'%';
