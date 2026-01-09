# Prompt API Engine

MySQL 테이블 행 추가/수정만으로 API를 생성하고 관리하는 **동적 API 엔진**입니다.

## 🎯 핵심 컨셉

- **코드 배포 없이 API 생성**: DB에 행을 추가하면 즉시 새 API 엔드포인트 활성화
- **다중 데이터소스 지원**: MySQL, BigQuery, OpenSearch 등 다양한 데이터소스
- **복잡한 쿼리 지원**: 다중 쿼리, 파이프라인 처리
- **버전 관리**: 모든 변경 사항을 버전으로 관리, 언제든 롤백 가능
- **감사 로그**: 모든 변경 이력을 자동 기록
- **보안**: SQL Injection 방지, Soft Delete, API 키 인증
- **🧠 AI 기능**: LLM 기반 API 생성, SQL 최적화, 테스트 케이스 생성, 자연어 API 호출

## 📁 프로젝트 구조

```
prompt-api-engine/
├── app/
│   ├── core/           # 핵심 설정 (config, database)
│   ├── models/         # SQLAlchemy 모델
│   ├── routers/        # FastAPI 라우터
│   ├── schemas/        # Pydantic 스키마
│   ├── services/       # 비즈니스 로직 (Executor, Validator)
│   └── main.py         # 애플리케이션 엔트리포인트
├── scripts/            # 유틸리티 스크립트
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## 🚀 시작하기

### 1. 환경 설정

```powershell
# 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\Activate

# 의존성 설치
pip install -r requirements.txt

# BigQuery 사용 시 (선택)
pip install google-cloud-bigquery
```

### 2. 환경 변수 설정

`.env` 파일에 다음 설정 추가:

```env
# MySQL
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DB=cliwant
MYSQL_PORT=3306

# 관리자 API 키
API_KEY=your-admin-api-key

# BigQuery (선택)
GCP_PROJECT_ID=your-project-id
GCP_CREDENTIALS_PATH=gcloud-key.json

# OpenSearch (선택)
OPENSEARCH_HOST=https://localhost:9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=admin
```

### 3. 데이터베이스 초기화

```powershell
# 테이블 생성
python scripts/create_tables.py

# 샘플 API 생성 (30개)
python scripts/insert_sample_apis.py
```

### 4. 서버 실행

```powershell
uvicorn app.main:app --reload
```

**접속 URL:**
| URL | 설명 |
|-----|------|
| http://localhost:8000 | API Tester UI (메인) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/admin/policy | Immutable 정책 조회 |

## 📝 지원 로직 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| `SQL` | 단일 MySQL 쿼리 | `SELECT * FROM users WHERE id = :id` |
| `MULTI_SQL` | 다중 쿼리 순차 실행 | 여러 테이블 조인 결과 조합 |
| `PIPELINE` | 여러 로직 파이프라인 연결 | SQL → 변환 → 응답 |
| `BIGQUERY` | Google BigQuery 쿼리 | 대용량 데이터 분석 |
| `OPENSEARCH` | OpenSearch 검색 쿼리 | 전문 검색, 로그 분석 |
| `PYTHON_EXPR` | Python 표현식 (제한적) | 간단한 데이터 변환 |
| `HTTP_CALL` | 외부 API 호출 | 타 서비스 연동 |
| `STATIC_RESPONSE` | 정적 JSON 응답 | 목업, 테스트용 |

## 🗄️ DB 테이블 구조

### APP_API_ROUTE_L (API 카탈로그)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| ROUTE_ID | VARCHAR(50) | PK |
| API_PATH | VARCHAR(255) | API 경로 |
| HTTP_MTHD | VARCHAR(10) | HTTP 메서드 |
| API_NAME | VARCHAR(255) | API 이름 |
| USE_YN | CHAR(1) | 사용 여부 (Y/N) |
| DEL_YN | CHAR(1) | 삭제 여부 (Y/N) |

### APP_API_VERSION_H (실제 동작 로직)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| VERSION_ID | VARCHAR(50) | PK |
| ROUTE_ID | VARCHAR(50) | FK → APP_API_ROUTE_L |
| VERSION_NO | INT | 버전 번호 |
| CRNT_YN | CHAR(1) | 현재 버전 여부 |
| REQ_SPEC | JSON | 입력 파라미터 검증 규칙 |
| LOGIC_TYPE | VARCHAR(50) | 로직 타입 |
| LOGIC_BODY | TEXT | 실행할 로직 |
| RESP_SPEC | JSON | 응답 매핑 규칙 |

## 📖 API 사용 예시

### 단일 SQL 쿼리

```json
{
  "logic_type": "SQL",
  "logic_body": "SELECT * FROM APP_USER_L WHERE CMPNY_ID = :cmpny_id",
  "request_spec": {
    "cmpny_id": {"type": "string", "required": true}
  }
}
```

### 다중 SQL 쿼리 (MULTI_SQL)

```json
{
  "logic_type": "MULTI_SQL",
  "logic_body": {
    "queries": [
      {"name": "users", "sql": "SELECT * FROM APP_USER_L WHERE CMPNY_ID = :cmpny_id"},
      {"name": "company", "sql": "SELECT * FROM APP_CMPNY_L WHERE CMPNY_ID = :cmpny_id"}
    ]
  }
}
```

### 파이프라인 (PIPELINE)

```json
{
  "logic_type": "PIPELINE",
  "logic_body": {
    "steps": [
      {"type": "SQL", "body": "SELECT COUNT(*) as cnt FROM APP_USER_L", "output": "user_count"},
      {"type": "STATIC_RESPONSE", "body": "{\"total_users\": $params.user_count}"}
    ]
  }
}
```

### BigQuery

```json
{
  "logic_type": "BIGQUERY",
  "logic_body": "SELECT * FROM `project.dataset.table` WHERE date = @date LIMIT @limit",
  "request_spec": {
    "date": {"type": "string", "required": true},
    "limit": {"type": "int", "default": 100}
  }
}
```

### OpenSearch

```json
{
  "logic_type": "OPENSEARCH",
  "logic_body": {
    "index": "logs-*",
    "body": {
      "query": {"match": {"message": "$params.keyword"}},
      "size": 100
    }
  }
}
```

## 🧠 AI 기능 (v1.8.0+)

Vertex AI Gemini 2.5/3.0을 활용한 강력한 AI 기능들:

### 💬 자연어 API 호출

자연어로 질문하면 AI가 적합한 API를 찾아 실행합니다.

```bash
POST /schema/ai/chat

{
  "question": "최근 가입한 사용자 10명 보여줘",
  "auto_execute": true,
  "model": "vertex_ai/gemini-2.5-flash"
}
```

**응답 예시:**
- 선택된 API: `GET /api/users/list`
- 추출된 파라미터: `{"limit": 10}`
- 신뢰도: 95%
- 자동 실행 결과 포함

### 🔧 SQL 최적화 제안

SQL 쿼리를 분석하여 성능 개선 방안을 제안합니다.

```bash
POST /schema/ai/optimize-sql

{
  "sql_query": "SELECT * FROM APP_USER_L WHERE CMPNY_ID = :cmpny_id",
  "table_names": ["APP_USER_L"],
  "execution_time_ms": 500,
  "model": "vertex_ai/gemini-2.5-flash"
}
```

**제안 항목:**
- 인덱스 활용 최적화
- 쿼리 재작성 추천
- JOIN 순서 최적화
- 새 인덱스 생성 권장

### 🧪 테스트 케이스 자동 생성

API 정의를 분석하여 포괄적인 테스트 케이스를 생성합니다.

```bash
POST /schema/ai/generate-test-cases

{
  "route_id": "api-route-id",
  "model": "vertex_ai/gemini-2.5-flash"
}
```

**생성 케이스 유형:**
| 유형 | 설명 | 최소 개수 |
|------|------|----------|
| Positive | 정상 동작 케이스 | 3개 |
| Negative | 에러 케이스 (필수값 누락 등) | 2개 |
| Boundary | 경계값 테스트 | 2개 |
| Performance | 성능 테스트 | 1개 |

---

## 🔒 보안 기능

| 기능 | 설명 |
|------|------|
| **Immutable 정책** | API 정의는 추가만 가능, 수정/삭제 불가 |
| **SQL Injection 방지** | DROP, TRUNCATE 등 위험 키워드 차단, 파라미터 바인딩 강제 |
| **감사 로그** | 모든 변경 이력 기록 (누가, 언제, 무엇을) |
| **버전 관리** | 기존 버전 보존, 언제든 이전 버전으로 전환 가능 |
| **API 키 인증** | 관리자 API 접근 제어 |

### ⚠️ 보안 진단 보고서

자연어 SQL 쿼리 생성 기능에 대한 상세 보안 분석은 **[SECURITY_ASSESSMENT.md](./SECURITY_ASSESSMENT.md)** 문서를 참조하세요.

**주요 권고사항:**
| 우선순위 | 항목 | 상태 |
|----------|------|------|
| 🔴 P0 | 인증/권한 시스템 추가 | 개선 필요 |
| 🔴 P0 | 읽기 전용 DB 사용자 분리 | 개선 필요 |
| 🔴 P0 | CORS 설정 강화 | 개선 필요 |
| 🟠 P1 | 민감 컬럼 서버 측 검증 | 개선 권장 |
| 🟠 P1 | Prompt Injection 방어 | 개선 권장 |
| 🟡 P2 | Rate Limiting | 개선 권장 |
| 🟡 P2 | 감사 로그 강화 | 개선 권장 |

> ⚠️ **프로덕션 배포 전 최소한 P0 항목들을 해결하세요.**

### 🔒 Immutable 정책

API 정의 데이터의 무결성을 보장하기 위해 **추가 전용(Append-only)** 정책을 적용합니다:

| 리소스 | 허용 작업 | 금지 작업 |
|--------|----------|----------|
| `APP_API_ROUTE_L` | CREATE, ACTIVATE, DEACTIVATE | UPDATE, DELETE |
| `APP_API_VERSION_H` | CREATE, SET_CURRENT | UPDATE, DELETE |
| `APP_API_AUDIT_H` | CREATE (자동) | UPDATE, DELETE |

**장점:**
- ✅ 실수로 인한 API 삭제 완전 방지
- ✅ 모든 변경 이력 영구 보존
- ✅ 언제든 이전 버전으로 즉시 전환
- ✅ 감사 추적 용이

## 🔧 관리자 API (Immutable)

⚠️ **주의**: API 정의는 추가만 가능하며 수정/삭제할 수 없습니다.

```bash
# API 목록 조회 (공개)
curl http://localhost:8000/admin/routes

# 새 API 생성 (API 키 필요)
curl -X POST http://localhost:8000/admin/routes \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"path": "my-api", "method": "GET", "name": "My API"}'

# 새 버전 생성 (API 키 필요)
curl -X POST http://localhost:8000/admin/routes/{route_id}/versions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "logic_type": "SQL",
    "logic_body": "SELECT * FROM users LIMIT :limit",
    "request_spec": {"limit": {"type": "int", "default": 10}},
    "change_note": "초기 버전"
  }'

# 상태 변경 (활성화/비활성화만 가능)
curl -X PATCH http://localhost:8000/admin/routes/{route_id}/status \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false, "reason": "임시 비활성화"}'

# 현재 버전 변경
curl -X PATCH http://localhost:8000/admin/routes/{route_id}/versions/1/activate \
  -H "X-API-Key: your-api-key"

# 정책 조회
curl http://localhost:8000/admin/policy
```

## 📊 포함된 샘플 API (33개)

| 카테고리 | API 수 | 예시 |
|----------|--------|------|
| 사용자 | 3 | `/api/users/list`, `/api/users/by-company` |
| 회사 | 3 | `/api/companies/list`, `/api/companies/by-bizno` |
| 프로젝트 | 6 | `/api/projects/recent`, `/api/projects/active` |
| 사전규격 | 3 | `/api/prcr-projects/recent` |
| 계약 | 4 | `/api/contracts/recent`, `/api/contracts/by-bizno` |
| 입찰계획 | 3 | `/api/bid-plans/by-year` |
| 면허 | 2 | `/api/licenses/by-bizno` |
| 검색 | 1 | `/api/searches/list` |
| 발주기관 | 2 | `/api/clients/list` |
| 다중쿼리 | 2 | `/api/company/dashboard` |
| 통계 | 1 | `/api/stats/projects-by-type` |
| 기본 | 3 | `/api/hello`, `/api/echo`, `/api/users` |

## 📄 라이선스

MIT License
