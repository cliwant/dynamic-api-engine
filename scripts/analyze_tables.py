"""
MySQL 테이블 구조 및 인덱스 분석 스크립트
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

# 주요 테이블들
important_tables = [
    'APP_USER_L', 'APP_CMPNY_L', 'APP_PROJ_L', 'APP_PRCR_PROJ_L',
    'APP_CNTRCT_PROJ_L', 'APP_BID_PLAN_L', 'APP_CORP_LCNS_L',
    'APP_CMPNY_PRDCT_L', 'APP_PROJ_DOC_L', 'APP_SRCH_L',
    'APP_CLNT_L', 'APP_FAVR_PROJ_L', 'APP_EMAIL_SRCH_L',
    'APP_CMPNY_PLAN_L', 'APP_SUBSCRIPTION_L'
]

results = {}

for table in important_tables:
    try:
        print(f'\n{"="*60}')
        print(f'테이블: {table}')
        print("="*60)
        
        # 컬럼 정보
        cursor.execute(f'DESCRIBE {table}')
        columns = cursor.fetchall()
        print(f'\n컬럼 ({len(columns)}개):')
        for col in columns:
            key_info = col[3] if col[3] else ""
            print(f'  {col[0]:30} {col[1]:25} {key_info}')
        
        # 인덱스 정보
        cursor.execute(f'SHOW INDEX FROM {table}')
        indexes = cursor.fetchall()
        if indexes:
            print(f'\n인덱스:')
            idx_dict = {}
            for idx in indexes:
                idx_name = idx[2]
                col_name = idx[4]
                if idx_name not in idx_dict:
                    idx_dict[idx_name] = []
                idx_dict[idx_name].append(col_name)
            
            for idx_name, cols in idx_dict.items():
                print(f'  {idx_name:30} -> {", ".join(cols)}')
        
        # 데이터 건수
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'\n데이터 건수: {count:,}')
        
        results[table] = {
            'columns': columns,
            'indexes': indexes,
            'count': count
        }
        
    except Exception as e:
        print(f'  오류: {e}')

conn.close()

print("\n\n" + "="*60)
print("분석 완료!")
print("="*60)

