"""
샘플 API 30개 생성 스크립트
인덱스 최적화된 쿼리로 구성
"""
import pymysql
import uuid
import json
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

# 샘플 API 정의 (인덱스 최적화)
SAMPLE_APIS = [
    # ============ 사용자 관련 API (APP_USER_L) ============
    {
        "path": "users/list",
        "method": "GET",
        "name": "사용자 목록 조회",
        "desc": "최근 가입한 사용자 목록 조회 (IX_CREA_DT 인덱스 활용)",
        "tags": "users,list",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 20, "min_value": 1, "max_value": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT USER_ID, EMAIL, FIRST_NAME, LAST_NAME, CREA_DT FROM APP_USER_L WHERE DEL_YN = 'N' ORDER BY CREA_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "data": "$result", "count": "$result_count"}
    },
    {
        "path": "users/by-company",
        "method": "GET",
        "name": "회사별 사용자 조회",
        "desc": "특정 회사의 사용자 목록 (IX_CMPNY_ID 인덱스 활용)",
        "tags": "users,company",
        "req_spec": {
            "cmpny_id": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT USER_ID, EMAIL, FIRST_NAME, LAST_NAME, DEPT, CREA_DT FROM APP_USER_L WHERE CMPNY_ID = :cmpny_id AND DEL_YN = 'N'",
        "resp_spec": {"success": True, "users": "$result", "count": "$result_count"}
    },
    {
        "path": "users/detail",
        "method": "GET",
        "name": "사용자 상세 조회",
        "desc": "사용자 ID로 상세 정보 조회 (PRIMARY KEY 활용)",
        "tags": "users,detail",
        "req_spec": {
            "user_id": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT * FROM APP_USER_L WHERE USER_ID = :user_id",
        "resp_spec": {"success": True, "user": "$result"}
    },
    
    # ============ 회사 관련 API (APP_CMPNY_L) ============
    {
        "path": "companies/list",
        "method": "GET",
        "name": "회사 목록 조회",
        "desc": "회사 목록 페이지네이션 조회",
        "tags": "companies,list",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 20},
            "offset": {"type": "int", "required": False, "default": 0}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT CMPNY_ID, CMPNY_NAME, CMPNY_BIZ_NO, RGN_CD, CEO_NAME, CREA_DT FROM APP_CMPNY_L WHERE DEL_YN = 'N' ORDER BY CREA_DT DESC LIMIT :limit OFFSET :offset",
        "resp_spec": {"success": True, "companies": "$result", "count": "$result_count"}
    },
    {
        "path": "companies/by-bizno",
        "method": "GET",
        "name": "사업자번호로 회사 조회",
        "desc": "사업자번호로 회사 검색 (BIZ_NO 인덱스 활용)",
        "tags": "companies,search",
        "req_spec": {
            "biz_no": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT * FROM APP_CMPNY_L WHERE CMPNY_BIZ_NO = :biz_no AND DEL_YN = 'N'",
        "resp_spec": {"success": True, "company": "$result"}
    },
    {
        "path": "companies/detail",
        "method": "GET",
        "name": "회사 상세 조회",
        "desc": "회사 ID로 상세 정보 조회 (PRIMARY KEY 활용)",
        "tags": "companies,detail",
        "req_spec": {
            "cmpny_id": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT * FROM APP_CMPNY_L WHERE CMPNY_ID = :cmpny_id",
        "resp_spec": {"success": True, "company": "$result"}
    },
    
    # ============ 프로젝트 관련 API (APP_PROJ_L) ============
    {
        "path": "projects/recent",
        "method": "GET",
        "name": "최근 프로젝트 목록",
        "desc": "최근 업로드된 프로젝트 조회 (IX_UPLDDT 인덱스 활용)",
        "tags": "projects,recent",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 20}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, TYPE_CD, BDGT_AMT, BEGIN_DT, CLOSE_DT, UPLD_DT FROM APP_PROJ_L WHERE USE_YN = 'Y' ORDER BY UPLD_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "projects/by-type",
        "method": "GET",
        "name": "타입별 프로젝트 조회",
        "desc": "프로젝트 타입으로 필터링 (IX_TYPE_CD 인덱스 활용)",
        "tags": "projects,filter",
        "req_spec": {
            "type_cd": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 50}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, BDGT_AMT, BEGIN_DT, CLOSE_DT FROM APP_PROJ_L WHERE TYPE_CD = :type_cd AND USE_YN = 'Y' ORDER BY UPLD_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "projects/by-channel",
        "method": "GET",
        "name": "채널별 프로젝트 조회",
        "desc": "채널 타입으로 필터링 (IX_CHANNEL_TYPE 인덱스 활용)",
        "tags": "projects,channel",
        "req_spec": {
            "chnl_type": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 50}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, CHNL_SRC_CD, BDGT_AMT, BEGIN_DT, CLOSE_DT FROM APP_PROJ_L WHERE CHNL_TYPE = :chnl_type AND USE_YN = 'Y' ORDER BY CLOSE_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "projects/active",
        "method": "GET",
        "name": "진행중 프로젝트",
        "desc": "마감일이 남은 프로젝트 (IX_CLOSE_DT 인덱스 활용)",
        "tags": "projects,active",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, TYPE_CD, BDGT_AMT, BEGIN_DT, CLOSE_DT FROM APP_PROJ_L WHERE CLOSE_DT >= NOW() AND USE_YN = 'Y' ORDER BY CLOSE_DT ASC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "projects/by-notice",
        "method": "GET",
        "name": "공고번호로 프로젝트 조회",
        "desc": "공고번호 검색 (IX_NOTICE 인덱스 활용)",
        "tags": "projects,notice",
        "req_spec": {
            "notice_no": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, NOTICE_NO, NOTICE_ORD, TYPE_CD, BDGT_AMT, BEGIN_DT, CLOSE_DT FROM APP_PROJ_L WHERE NOTICE_NO = :notice_no",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "projects/detail",
        "method": "GET",
        "name": "프로젝트 상세 조회",
        "desc": "프로젝트 ID로 상세 정보 (PRIMARY KEY 활용)",
        "tags": "projects,detail",
        "req_spec": {
            "proj_id": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT * FROM APP_PROJ_L WHERE PROJ_ID = :proj_id",
        "resp_spec": {"success": True, "project": "$result"}
    },
    
    # ============ 사전규격 프로젝트 API (APP_PRCR_PROJ_L) ============
    {
        "path": "prcr-projects/recent",
        "method": "GET",
        "name": "최근 사전규격 프로젝트",
        "desc": "최근 업로드된 사전규격 프로젝트 (IX_UPLDDT 인덱스 활용)",
        "tags": "prcr,recent",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 20}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, TYPE_CD, BDGT_AMT, BEGIN_DT, CLOSE_DT, UPLD_DT FROM APP_PRCR_PROJ_L WHERE SYNC_YN = 'Y' ORDER BY UPLD_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "prcr-projects/active",
        "method": "GET",
        "name": "진행중 사전규격 프로젝트",
        "desc": "마감일이 남은 사전규격 (IX_CLOSEDT 인덱스 활용)",
        "tags": "prcr,active",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, TYPE_CD, BDGT_AMT, BEGIN_DT, CLOSE_DT FROM APP_PRCR_PROJ_L WHERE CLOSE_DT >= NOW() AND SYNC_YN = 'Y' ORDER BY CLOSE_DT ASC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    {
        "path": "prcr-projects/by-type",
        "method": "GET",
        "name": "타입별 사전규격 조회",
        "desc": "타입 코드로 필터링 (IX_TYPE_CD 인덱스 활용)",
        "tags": "prcr,filter",
        "req_spec": {
            "type_cd": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 50}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, TITLE, BDGT_AMT, BEGIN_DT, CLOSE_DT FROM APP_PRCR_PROJ_L WHERE TYPE_CD = :type_cd AND SYNC_YN = 'Y' ORDER BY CLOSE_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "projects": "$result", "count": "$result_count"}
    },
    
    # ============ 계약 관련 API (APP_CNTRCT_PROJ_L) ============
    {
        "path": "contracts/recent",
        "method": "GET",
        "name": "최근 계약 목록",
        "desc": "최근 등록된 계약 (IX_RGST_DT 인덱스 활용)",
        "tags": "contracts,recent",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 20}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT UNTY_CNTRCT_NO, CNTRCT_NM, MAIN_CORP_NM, THTM_CNTRCT_AMT, CNTRCT_DT, RGST_DT FROM APP_CNTRCT_PROJ_L ORDER BY RGST_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "contracts": "$result", "count": "$result_count"}
    },
    {
        "path": "contracts/by-bizno",
        "method": "GET",
        "name": "사업자번호로 계약 조회",
        "desc": "사업자번호로 계약 검색 (IX_BIZ_NO 인덱스 활용)",
        "tags": "contracts,search",
        "req_spec": {
            "biz_no": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT UNTY_CNTRCT_NO, CNTRCT_NM, THTM_CNTRCT_AMT, CNTRCT_DT, DMINST_NM FROM APP_CNTRCT_PROJ_L WHERE MAIN_CORP_BIZ_NO = :biz_no ORDER BY CNTRCT_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "contracts": "$result", "count": "$result_count"}
    },
    {
        "path": "contracts/by-dminst",
        "method": "GET",
        "name": "발주기관별 계약 조회",
        "desc": "발주기관 코드로 조회 (IX_DMINST_CD 인덱스 활용)",
        "tags": "contracts,agency",
        "req_spec": {
            "dminst_cd": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT UNTY_CNTRCT_NO, CNTRCT_NM, MAIN_CORP_NM, THTM_CNTRCT_AMT, CNTRCT_DT FROM APP_CNTRCT_PROJ_L WHERE DMINST_CD = :dminst_cd ORDER BY CNTRCT_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "contracts": "$result", "count": "$result_count"}
    },
    {
        "path": "contracts/by-type",
        "method": "GET",
        "name": "타입별 계약 조회",
        "desc": "계약 타입으로 필터링 (IX_TYPE 인덱스 활용)",
        "tags": "contracts,type",
        "req_spec": {
            "type": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 50}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT UNTY_CNTRCT_NO, CNTRCT_NM, MAIN_CORP_NM, THTM_CNTRCT_AMT, CNTRCT_DT FROM APP_CNTRCT_PROJ_L WHERE TYPE = :type ORDER BY CNTRCT_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "contracts": "$result", "count": "$result_count"}
    },
    
    # ============ 입찰계획 API (APP_BID_PLAN_L) ============
    {
        "path": "bid-plans/by-year",
        "method": "GET",
        "name": "연도별 입찰계획",
        "desc": "연도별 입찰계획 조회 (idx_orderYear 인덱스 활용)",
        "tags": "bidplan,year",
        "req_spec": {
            "year": {"type": "int", "required": True},
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, BIZ_NM, ORDER_INSTT_NM, ORDER_MNTH, SUM_ORDER_AMT, NTICE_DT FROM APP_BID_PLAN_L WHERE ORDER_YEAR = :year ORDER BY NTICE_DT DESC LIMIT :limit",
        "resp_spec": {"success": True, "plans": "$result", "count": "$result_count"}
    },
    {
        "path": "bid-plans/by-month",
        "method": "GET",
        "name": "월별 입찰계획",
        "desc": "특정 월의 입찰계획 (idx_orderMnth 인덱스 활용)",
        "tags": "bidplan,month",
        "req_spec": {
            "year": {"type": "int", "required": True},
            "month": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, BIZ_NM, ORDER_INSTT_NM, SUM_ORDER_AMT, NTICE_DT FROM APP_BID_PLAN_L WHERE ORDER_YEAR = :year AND ORDER_MNTH = :month ORDER BY SUM_ORDER_AMT DESC",
        "resp_spec": {"success": True, "plans": "$result", "count": "$result_count"}
    },
    {
        "path": "bid-plans/by-agency",
        "method": "GET",
        "name": "발주기관별 입찰계획",
        "desc": "발주기관 코드로 조회 (idx_orderInsttCd 인덱스 활용)",
        "tags": "bidplan,agency",
        "req_spec": {
            "agency_cd": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT PROJ_ID, BIZ_NM, ORDER_YEAR, ORDER_MNTH, SUM_ORDER_AMT, NTICE_DT FROM APP_BID_PLAN_L WHERE ORDER_INSTT_CD = :agency_cd ORDER BY ORDER_YEAR DESC, ORDER_MNTH DESC",
        "resp_spec": {"success": True, "plans": "$result", "count": "$result_count"}
    },
    
    # ============ 면허 API (APP_CORP_LCNS_L) ============
    {
        "path": "licenses/by-bizno",
        "method": "GET",
        "name": "사업자번호로 면허 조회",
        "desc": "사업자번호로 보유 면허 조회 (idx_bizno 인덱스 활용)",
        "tags": "license,bizno",
        "req_spec": {
            "biz_no": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT bizno, indstrytyNm, indstrytyCd, rgstDt, vldPrdExprtDt, indstrytyStatsNm FROM APP_CORP_LCNS_L WHERE bizno = :biz_no ORDER BY rgstDt DESC",
        "resp_spec": {"success": True, "licenses": "$result", "count": "$result_count"}
    },
    {
        "path": "licenses/by-type",
        "method": "GET",
        "name": "면허종류별 조회",
        "desc": "면허 종류 코드로 조회 (idx_indstrytyCd 인덱스 활용)",
        "tags": "license,type",
        "req_spec": {
            "type_cd": {"type": "string", "required": True},
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT bizno, indstrytyNm, rgstDt, vldPrdExprtDt, indstrytyStatsNm FROM APP_CORP_LCNS_L WHERE indstrytyCd = :type_cd AND indstrytyStatsNm = '유효' ORDER BY rgstDt DESC LIMIT :limit",
        "resp_spec": {"success": True, "licenses": "$result", "count": "$result_count"}
    },
    
    # ============ 검색 관련 API (APP_SRCH_L) ============
    {
        "path": "searches/list",
        "method": "GET",
        "name": "저장된 검색 목록",
        "desc": "회사의 저장된 검색 목록 조회",
        "tags": "search,list",
        "req_spec": {
            "cmpny_id": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT SRCH_ID, SRCH_NM, FILTER_JSON, CREA_DT, UPDT_DT FROM APP_SRCH_L WHERE CMPNY_ID = :cmpny_id ORDER BY UPDT_DT DESC",
        "resp_spec": {"success": True, "searches": "$result", "count": "$result_count"}
    },
    
    # ============ 발주기관 API (APP_CLNT_L) ============
    {
        "path": "clients/list",
        "method": "GET",
        "name": "발주기관 목록",
        "desc": "발주기관 목록 조회",
        "tags": "clients,list",
        "req_spec": {
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT CLNT_ID, CLNT_NM, CLNT_CD, CLNT_TYPE, OFCL_NM FROM APP_CLNT_L WHERE SYNC_YN = 'Y' LIMIT :limit",
        "resp_spec": {"success": True, "clients": "$result", "count": "$result_count"}
    },
    {
        "path": "clients/by-code",
        "method": "GET",
        "name": "기관코드로 조회",
        "desc": "기관 코드로 발주기관 조회 (client_code_UNIQUE 인덱스 활용)",
        "tags": "clients,code",
        "req_spec": {
            "clnt_cd": {"type": "string", "required": True}
        },
        "logic_type": "SQL",
        "logic_body": "SELECT * FROM APP_CLNT_L WHERE CLNT_CD = :clnt_cd",
        "resp_spec": {"success": True, "client": "$result"}
    },
    
    # ============ 다중 쿼리 API (MULTI_SQL) ============
    {
        "path": "company/dashboard",
        "method": "GET",
        "name": "회사 대시보드",
        "desc": "회사 정보와 사용자, 즐겨찾기 프로젝트를 한번에 조회",
        "tags": "company,dashboard,multi",
        "req_spec": {
            "cmpny_id": {"type": "string", "required": True}
        },
        "logic_type": "MULTI_SQL",
        "logic_body": json.dumps({
            "queries": [
                {"name": "company", "sql": "SELECT CMPNY_ID, CMPNY_NAME, CMPNY_BIZ_NO, CEO_NAME FROM APP_CMPNY_L WHERE CMPNY_ID = :cmpny_id"},
                {"name": "users", "sql": "SELECT USER_ID, EMAIL, FIRST_NAME, LAST_NAME FROM APP_USER_L WHERE CMPNY_ID = :cmpny_id AND DEL_YN = 'N'"},
                {"name": "favorites", "sql": "SELECT COUNT(*) as cnt FROM APP_FAVR_PROJ_L WHERE CMPNY_ID = :cmpny_id AND DEL_YN = 'N'"}
            ]
        }),
        "resp_spec": {"success": True, "data": "$result"}
    },
    {
        "path": "user/profile",
        "method": "GET",
        "name": "사용자 프로필 종합",
        "desc": "사용자 정보, 소속 회사, 저장된 검색을 한번에 조회",
        "tags": "user,profile,multi",
        "req_spec": {
            "user_id": {"type": "string", "required": True}
        },
        "logic_type": "MULTI_SQL",
        "logic_body": json.dumps({
            "queries": [
                {"name": "user", "sql": "SELECT USER_ID, EMAIL, FIRST_NAME, LAST_NAME, CMPNY_ID, DEPT FROM APP_USER_L WHERE USER_ID = :user_id"},
                {"name": "company", "sql": "SELECT CMPNY_ID, CMPNY_NAME FROM APP_CMPNY_L WHERE CMPNY_ID = (SELECT CMPNY_ID FROM APP_USER_L WHERE USER_ID = :user_id)"},
                {"name": "searches", "sql": "SELECT SRCH_ID, SRCH_NM FROM APP_SRCH_L WHERE USER_ID = :user_id"}
            ]
        }),
        "resp_spec": {"success": True, "data": "$result"}
    },
    
    # ============ 통계 API ============
    {
        "path": "stats/projects-by-type",
        "method": "GET",
        "name": "타입별 프로젝트 통계",
        "desc": "프로젝트 타입별 건수 통계",
        "tags": "stats,projects",
        "req_spec": {},
        "logic_type": "SQL",
        "logic_body": "SELECT TYPE_CD, COUNT(*) as cnt, SUM(BDGT_AMT) as total_budget FROM APP_PROJ_L WHERE USE_YN = 'Y' GROUP BY TYPE_CD ORDER BY cnt DESC",
        "resp_spec": {"success": True, "stats": "$result"}
    },
]

print(f"총 {len(SAMPLE_APIS)}개의 샘플 API 생성 시작...")

created_count = 0
for api in SAMPLE_APIS:
    try:
        # 중복 체크
        cursor.execute(
            "SELECT COUNT(*) FROM APP_API_ROUTE_L WHERE API_PATH = %s AND HTTP_MTHD = %s",
            (api["path"], api["method"])
        )
        if cursor.fetchone()[0] > 0:
            print(f"  ⏭️  {api['method']} /api/{api['path']} - 이미 존재")
            continue
        
        # 라우트 생성
        route_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO APP_API_ROUTE_L (ROUTE_ID, API_PATH, HTTP_MTHD, API_NAME, API_DESC, TAGS, USE_YN, DEL_YN, CREA_BY)
            VALUES (%s, %s, %s, %s, %s, %s, 'Y', 'N', 'system')
        """, (route_id, api["path"], api["method"], api["name"], api["desc"], api["tags"]))
        
        # 버전 생성
        version_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO APP_API_VERSION_H (VERSION_ID, ROUTE_ID, VERSION_NO, CRNT_YN, REQ_SPEC, LOGIC_TYPE, LOGIC_BODY, RESP_SPEC, CHG_NOTE, CREA_BY)
            VALUES (%s, %s, 1, 'Y', %s, %s, %s, %s, '초기 버전', 'system')
        """, (
            version_id,
            route_id,
            json.dumps(api["req_spec"]),
            api["logic_type"],
            api["logic_body"],
            json.dumps(api["resp_spec"])
        ))
        
        created_count += 1
        print(f"  ✅ {api['method']} /api/{api['path']} - {api['name']}")
        
    except Exception as e:
        print(f"  ❌ {api['method']} /api/{api['path']} - 오류: {e}")

conn.commit()
conn.close()

print(f"\n🎉 완료! {created_count}개의 API가 생성되었습니다.")

