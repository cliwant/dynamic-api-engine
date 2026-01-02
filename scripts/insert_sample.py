"""
샘플 API 데이터 삽입 스크립트
"""
import pymysql
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB"),
    port=int(os.getenv("MYSQL_PORT", 3306))
)

cursor = conn.cursor()

# 기존 샘플 데이터 확인
cursor.execute("SELECT COUNT(*) FROM APP_API_ROUTE_L")
count = cursor.fetchone()[0]
if count > 0:
    print(f"이미 {count}개의 라우트가 존재합니다. 샘플 데이터 삽입을 건너뜁니다.")
    conn.close()
    exit()

# 샘플 1: Hello API
hello_route_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO APP_API_ROUTE_L (ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME, API_DESC, TAGS, USE_YN, DEL_YN, CREA_BY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (hello_route_id, 'hello', 'GET', 'Hello World API', '간단한 인사 API입니다.', 'sample,hello', 'Y', 'N', 'system'))

hello_version_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO APP_API_VERSION_H (VERSION_ID, ROUTE_ID, VERSION_NO, CRNT_YN, REQ_SPEC, LOGIC_TYPE, LOGIC_BODY, RESP_SPEC, CHG_NOTE, CREA_BY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    hello_version_id,
    hello_route_id,
    1,
    'Y',
    '{"name": {"type": "string", "required": false, "default": "World", "description": "인사할 이름"}}',
    'STATIC_RESPONSE',
    '{"message": "Hello, World!", "timestamp": "2024-01-01T00:00:00"}',
    '{"success": true, "data": "$result"}',
    '초기 버전',
    'system'
))
print("✅ Hello API 추가 완료")

# 샘플 2: Echo API
echo_route_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO APP_API_ROUTE_L (ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME, API_DESC, TAGS, USE_YN, DEL_YN, CREA_BY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (echo_route_id, 'echo', 'POST', 'Echo API', '입력받은 데이터를 그대로 반환합니다.', 'sample,echo', 'Y', 'N', 'system'))

echo_version_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO APP_API_VERSION_H (VERSION_ID, ROUTE_ID, VERSION_NO, CRNT_YN, REQ_SPEC, LOGIC_TYPE, LOGIC_BODY, RESP_SPEC, CHG_NOTE, CREA_BY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    echo_version_id,
    echo_route_id,
    1,
    'Y',
    '{"message": {"type": "string", "required": true, "min_length": 1, "max_length": 1000, "description": "에코할 메시지"}}',
    'PYTHON_EXPR',
    '{"echo": params["message"], "length": len(params["message"])}',
    '{"success": true, "data": "$result"}',
    '초기 버전',
    'system'
))
print("✅ Echo API 추가 완료")

# 샘플 3: 사용자 목록 조회 API (SQL 예시)
users_route_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO APP_API_ROUTE_L (ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME, API_DESC, TAGS, USE_YN, DEL_YN, CREA_BY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (users_route_id, 'users', 'GET', '사용자 목록 조회', 'APP_USER_L 테이블에서 사용자 목록을 조회합니다.', 'users,sample', 'Y', 'N', 'system'))

users_version_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO APP_API_VERSION_H (VERSION_ID, ROUTE_ID, VERSION_NO, CRNT_YN, REQ_SPEC, LOGIC_TYPE, LOGIC_BODY, RESP_SPEC, CHG_NOTE, CREA_BY)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    users_version_id,
    users_route_id,
    1,
    'Y',
    '{"limit": {"type": "int", "required": false, "default": 10, "min_value": 1, "max_value": 100}}',
    'SQL',
    'SELECT USER_ID, EMAIL, FIRST_NAME, LAST_NAME, CREA_DT FROM APP_USER_L WHERE DEL_YN = \'N\' ORDER BY CREA_DT DESC LIMIT :limit',
    '{"success": true, "users": "$result", "count": "$result_count"}',
    '사용자 목록 조회 API',
    'system'
))
print("✅ Users API 추가 완료")

conn.commit()

# 확인
cursor.execute("SELECT ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME FROM APP_API_ROUTE_L")
print("\n📋 생성된 API 목록:")
for row in cursor.fetchall():
    print(f"  - {row[2]} /api/{row[1]} : {row[3]}")

conn.close()
print("\n🎉 샘플 API 추가 완료!")

