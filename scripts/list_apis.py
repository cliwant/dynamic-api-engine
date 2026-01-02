"""
현재 등록된 API 목록 조회
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DB'),
    port=int(os.getenv('MYSQL_PORT', 3306))
)

cursor = conn.cursor()
cursor.execute('''
    SELECT r.API_PATH, r.HTTP_MTHD, r.API_NAME, r.TAGS, v.LOGIC_TYPE
    FROM APP_API_ROUTE_L r
    LEFT JOIN APP_API_VERSION_H v ON r.ROUTE_ID = v.ROUTE_ID AND v.CRNT_YN = 'Y'
    WHERE r.USE_YN = 'Y' AND r.DEL_YN = 'N'
    ORDER BY r.TAGS, r.API_PATH
''')

print("현재 등록된 API 목록:")
print("=" * 90)
print(f"{'METHOD':<8} {'PATH':<40} {'TYPE':<18} NAME")
print("-" * 90)

for row in cursor.fetchall():
    path, method, name, tags, logic_type = row
    lt = logic_type if logic_type else "N/A"
    print(f"{method:<8} /api/{path:<35} [{lt:<15}] {name}")

cursor.execute("SELECT COUNT(*) FROM APP_API_ROUTE_L WHERE USE_YN = 'Y' AND DEL_YN = 'N'")
total = cursor.fetchone()[0]
print("-" * 90)
print(f"총 {total}개의 API가 등록되어 있습니다.")

conn.close()

