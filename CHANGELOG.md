# Changelog

이 문서는 Prompt API Engine의 모든 주요 변경 사항을 기록합니다.

## [1.6.0] - 2026-01-09 15:30

### 🛡️ 에러 핸들링 고도화 & 로깅 시스템 개선

#### 에러 핸들링 고도화

**커스텀 예외 클래스 추가** (`app/core/exceptions.py`)
- `ApiEngineError` - 기본 예외 클래스
- `ValidationError` - 유효성 검증 오류
- `NotFoundError` - 리소스 미발견
- `DuplicateError` - 중복 데이터
- `AuthenticationError` - 인증 오류
- `AuthorizationError` - 권한 오류
- `ExecutionError` - 로직 실행 오류
- `SecurityError` - 보안 위반
- `DatabaseError` - DB 오류
- `ExternalServiceError` - 외부 서비스 오류
- `RateLimitError` - 요청 제한
- `ImmutablePolicyError` - 불변 정책 위반

**사용자 친화적 에러 응답**
- 에러 코드별 한글 메시지 매핑
- 구조화된 에러 응답 형식
- 디버그 모드에서 상세 정보 제공

**예외 핸들러 개선**
- `RequestValidationError` 핸들러 추가
- `PydanticValidationError` 핸들러 추가
- `SQLAlchemyError` 핸들러 추가
- 전역 catch-all 핸들러 개선

#### 로깅 시스템 개선 (`app/core/logging.py`)

**JSON 구조화 로깅**
- `JSONFormatter` - JSON 형식 로그 출력
- 타임스탬프, 레벨, 로거명, 메시지 포함
- 요청 ID, HTTP 메서드, 경로, 상태 코드, 응답 시간 추적

**요청/응답 로깅 미들웨어**
- `RequestLoggingMiddleware` - 모든 요청/응답 자동 로깅
- 요청 ID 자동 생성 및 헤더 추가 (`X-Request-ID`)
- 응답 시간 측정 및 헤더 추가 (`X-Response-Time`)
- 클라이언트 IP, User-Agent 추적

**API 호출 로거**
- `APICallLogger` - API 실행 로깅 유틸리티
- SQL 실행 로깅
- 성능 메트릭 수집

**로그 예시**
```json
{
  "timestamp": "2026-01-09T06:24:07.012887Z",
  "level": "INFO",
  "logger": "api_engine.request",
  "message": "← 200 (532.36ms)",
  "request_id": "b1d4a681",
  "method": "GET",
  "path": "/admin/routes",
  "status_code": 200,
  "duration_ms": 532.36,
  "client_ip": "127.0.0.1"
}
```

---

## [1.5.0] - 2026-01-02 20:00

### 🧪 테스트 필수화 & LLM UI 고도화 & Response 뷰 개선

#### API 생성/버전 추가 시 테스트 필수화
- 신규 API 생성 전 SQL 테스트 통과 필수
- 버전 추가 전 SQL 테스트 통과 필수
- 테스트 결과 (성공/실패, 행 수, 실행 시간) 표시
- 테스트 통과 전까지 생성 버튼 비활성화

#### SQL 테스트 API
- `POST /schema/test-sql` - SQL 쿼리 테스트 실행
- 위험 쿼리 자동 차단 (DROP, DELETE, ALTER 등)
- 실행 시간, 결과 행 수, 샘플 데이터 반환

#### LLM UI 대폭 개선

**테이블 스키마 상세 표시**
- 선택한 테이블의 전체 컬럼 목록
- 각 컬럼별 실제 데이터 샘플 5개씩 표시
- 컬럼 타입, 키 정보, 샘플 값 한눈에 확인

**다양한 LLM 모델 지원 (40+ 모델)**

| 프로바이더 | 모델 | 인증 방식 |
|-----------|------|----------|
| OpenAI | GPT-4o, GPT-4o Mini, O1 등 | API Key |
| Anthropic | Claude 3.5 Sonnet/Haiku, Claude 3 Opus 등 | API Key |
| Google | Gemini 1.5 Pro/Flash, Gemini 2.0 | API Key |
| Vertex AI | Gemini, Claude (Google Cloud) | Service Account JSON |
| Azure | GPT-4o, GPT-4 (Azure OpenAI) | API Key + Endpoint |
| AWS Bedrock | Claude, Titan | AWS Credentials |
| Mistral | Mistral Large/Medium/Small, Codestral | API Key |
| Groq | Llama 3.3 70B, Mixtral | API Key |
| Together AI | Llama, Mixtral | API Key |
| Ollama | Llama 3.2, Mistral, CodeLlama (로컬) | 없음 |
| OpenRouter | 모든 주요 모델 | API Key |

**인증 설정 UI**
- 모델 선택 시 해당 인증 방식 자동 표시
- Vertex AI: gcloud-key.json 내용 직접 붙여넣기 지원
- Azure: Endpoint URL + API Key
- AWS Bedrock: Access Key + Secret Key

**LLM 파라미터 설정**
- Temperature (0~2)
- Max Tokens (100~8000)
- Top P (0~1)

#### Response 뷰 개선

**JSON/Table 뷰 전환**
- JSON 뷰: 구문 강조된 JSON
- Table 뷰: 데이터를 테이블 형식으로 표시

**다중 리스트 테이블 렌더링**
- 중첩된 배열 데이터도 각각의 테이블로 표시
- 복잡한 API 응답을 직관적으로 확인

---

## [1.4.0] - 2026-01-02 18:30

### 🤖 LLM 기반 API 자동 생성 & 샘플 파라미터

#### 새로운 기능

**LLM 기반 API 생성**
- LiteLLM 통합으로 다양한 LLM 모델 지원 (GPT-4o, Claude 3.5, Gemini 등)
- DB 테이블 선택 후 자연어로 의도 입력 → AI가 API 정의 자동 생성
- 생성된 스펙 미리보기 및 바로 API 생성 가능

**DB 스키마 조회 API**
- `GET /schema/tables` - 전체 테이블 목록 조회
- `GET /schema/tables/{name}` - 테이블 상세 (컬럼, 인덱스, 샘플 데이터)
- `GET /schema/llm/models` - 지원 LLM 모델 목록
- `POST /schema/llm/generate-api` - LLM으로 API 스펙 생성

**샘플 파라미터 관리**
- `APP_API_VERSION_H.SMPL_PARAMS` 컬럼 추가
- API 테스터에서 "샘플값 채우기" 버튼으로 테스트 편의성 향상
- 신규 API 생성/버전 추가 시 샘플 파라미터 설정 가능

#### UI 개선
- 새로고침 버튼 추가 (API 목록 갱신)
- LLM 생성 탭 추가 (테이블 선택 → 스키마 미리보기 → AI 생성)
- 샘플 파라미터 표시 및 자동 채우기 기능

#### 의존성 추가
- `litellm==1.30.0`

---

## [1.3.0] - 2026-01-02 16:30

### 🔒 Immutable 정책 적용 및 API 관리 UI

#### Immutable 정책
API 정의 데이터의 무결성 보장을 위해 **추가 전용(Append-only)** 정책 적용:

| 리소스 | 허용 | 금지 |
|--------|------|------|
| `APP_API_ROUTE_L` | CREATE, ACTIVATE, DEACTIVATE | UPDATE, DELETE |
| `APP_API_VERSION_H` | CREATE, SET_CURRENT | UPDATE, DELETE |
| `APP_API_AUDIT_H` | CREATE (자동) | UPDATE, DELETE |

**장점:**
- 실수로 인한 API 삭제 완전 방지
- 모든 변경 이력 영구 보존
- 언제든 이전 버전으로 즉시 전환 가능
- 감사 추적 용이

#### 프론트엔드 API 관리 기능
- **새 API 추가 모달**: 라우트 + 초기 버전을 한 번에 생성
- **버전 추가 탭**: 선택한 API에 새 버전 추가 (기존 버전 기반)
- **상태 표시**: 활성/비활성 API 구분 표시
- **Immutable 배지**: UI에서 정책 안내

#### 백엔드 변경사항
- `PUT /admin/routes/{id}` 제거 (수정 불가)
- `DELETE /admin/routes/{id}` 제거 (삭제 불가)
- `PATCH /admin/routes/{id}/status` 추가 (상태 변경만 허용)
- `POST /admin/routes/{id}/versions` 추가 (새 버전 생성)
- `PATCH /admin/routes/{id}/versions/{v}/activate` 추가 (현재 버전 설정)
- `GET /admin/policy` 추가 (정책 안내 API)

#### 버전 넘버링
- 정수 자동 증가: 1, 2, 3, ...
- 새 버전 생성 시 자동으로 현재 버전(CRNT_YN='Y')으로 설정

---

## [1.2.0] - 2026-01-02 15:45

### 🎨 API Tester UI 추가

#### 새로운 기능
- **API Tester UI**: 브라우저에서 모든 API를 테스트할 수 있는 모던한 UI 추가
  - 사이드바에서 등록된 API 33개 목록 확인
  - API 선택 시 파라미터 자동 표시
  - 요청 전송 및 응답 확인 (JSON 구문 강조)
  - 검색 기능으로 빠르게 API 찾기
  
- **API Metadata 탭**: 선택한 API의 상세 메타데이터 표시
  - `APP_API_ROUTE_L` 테이블 정보 (라우트 설정)
  - `APP_API_VERSION_H` 테이블 정보 (현재 버전 로직)
  - `APP_API_AUDIT_H` 테이블 정보 (변경 이력 최근 10건)
  
- **접속 URL**:
  - API Tester: `http://localhost:8000` 또는 `/tester`
  - Swagger UI: `/docs`
  - ReDoc: `/redoc`

#### 공개 API 엔드포인트
다음 엔드포인트는 API 키 없이 조회 가능:
- `GET /admin/routes` - API 목록 조회
- `GET /admin/routes/{id}` - API 상세 조회
- `GET /admin/routes/{id}/versions` - 버전 목록 조회
- `GET /admin/routes/{id}/versions/{version}` - 버전 상세 조회
- `GET /admin/routes/{id}/audit-logs` - 감사 로그 조회

---

## [1.0.0] - 2026-01-02 14:00

### 🎉 최초 릴리스

#### 핵심 기능
- **동적 API 엔진**: MySQL 테이블 행 추가/수정만으로 API 생성/수정
- **버전 관리**: 모든 API 변경 이력 보존, 롤백 지원
- **감사 로그**: CREATE, UPDATE, DELETE, RESTORE, ROLLBACK 등 모든 작업 기록

#### 지원 로직 타입
- `SQL`: MySQL 쿼리 실행 (파라미터 바인딩)
- `PYTHON_EXPR`: 간단한 Python 표현식 실행
- `HTTP_CALL`: 외부 API 호출
- `STATIC_RESPONSE`: 정적 JSON 응답

#### 보안 기능
- SQL Injection 방지 (위험 키워드 차단, 파라미터 바인딩 강제)
- Soft Delete (실수로 인한 삭제 방지)
- API 키 인증 (관리자 API)

#### 테이블 구조
- `APP_API_ROUTE_L`: API 라우트 정의
- `APP_API_VERSION_H`: API 버전 히스토리
- `APP_API_AUDIT_H`: 감사 로그

---

## [1.1.0] - 2026-01-02 15:00

### 🚀 고도화 업데이트

#### 새로운 로직 타입
- `MULTI_SQL`: 다중 쿼리 순차 실행 (이전 쿼리 결과를 다음 쿼리의 파라미터로 사용 가능)
- `PIPELINE`: 여러 로직을 파이프라인으로 연결 (SQL → 변환 → 응답)
- `BIGQUERY`: Google BigQuery 쿼리 실행 (파라미터 바인딩 지원)
- `OPENSEARCH`: OpenSearch 쿼리 실행 (전문 검색, 로그 분석)

#### 샘플 API 30개 추가
인덱스 최적화된 쿼리로 구성:

**사용자 관련 (3개)**
- `GET /api/users/list` - 사용자 목록 (IX_CREA_DT 인덱스)
- `GET /api/users/by-company` - 회사별 사용자 (IX_CMPNY_ID 인덱스)
- `GET /api/users/detail` - 사용자 상세 (PRIMARY KEY)

**회사 관련 (3개)**
- `GET /api/companies/list` - 회사 목록
- `GET /api/companies/by-bizno` - 사업자번호 검색 (BIZ_NO 인덱스)
- `GET /api/companies/detail` - 회사 상세

**프로젝트 관련 (6개)**
- `GET /api/projects/recent` - 최근 프로젝트 (IX_UPLDDT 인덱스)
- `GET /api/projects/by-type` - 타입별 필터 (IX_TYPE_CD 인덱스)
- `GET /api/projects/by-channel` - 채널별 필터 (IX_CHANNEL_TYPE 인덱스)
- `GET /api/projects/active` - 진행중 프로젝트 (IX_CLOSE_DT 인덱스)
- `GET /api/projects/by-notice` - 공고번호 검색 (IX_NOTICE 인덱스)
- `GET /api/projects/detail` - 프로젝트 상세

**사전규격 프로젝트 (3개)**
- `GET /api/prcr-projects/recent` - 최근 사전규격
- `GET /api/prcr-projects/active` - 진행중 사전규격
- `GET /api/prcr-projects/by-type` - 타입별 필터

**계약 관련 (4개)**
- `GET /api/contracts/recent` - 최근 계약 (IX_RGST_DT 인덱스)
- `GET /api/contracts/by-bizno` - 사업자번호 검색 (IX_BIZ_NO 인덱스)
- `GET /api/contracts/by-dminst` - 발주기관별 (IX_DMINST_CD 인덱스)
- `GET /api/contracts/by-type` - 타입별 (IX_TYPE 인덱스)

**입찰계획 관련 (3개)**
- `GET /api/bid-plans/by-year` - 연도별 (idx_orderYear 인덱스)
- `GET /api/bid-plans/by-month` - 월별 (idx_orderMnth 인덱스)
- `GET /api/bid-plans/by-agency` - 발주기관별 (idx_orderInsttCd 인덱스)

**면허 관련 (2개)**
- `GET /api/licenses/by-bizno` - 사업자번호 검색 (idx_bizno 인덱스)
- `GET /api/licenses/by-type` - 면허종류별 (idx_indstrytyCd 인덱스)

**기타 (6개)**
- `GET /api/searches/list` - 저장된 검색 목록
- `GET /api/clients/list` - 발주기관 목록
- `GET /api/clients/by-code` - 기관코드 검색
- `GET /api/company/dashboard` - 회사 대시보드 (MULTI_SQL)
- `GET /api/user/profile` - 사용자 프로필 종합 (MULTI_SQL)
- `GET /api/stats/projects-by-type` - 타입별 통계

#### 기술 개선사항
- datetime 객체 자동 직렬화
- Decimal 타입 자동 변환
- 다중 데이터소스 연결 지원
- 파이프라인 내 결과 전달 기능

---

## 버전 형식

이 프로젝트는 [Semantic Versioning](https://semver.org/)을 따릅니다.

- **MAJOR**: 호환되지 않는 API 변경
- **MINOR**: 하위 호환되는 기능 추가
- **PATCH**: 하위 호환되는 버그 수정

