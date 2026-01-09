"""
LLM 서비스
LiteLLM을 사용하여 다양한 LLM 모델을 호출합니다.
API 생성을 위한 프롬프트 엔지니어링을 담당합니다.
"""
import json
import os
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# gcloud-key.json 경로 자동 설정
GCLOUD_KEY_PATH = Path(__file__).parent.parent.parent / "gcloud-key.json"
if GCLOUD_KEY_PATH.exists() and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GCLOUD_KEY_PATH)
    print(f"✅ Vertex AI 인증 설정됨: {GCLOUD_KEY_PATH}")


class LLMConfig(BaseModel):
    """LLM 설정"""
    model: str = "vertex_ai/gemini-2.5-flash"  # 기본값: Vertex AI Gemini 2.5 Flash
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    # 인증 설정
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    vertex_credentials: Optional[str] = None  # gcloud-key.json 내용
    vertex_project: str = "cliwant-403702"  # 프로젝트 ID
    vertex_location: str = "us-central1"  # 리전


class TableSchema(BaseModel):
    """테이블 스키마 정보"""
    table_name: str
    columns: list[dict]
    indexes: list[dict]
    sample_data: list[dict]


class ApiGenerationRequest(BaseModel):
    """API 생성 요청"""
    user_intent: str
    tables: list[TableSchema]
    method: str = "GET"


class GeneratedApiSpec(BaseModel):
    """생성된 API 스펙"""
    path: str
    method: str
    name: str
    description: str
    tags: Optional[str] = None
    logic_type: str
    logic_body: str
    request_spec: dict
    response_spec: Optional[dict] = None
    sample_params: dict
    change_note: str


# LiteLLM 지원 모델 목록 (주요 프로바이더) - Vertex AI를 먼저 배치
# Vertex AI Gemini는 2.5 이상 버전만 사용 가능 (2.5 ~ 3.0)
SUPPORTED_MODELS = [
    # Vertex AI (Google Cloud) - Gemini 2.5+ 전용, gcloud-key.json 자동 인증
    {"id": "vertex_ai/gemini-2.5-flash", "name": "✨ Gemini 2.5 Flash (Vertex)", "provider": "vertex_ai", "auth": "vertex", "default": True},
    {"id": "vertex_ai/gemini-2.5-pro", "name": "🚀 Gemini 2.5 Pro (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/gemini-2.5-flash-preview-05-20", "name": "Gemini 2.5 Flash Preview (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/gemini-2.5-pro-preview-05-06", "name": "Gemini 2.5 Pro Preview (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    # Gemini 3.0 (향후 출시 예정)
    {"id": "vertex_ai/gemini-3.0-flash", "name": "⚡ Gemini 3.0 Flash (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/gemini-3.0-pro", "name": "🌟 Gemini 3.0 Pro (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    # Vertex AI Claude (non-Gemini)
    {"id": "vertex_ai/claude-3-5-sonnet@20241022", "name": "Claude 3.5 Sonnet (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/claude-3-5-haiku@20241022", "name": "Claude 3.5 Haiku (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    
    # Google AI (Gemini) - API Key 방식
    {"id": "gemini/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "google", "auth": "api_key"},
    {"id": "gemini/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "google", "auth": "api_key"},
    {"id": "gemini/gemini-2.5-flash-preview-05-20", "name": "Gemini 2.5 Flash Preview", "provider": "google", "auth": "api_key"},
    
    # OpenAI
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "auth": "api_key"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "auth": "api_key"},
    {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai", "auth": "api_key"},
    {"id": "gpt-4", "name": "GPT-4", "provider": "openai", "auth": "api_key"},
    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai", "auth": "api_key"},
    {"id": "o1-preview", "name": "O1 Preview", "provider": "openai", "auth": "api_key"},
    {"id": "o1-mini", "name": "O1 Mini", "provider": "openai", "auth": "api_key"},
    
    # Anthropic
    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "auth": "api_key"},
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "provider": "anthropic", "auth": "api_key"},
    {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "anthropic", "auth": "api_key"},
    {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "anthropic", "auth": "api_key"},
    {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "provider": "anthropic", "auth": "api_key"},
    
    # Azure OpenAI
    {"id": "azure/gpt-4o", "name": "GPT-4o (Azure)", "provider": "azure", "auth": "azure"},
    {"id": "azure/gpt-4", "name": "GPT-4 (Azure)", "provider": "azure", "auth": "azure"},
    {"id": "azure/gpt-35-turbo", "name": "GPT-3.5 Turbo (Azure)", "provider": "azure", "auth": "azure"},
    
    # AWS Bedrock
    {"id": "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet (Bedrock)", "provider": "bedrock", "auth": "aws"},
    {"id": "bedrock/anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku (Bedrock)", "provider": "bedrock", "auth": "aws"},
    {"id": "bedrock/amazon.titan-text-express-v1", "name": "Titan Text Express (Bedrock)", "provider": "bedrock", "auth": "aws"},
    
    # Mistral
    {"id": "mistral/mistral-large-latest", "name": "Mistral Large", "provider": "mistral", "auth": "api_key"},
    {"id": "mistral/mistral-medium-latest", "name": "Mistral Medium", "provider": "mistral", "auth": "api_key"},
    {"id": "mistral/mistral-small-latest", "name": "Mistral Small", "provider": "mistral", "auth": "api_key"},
    {"id": "mistral/codestral-latest", "name": "Codestral", "provider": "mistral", "auth": "api_key"},
    
    # Groq
    {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B (Groq)", "provider": "groq", "auth": "api_key"},
    {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B (Groq)", "provider": "groq", "auth": "api_key"},
    {"id": "groq/mixtral-8x7b-32768", "name": "Mixtral 8x7B (Groq)", "provider": "groq", "auth": "api_key"},
    
    # Together AI
    {"id": "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "name": "Llama 3.1 70B (Together)", "provider": "together_ai", "auth": "api_key"},
    {"id": "together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1", "name": "Mixtral 8x7B (Together)", "provider": "together_ai", "auth": "api_key"},
    
    # Ollama (로컬)
    {"id": "ollama/llama3.2", "name": "Llama 3.2 (Ollama)", "provider": "ollama", "auth": "none"},
    {"id": "ollama/mistral", "name": "Mistral (Ollama)", "provider": "ollama", "auth": "none"},
    {"id": "ollama/codellama", "name": "CodeLlama (Ollama)", "provider": "ollama", "auth": "none"},
    
    # OpenRouter
    {"id": "openrouter/openai/gpt-4o", "name": "GPT-4o (OpenRouter)", "provider": "openrouter", "auth": "api_key"},
    {"id": "openrouter/anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet (OpenRouter)", "provider": "openrouter", "auth": "api_key"},
    {"id": "openrouter/google/gemini-pro-1.5", "name": "Gemini 1.5 Pro (OpenRouter)", "provider": "openrouter", "auth": "api_key"},
]

# 인증 방식 설명
AUTH_METHODS = {
    "api_key": {
        "name": "API Key",
        "description": "API 키를 직접 입력합니다.",
        "fields": [{"name": "api_key", "label": "API Key", "type": "password", "required": True}]
    },
    "vertex": {
        "name": "Google Cloud (Vertex AI)",
        "description": "Google Cloud 서비스 계정 JSON 키를 사용합니다.",
        "fields": [
            {"name": "vertex_credentials", "label": "Service Account JSON", "type": "textarea", "required": True},
            {"name": "vertex_project", "label": "Project ID", "type": "text", "required": True},
            {"name": "vertex_location", "label": "Location", "type": "text", "required": False, "default": "us-central1"}
        ]
    },
    "azure": {
        "name": "Azure OpenAI",
        "description": "Azure OpenAI 엔드포인트와 API 키를 사용합니다.",
        "fields": [
            {"name": "api_key", "label": "API Key", "type": "password", "required": True},
            {"name": "api_base", "label": "Endpoint URL", "type": "text", "required": True},
            {"name": "api_version", "label": "API Version", "type": "text", "required": False, "default": "2024-02-01"}
        ]
    },
    "aws": {
        "name": "AWS Bedrock",
        "description": "AWS 자격 증명을 사용합니다.",
        "fields": [
            {"name": "aws_access_key_id", "label": "Access Key ID", "type": "text", "required": True},
            {"name": "aws_secret_access_key", "label": "Secret Access Key", "type": "password", "required": True},
            {"name": "aws_region", "label": "Region", "type": "text", "required": False, "default": "us-east-1"}
        ]
    },
    "none": {
        "name": "인증 불필요",
        "description": "로컬 모델 (Ollama 등)",
        "fields": [{"name": "api_base", "label": "API Base URL", "type": "text", "required": False, "default": "http://localhost:11434"}]
    }
}


def get_supported_models() -> list[dict]:
    """지원되는 LLM 모델 목록 반환"""
    return SUPPORTED_MODELS


def get_auth_methods() -> dict:
    """인증 방식 목록 반환"""
    return AUTH_METHODS


def get_providers() -> list[dict]:
    """프로바이더 목록 반환"""
    providers = {}
    for model in SUPPORTED_MODELS:
        p = model["provider"]
        if p not in providers:
            providers[p] = {"id": p, "auth": model["auth"], "models": []}
        providers[p]["models"].append(model)
    return list(providers.values())


def _build_system_prompt() -> str:
    """시스템 프롬프트 생성"""
    return """당신은 MySQL API 생성 전문가입니다. 사용자의 의도와 테이블 스키마를 분석하여 최적의 API 정의를 생성합니다.

생성해야 할 JSON 구조:
{
  "path": "API 경로 (예: users/list, projects/by-type)",
  "method": "HTTP 메서드 (GET, POST, PUT, DELETE)",
  "name": "API 한글 이름",
  "description": "API 설명",
  "tags": "태그 (첫 번째 경로 세그먼트)",
  "logic_type": "SQL 또는 MULTI_SQL",
  "logic_body": "실행할 SQL 쿼리 (:param 형식으로 파라미터 바인딩)",
  "request_spec": {"param_name": {"type": "string|int|float|bool", "required": true/false, "default": 기본값, "description": "설명"}},
  "response_spec": {"type": "list|object", "description": "응답 설명"},
  "sample_params": {"param_name": 샘플값},
  "change_note": "변경 노트"
}

규칙:
1. SQL은 반드시 파라미터 바인딩(:param)을 사용하세요.
2. 테이블의 인덱스를 활용하여 효율적인 쿼리를 작성하세요.
3. LIMIT와 OFFSET을 통한 페이지네이션을 고려하세요.
4. 한글 이름과 설명을 사용하세요.
5. sample_params에는 실제 테스트에 사용할 수 있는 현실적인 값을 넣으세요.
6. 반드시 유효한 JSON만 반환하세요. 다른 텍스트는 포함하지 마세요."""


def _build_user_prompt(request: ApiGenerationRequest) -> str:
    """사용자 프롬프트 생성"""
    tables_info = []
    for table in request.tables:
        table_info = f"""
### 테이블: {table.table_name}

**컬럼:**
{json.dumps(table.columns, indent=2, ensure_ascii=False)}

**인덱스:**
{json.dumps(table.indexes, indent=2, ensure_ascii=False)}

**샘플 데이터 (최대 5행):**
{json.dumps(table.sample_data[:5], indent=2, ensure_ascii=False, default=str)}
"""
        tables_info.append(table_info)
    
    return f"""사용자 의도: {request.user_intent}

HTTP 메서드: {request.method}

## 사용 가능한 테이블

{"".join(tables_info)}

위 정보를 바탕으로 사용자의 의도에 맞는 API 정의 JSON을 생성해주세요."""


def _setup_vertex_auth(config: LLMConfig) -> None:
    """Vertex AI 인증 설정"""
    # gcloud-key.json 파일이 이미 설정되어 있으면 사용
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    
    # vertex_credentials가 제공된 경우 임시 파일로 저장
    if config.vertex_credentials:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config.vertex_credentials)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name


async def generate_api_spec(
    request: ApiGenerationRequest,
    config: LLMConfig = LLMConfig()
) -> GeneratedApiSpec:
    """
    LLM을 사용하여 API 스펙 생성
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("litellm 라이브러리가 설치되어 있지 않습니다. pip install litellm을 실행해주세요.")
    
    # Vertex AI 인증 설정
    if config.vertex_credentials:
        _setup_vertex_auth(config)
    
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(request)
    
    # LiteLLM 호출 파라미터 구성
    completion_kwargs = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "top_p": config.top_p,
    }
    
    # Vertex AI 설정
    if config.model.startswith("vertex_ai/"):
        completion_kwargs["vertex_project"] = config.vertex_project
        completion_kwargs["vertex_location"] = config.vertex_location
    
    # API 키/베이스 설정
    if config.api_key:
        completion_kwargs["api_key"] = config.api_key
    if config.api_base:
        completion_kwargs["api_base"] = config.api_base
    
    try:
        response = await litellm.acompletion(**completion_kwargs)
        
        content = response.choices[0].message.content.strip()
        
        # JSON 추출 (마크다운 코드 블록 처리)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # JSON 파싱
        spec_dict = json.loads(content)
        
        return GeneratedApiSpec(**spec_dict)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")
    except Exception as e:
        raise RuntimeError(f"LLM 호출 실패: {e}")


def check_llm_availability() -> dict:
    """LLM 사용 가능 여부 확인"""
    result = {
        "litellm_installed": LITELLM_AVAILABLE,
        "env_keys": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "google": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
            "vertex": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            "azure": bool(os.getenv("AZURE_API_KEY")),
            "aws": bool(os.getenv("AWS_ACCESS_KEY_ID")),
            "mistral": bool(os.getenv("MISTRAL_API_KEY")),
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "together": bool(os.getenv("TOGETHER_API_KEY")),
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        }
    }
    
    result["available"] = result["litellm_installed"] and any(result["env_keys"].values())
    
    return result


# ==================== AI 기능 확장 ====================

class SqlOptimizationRequest(BaseModel):
    """SQL 최적화 요청"""
    sql_query: str
    table_schemas: list[dict]  # 테이블 스키마 정보
    indexes: list[dict] = []   # 사용 가능한 인덱스
    execution_time_ms: Optional[float] = None  # 현재 실행 시간


class SqlOptimizationResult(BaseModel):
    """SQL 최적화 결과"""
    original_query: str
    optimized_query: str
    suggestions: list[dict]  # [{"type": "INDEX", "message": "...", "priority": "HIGH"}]
    index_recommendations: list[dict]  # 새 인덱스 제안
    explanation: str
    estimated_improvement: Optional[str] = None


class TestCaseGenerationRequest(BaseModel):
    """테스트 케이스 생성 요청"""
    api_path: str
    method: str
    request_spec: dict
    logic_body: str
    sample_data: list[dict] = []


class TestCase(BaseModel):
    """단일 테스트 케이스"""
    name: str
    description: str
    params: dict
    expected_behavior: str
    test_type: str  # "positive", "negative", "boundary", "performance"


class TestCaseGenerationResult(BaseModel):
    """테스트 케이스 생성 결과"""
    api_path: str
    total_cases: int
    test_cases: list[TestCase]


class NaturalLanguageQueryRequest(BaseModel):
    """자연어 쿼리 요청"""
    question: str
    available_apis: list[dict]  # 사용 가능한 API 목록


class NaturalLanguageQueryResult(BaseModel):
    """자연어 쿼리 결과"""
    question: str
    selected_api: Optional[dict] = None  # 선택된 API
    params: dict = {}  # 추출된 파라미터
    confidence: float = 0.0  # 신뢰도 (0~1)
    explanation: str = ""  # 해석 설명
    alternative_apis: list[dict] = []  # 대안 API 목록


def _build_sql_optimization_prompt(request: SqlOptimizationRequest) -> str:
    """SQL 최적화 프롬프트 생성"""
    return f"""당신은 MySQL 쿼리 최적화 전문가입니다. 주어진 SQL 쿼리를 분석하고 성능 개선 방안을 제시해주세요.

## 분석 대상 쿼리
```sql
{request.sql_query}
```

## 테이블 스키마
{json.dumps(request.table_schemas, indent=2, ensure_ascii=False)}

## 사용 가능한 인덱스
{json.dumps(request.indexes, indent=2, ensure_ascii=False)}

{f"## 현재 실행 시간: {request.execution_time_ms}ms" if request.execution_time_ms else ""}

## 요청사항
다음 JSON 형식으로 최적화 결과를 반환해주세요:

```json
{{
  "original_query": "원본 쿼리",
  "optimized_query": "최적화된 쿼리",
  "suggestions": [
    {{"type": "INDEX|REWRITE|JOIN|LIMIT", "message": "개선 사항 설명", "priority": "HIGH|MEDIUM|LOW"}}
  ],
  "index_recommendations": [
    {{"table": "테이블명", "columns": ["컬럼1", "컬럼2"], "type": "INDEX|UNIQUE|FULLTEXT", "reason": "이유"}}
  ],
  "explanation": "전반적인 설명 (한글)",
  "estimated_improvement": "예상 성능 향상 (예: 50% 개선)"
}}
```

규칙:
1. 인덱스를 효과적으로 활용하도록 쿼리 수정
2. 불필요한 컬럼 선택 제거
3. JOIN 순서 최적화
4. WHERE 절 조건 순서 최적화
5. LIMIT 활용 권장
6. 서브쿼리보다 JOIN 선호"""


def _build_test_case_prompt(request: TestCaseGenerationRequest) -> str:
    """테스트 케이스 생성 프롬프트"""
    return f"""당신은 API 테스트 전문가입니다. 주어진 API 정의를 분석하여 포괄적인 테스트 케이스를 생성해주세요.

## API 정보
- 경로: {request.api_path}
- 메서드: {request.method}
- 요청 스펙: {json.dumps(request.request_spec, indent=2, ensure_ascii=False)}

## SQL 로직
```sql
{request.logic_body}
```

## 샘플 데이터
{json.dumps(request.sample_data[:3], indent=2, ensure_ascii=False, default=str)}

## 요청사항
다음 JSON 형식으로 테스트 케이스를 생성해주세요:

```json
{{
  "api_path": "API 경로",
  "total_cases": 테스트케이스수,
  "test_cases": [
    {{
      "name": "테스트케이스명",
      "description": "설명 (한글)",
      "params": {{"param1": "value1"}},
      "expected_behavior": "예상 동작 (한글)",
      "test_type": "positive|negative|boundary|performance"
    }}
  ]
}}
```

테스트 케이스 유형별 최소 개수:
1. positive (정상 케이스): 3개 이상
2. negative (에러 케이스): 2개 이상 - 필수 파라미터 누락, 잘못된 타입 등
3. boundary (경계값 테스트): 2개 이상 - 빈 문자열, 최대/최소값, 특수문자 등
4. performance (성능 테스트): 1개 이상 - 대량 데이터 조회 등

샘플 데이터의 실제 값을 활용하여 현실적인 테스트 파라미터를 생성하세요."""


def _build_natural_language_query_prompt(request: NaturalLanguageQueryRequest) -> str:
    """자연어 쿼리 프롬프트"""
    # API 목록을 간략하게 정리
    apis_summary = []
    for api in request.available_apis:
        apis_summary.append({
            "route_id": api.get("route_id"),
            "path": api.get("path"),
            "method": api.get("method"),
            "name": api.get("name"),
            "description": api.get("description", ""),
            "request_spec": api.get("request_spec", {}),
        })
    
    return f"""당신은 API 검색 및 파라미터 추출 전문가입니다. 사용자의 자연어 질문을 분석하여 가장 적합한 API를 찾고 파라미터를 추출해주세요.

## 사용자 질문
"{request.question}"

## 사용 가능한 API 목록
{json.dumps(apis_summary, indent=2, ensure_ascii=False)}

## 요청사항
다음 JSON 형식으로 결과를 반환해주세요:

```json
{{
  "question": "원본 질문",
  "selected_api": {{
    "route_id": "선택된 API ID",
    "path": "API 경로",
    "method": "HTTP 메서드"
  }},
  "params": {{"param_name": "추출된값"}},
  "confidence": 0.95,
  "explanation": "해석 설명 (한글) - 왜 이 API를 선택했고, 파라미터를 어떻게 추출했는지",
  "alternative_apis": [
    {{"route_id": "대안 API ID", "path": "경로", "reason": "이 API도 사용 가능한 이유"}}
  ]
}}
```

규칙:
1. 질문에서 언급된 키워드로 가장 적합한 API를 찾으세요.
2. 질문에서 파라미터 값을 추출하세요 (예: "홍길동 사용자" → {{"user_name": "홍길동"}})
3. 숫자, 날짜, ID 등을 자동으로 인식하여 파라미터에 매핑하세요.
4. 확실하지 않으면 confidence를 낮게 설정하세요.
5. 적합한 API가 없으면 selected_api를 null로 설정하고 설명하세요.
6. 여러 API가 가능하면 alternative_apis에 추가하세요."""


async def optimize_sql(
    request: SqlOptimizationRequest,
    config: LLMConfig = LLMConfig()
) -> SqlOptimizationResult:
    """SQL 쿼리 최적화 제안"""
    if not LITELLM_AVAILABLE:
        raise ImportError("litellm 라이브러리가 설치되어 있지 않습니다.")
    
    if config.vertex_credentials:
        _setup_vertex_auth(config)
    
    prompt = _build_sql_optimization_prompt(request)
    
    completion_kwargs = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "당신은 MySQL 쿼리 최적화 전문가입니다. 반드시 유효한 JSON만 반환하세요."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # 일관성 있는 결과를 위해 낮은 온도
        "max_tokens": config.max_tokens,
    }
    
    if config.model.startswith("vertex_ai/"):
        completion_kwargs["vertex_project"] = config.vertex_project
        completion_kwargs["vertex_location"] = config.vertex_location
    
    if config.api_key:
        completion_kwargs["api_key"] = config.api_key
    
    try:
        response = await litellm.acompletion(**completion_kwargs)
        content = response.choices[0].message.content.strip()
        
        # JSON 추출
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result_dict = json.loads(content)
        return SqlOptimizationResult(**result_dict)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")
    except Exception as e:
        raise RuntimeError(f"LLM 호출 실패: {e}")


async def generate_test_cases(
    request: TestCaseGenerationRequest,
    config: LLMConfig = LLMConfig()
) -> TestCaseGenerationResult:
    """API 테스트 케이스 자동 생성"""
    if not LITELLM_AVAILABLE:
        raise ImportError("litellm 라이브러리가 설치되어 있지 않습니다.")
    
    if config.vertex_credentials:
        _setup_vertex_auth(config)
    
    prompt = _build_test_case_prompt(request)
    
    completion_kwargs = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "당신은 API 테스트 케이스 생성 전문가입니다. 반드시 유효한 JSON만 반환하세요."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": config.max_tokens,
    }
    
    if config.model.startswith("vertex_ai/"):
        completion_kwargs["vertex_project"] = config.vertex_project
        completion_kwargs["vertex_location"] = config.vertex_location
    
    if config.api_key:
        completion_kwargs["api_key"] = config.api_key
    
    try:
        response = await litellm.acompletion(**completion_kwargs)
        content = response.choices[0].message.content.strip()
        
        # JSON 추출
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result_dict = json.loads(content)
        return TestCaseGenerationResult(**result_dict)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")
    except Exception as e:
        raise RuntimeError(f"LLM 호출 실패: {e}")


async def process_natural_language_query(
    request: NaturalLanguageQueryRequest,
    config: LLMConfig = LLMConfig()
) -> NaturalLanguageQueryResult:
    """자연어로 API 호출"""
    if not LITELLM_AVAILABLE:
        raise ImportError("litellm 라이브러리가 설치되어 있지 않습니다.")
    
    if config.vertex_credentials:
        _setup_vertex_auth(config)
    
    prompt = _build_natural_language_query_prompt(request)
    
    completion_kwargs = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "당신은 사용자의 자연어 질문을 분석하여 적합한 API를 찾는 전문가입니다. 반드시 유효한 JSON만 반환하세요."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": config.max_tokens,
    }
    
    if config.model.startswith("vertex_ai/"):
        completion_kwargs["vertex_project"] = config.vertex_project
        completion_kwargs["vertex_location"] = config.vertex_location
    
    if config.api_key:
        completion_kwargs["api_key"] = config.api_key
    
    try:
        response = await litellm.acompletion(**completion_kwargs)
        content = response.choices[0].message.content.strip()
        
        # JSON 추출
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result_dict = json.loads(content)
        return NaturalLanguageQueryResult(**result_dict)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}")
    except Exception as e:
        raise RuntimeError(f"LLM 호출 실패: {e}")


# ============================================================================
# 자연어 → SQL 쿼리 생성 및 보안 검증 시스템
# ============================================================================

import re
from enum import Enum
from dataclasses import dataclass


class SecurityRiskLevel(str, Enum):
    """보안 위험 수준"""
    SAFE = "safe"           # 안전
    LOW = "low"             # 낮은 위험
    MEDIUM = "medium"       # 중간 위험
    HIGH = "high"           # 높은 위험 (차단)
    CRITICAL = "critical"   # 치명적 위험 (즉시 차단)


class SecurityViolationType(str, Enum):
    """보안 위반 유형"""
    SQL_INJECTION = "sql_injection"
    DDL_COMMAND = "ddl_command"
    DANGEROUS_DML = "dangerous_dml"
    SENSITIVE_DATA = "sensitive_data"
    SYSTEM_TABLE = "system_table"
    MALICIOUS_INTENT = "malicious_intent"
    EXCESSIVE_SCOPE = "excessive_scope"
    PROHIBITED_KEYWORD = "prohibited_keyword"


@dataclass
class SecurityViolation:
    """보안 위반 정보"""
    violation_type: SecurityViolationType
    risk_level: SecurityRiskLevel
    description: str
    matched_pattern: str = ""


class NaturalLanguageToSqlRequest(BaseModel):
    """자연어 → SQL 변환 요청"""
    question: str
    tables: list[TableSchema]
    max_rows: int = 100  # 최대 반환 행 수
    allow_joins: bool = True  # JOIN 허용 여부
    read_only: bool = True  # SELECT만 허용


class SqlSecurityCheckResult(BaseModel):
    """SQL 보안 검사 결과"""
    is_safe: bool
    risk_level: str
    violations: list[dict]
    sanitized_query: Optional[str] = None
    blocked_reason: Optional[str] = None


class GeneratedSqlResult(BaseModel):
    """생성된 SQL 쿼리 결과"""
    original_question: str
    sql_query: str
    explanation: str
    tables_used: list[str]
    estimated_rows: Optional[int] = None
    security_check: SqlSecurityCheckResult
    execution_allowed: bool
    warnings: list[str] = []


# 민감 테이블 패턴 (정규식)
SENSITIVE_TABLE_PATTERNS = [
    r".*password.*",
    r".*passwd.*",
    r".*secret.*",
    r".*token.*",
    r".*credential.*",
    r".*api_key.*",
    r".*private.*",
    r".*admin.*",
    r".*auth.*",
    r".*session.*",
    r".*payment.*",
    r".*credit.*card.*",
    r".*bank.*",
    r".*ssn.*",  # Social Security Number
    r".*주민.*번호.*",
]

# 민감 컬럼 패턴
SENSITIVE_COLUMN_PATTERNS = [
    r".*password.*",
    r".*passwd.*",
    r".*pwd.*",
    r".*secret.*",
    r".*token.*",
    r".*api_key.*",
    r".*private_key.*",
    r".*credit.*card.*",
    r".*cvv.*",
    r".*ssn.*",
    r".*주민.*번호.*",
    r".*계좌.*번호.*",
    r".*카드.*번호.*",
    r".*비밀번호.*",
]

# SQL Injection 패턴
SQL_INJECTION_PATTERNS = [
    r";\s*--",                          # ; --
    r"'\s*OR\s+'?1'?\s*=\s*'?1",       # ' OR '1'='1
    r"'\s*OR\s+''='",                   # ' OR ''='
    r"UNION\s+SELECT",                  # UNION SELECT
    r"UNION\s+ALL\s+SELECT",           # UNION ALL SELECT
    r"'\s*;\s*DROP",                    # '; DROP
    r"'\s*;\s*DELETE",                  # '; DELETE
    r"'\s*;\s*UPDATE",                  # '; UPDATE
    r"'\s*;\s*INSERT",                  # '; INSERT
    r"EXEC\s*\(",                       # EXEC(
    r"EXECUTE\s*\(",                    # EXECUTE(
    r"xp_cmdshell",                     # xp_cmdshell
    r"INTO\s+OUTFILE",                  # INTO OUTFILE
    r"INTO\s+DUMPFILE",                 # INTO DUMPFILE
    r"LOAD_FILE\s*\(",                  # LOAD_FILE(
    r"BENCHMARK\s*\(",                  # BENCHMARK(
    r"SLEEP\s*\(",                      # SLEEP(
    r"WAITFOR\s+DELAY",                 # WAITFOR DELAY
    r"0x[0-9a-fA-F]+",                  # Hex encoding
]

# 금지된 DDL 명령어
PROHIBITED_DDL_COMMANDS = [
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
]

# 금지된 DML 명령어 (조건 없이 사용 시)
DANGEROUS_DML_COMMANDS = [
    "DELETE",
    "UPDATE",
    "INSERT",
    "REPLACE",
]

# 시스템 테이블 패턴
SYSTEM_TABLE_PATTERNS = [
    r"^information_schema\.",
    r"^mysql\.",
    r"^performance_schema\.",
    r"^sys\.",
]

# 악의적 의도 키워드
MALICIOUS_INTENT_KEYWORDS = [
    "삭제해줘",
    "지워줘",
    "모두 삭제",
    "전부 삭제",
    "데이터 삭제",
    "테이블 삭제",
    "drop",
    "delete all",
    "remove all",
    "비밀번호 보여줘",
    "password 조회",
    "토큰 보여줘",
    "api key",
    "해킹",
    "취약점",
    "우회",
    "injection",
]


def check_sql_security(sql_query: str, original_question: str = "") -> SqlSecurityCheckResult:
    """
    SQL 쿼리 보안 검사
    
    검사 항목:
    1. SQL Injection 패턴
    2. DDL 명령어
    3. 위험한 DML 명령어
    4. 민감 테이블/컬럼 접근
    5. 시스템 테이블 접근
    6. 악의적 의도
    """
    violations = []
    
    # SQL 쿼리 정규화 (우회 공격 방지)
    # 1. 주석 제거
    normalized_sql = re.sub(r'--.*$', ' ', sql_query, flags=re.MULTILINE)  # 라인 주석
    normalized_sql = re.sub(r'/\*.*?\*/', ' ', normalized_sql, flags=re.DOTALL)  # 블록 주석
    # 2. 연속 공백을 단일 공백으로
    normalized_sql = re.sub(r'\s+', ' ', normalized_sql)
    # 3. 대문자 변환 (비교용)
    sql_upper = normalized_sql.upper().strip()
    question_lower = original_question.lower()
    
    # 1. SQL Injection 패턴 검사 (원본 + 정규화된 쿼리 모두 검사)
    for pattern in SQL_INJECTION_PATTERNS:
        # 원본 쿼리 검사
        if re.search(pattern, sql_query, re.IGNORECASE):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.SQL_INJECTION,
                risk_level=SecurityRiskLevel.CRITICAL,
                description="SQL Injection 패턴이 감지되었습니다.",
                matched_pattern=pattern
            ))
            continue
        # 정규화된 쿼리 검사 (우회 공격 방지)
        if re.search(pattern, normalized_sql, re.IGNORECASE):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.SQL_INJECTION,
                risk_level=SecurityRiskLevel.CRITICAL,
                description="SQL Injection 패턴이 감지되었습니다 (주석/공백 우회 시도).",
                matched_pattern=pattern
            ))
    
    # 2. DDL 명령어 검사 (정규화된 쿼리 사용)
    for cmd in PROHIBITED_DDL_COMMANDS:
        if re.search(rf'\b{cmd}\b', sql_upper):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.DDL_COMMAND,
                risk_level=SecurityRiskLevel.CRITICAL,
                description=f"금지된 DDL 명령어 '{cmd}'가 감지되었습니다.",
                matched_pattern=cmd
            ))
    
    # 3. 위험한 DML 명령어 검사 (SELECT 외의 명령어)
    for cmd in DANGEROUS_DML_COMMANDS:
        if re.search(rf'\b{cmd}\b', sql_upper):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.DANGEROUS_DML,
                risk_level=SecurityRiskLevel.HIGH,
                description=f"위험한 DML 명령어 '{cmd}'가 감지되었습니다. 읽기 전용 쿼리만 허용됩니다.",
                matched_pattern=cmd
            ))
    
    # 4. 민감 테이블 접근 검사
    for pattern in SENSITIVE_TABLE_PATTERNS:
        if re.search(pattern, sql_query, re.IGNORECASE):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.SENSITIVE_DATA,
                risk_level=SecurityRiskLevel.HIGH,
                description="민감한 데이터 테이블에 대한 접근이 감지되었습니다.",
                matched_pattern=pattern
            ))
    
    # 5. 민감 컬럼 접근 검사
    for pattern in SENSITIVE_COLUMN_PATTERNS:
        if re.search(pattern, sql_query, re.IGNORECASE):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.SENSITIVE_DATA,
                risk_level=SecurityRiskLevel.HIGH,
                description="민감한 데이터 컬럼에 대한 접근이 감지되었습니다.",
                matched_pattern=pattern
            ))
    
    # 6. 시스템 테이블 접근 검사
    for pattern in SYSTEM_TABLE_PATTERNS:
        if re.search(pattern, sql_query, re.IGNORECASE):
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.SYSTEM_TABLE,
                risk_level=SecurityRiskLevel.MEDIUM,
                description="시스템 테이블에 대한 접근이 감지되었습니다.",
                matched_pattern=pattern
            ))
    
    # 7. 악의적 의도 검사 (원본 질문)
    for keyword in MALICIOUS_INTENT_KEYWORDS:
        if keyword.lower() in question_lower:
            violations.append(SecurityViolation(
                violation_type=SecurityViolationType.MALICIOUS_INTENT,
                risk_level=SecurityRiskLevel.HIGH,
                description=f"악의적 의도가 의심되는 키워드 '{keyword}'가 감지되었습니다.",
                matched_pattern=keyword
            ))
    
    # 8. SELECT 문이 아닌 경우 (읽기 전용 모드)
    if not sql_upper.startswith("SELECT"):
        violations.append(SecurityViolation(
            violation_type=SecurityViolationType.DANGEROUS_DML,
            risk_level=SecurityRiskLevel.HIGH,
            description="SELECT 문이 아닙니다. 읽기 전용 쿼리만 허용됩니다.",
            matched_pattern="NON_SELECT"
        ))
    
    # 위험 수준 결정
    if any(v.risk_level == SecurityRiskLevel.CRITICAL for v in violations):
        overall_risk = SecurityRiskLevel.CRITICAL
    elif any(v.risk_level == SecurityRiskLevel.HIGH for v in violations):
        overall_risk = SecurityRiskLevel.HIGH
    elif any(v.risk_level == SecurityRiskLevel.MEDIUM for v in violations):
        overall_risk = SecurityRiskLevel.MEDIUM
    elif any(v.risk_level == SecurityRiskLevel.LOW for v in violations):
        overall_risk = SecurityRiskLevel.LOW
    else:
        overall_risk = SecurityRiskLevel.SAFE
    
    is_safe = overall_risk == SecurityRiskLevel.SAFE
    blocked_reason = None
    
    if not is_safe:
        blocked_reason = "; ".join([v.description for v in violations[:3]])  # 상위 3개 이유
    
    return SqlSecurityCheckResult(
        is_safe=is_safe,
        risk_level=overall_risk.value,
        violations=[{
            "type": v.violation_type.value,
            "risk_level": v.risk_level.value,
            "description": v.description,
            "pattern": v.matched_pattern
        } for v in violations],
        sanitized_query=sql_query if is_safe else None,
        blocked_reason=blocked_reason
    )


def check_question_intent(question: str) -> tuple[bool, list[str]]:
    """
    사용자 질문의 의도를 검사하여 악의적인지 판단
    
    Returns:
        (is_safe, warnings): 안전 여부와 경고 메시지 목록
    """
    warnings = []
    question_lower = question.lower()
    
    # 악의적 의도 키워드 검사
    for keyword in MALICIOUS_INTENT_KEYWORDS:
        if keyword.lower() in question_lower:
            return False, [f"'{keyword}'와 관련된 요청은 처리할 수 없습니다."]
    
    # 데이터 수정/삭제 의도 검사
    modification_patterns = [
        (r"삭제|지우|제거|drop|delete|remove", "데이터 삭제"),
        (r"수정|변경|업데이트|update|modify|change", "데이터 수정"),
        (r"추가|입력|삽입|insert|add|create", "데이터 추가"),
    ]
    
    for pattern, description in modification_patterns:
        if re.search(pattern, question_lower):
            warnings.append(f"'{description}' 관련 요청은 읽기 전용 모드에서 처리되지 않습니다.")
    
    # 민감 정보 요청 검사
    sensitive_patterns = [
        (r"비밀번호|password|pwd|passwd", "비밀번호"),
        (r"주민.*번호|ssn|social.*security", "주민등록번호"),
        (r"카드.*번호|credit.*card|cvv", "카드번호"),
        (r"계좌.*번호|bank.*account", "계좌번호"),
        (r"토큰|token|api.*key|secret", "인증 토큰"),
    ]
    
    for pattern, description in sensitive_patterns:
        if re.search(pattern, question_lower):
            return False, [f"'{description}' 관련 민감 정보는 조회할 수 없습니다."]
    
    return True, warnings


def sanitize_sql_query(sql_query: str, max_rows: int = 100) -> str:
    """
    SQL 쿼리 정제 및 LIMIT 강제 적용
    """
    sql_query = sql_query.strip()
    
    # 세미콜론 제거 (다중 쿼리 방지)
    sql_query = sql_query.rstrip(';')
    
    # 주석 제거
    sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
    sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
    
    # LIMIT 강제 적용
    sql_upper = sql_query.upper()
    if "LIMIT" not in sql_upper:
        sql_query = f"{sql_query} LIMIT {max_rows}"
    else:
        # 기존 LIMIT 값이 max_rows보다 크면 제한
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
        if limit_match:
            current_limit = int(limit_match.group(1))
            if current_limit > max_rows:
                sql_query = re.sub(
                    r'LIMIT\s+\d+',
                    f'LIMIT {max_rows}',
                    sql_query,
                    flags=re.IGNORECASE
                )
    
    return sql_query


def _build_natural_language_to_sql_prompt(request: NaturalLanguageToSqlRequest) -> str:
    """자연어 → SQL 변환 프롬프트 생성"""
    
    # 테이블 스키마 정보 구성
    tables_info = []
    for table in request.tables:
        columns_str = "\n      ".join([
            f"- {col.get('column_name', col.get('name', 'unknown'))}: "
            f"{col.get('data_type', col.get('type', 'unknown'))} "
            f"{'(PK)' if col.get('is_primary_key') or col.get('column_key') == 'PRI' else ''} "
            f"{'(nullable)' if col.get('is_nullable') == 'YES' else ''}"
            f"{' - ' + col.get('column_comment', '') if col.get('column_comment') else ''}"
            for col in table.columns
        ])
        
        sample_str = ""
        if table.sample_data:
            sample_str = f"\n    샘플 데이터 (최대 3행):\n      {json.dumps(table.sample_data[:3], ensure_ascii=False, indent=6)}"
        
        tables_info.append(f"""
    테이블: {table.table_name}
    컬럼:
      {columns_str}{sample_str}
""")
    
    tables_schema = "\n".join(tables_info)
    
    return f"""사용자의 자연어 질문을 분석하여 안전한 MySQL SELECT 쿼리를 생성하세요.

## 사용 가능한 테이블
{tables_schema}

## 사용자 질문
"{request.question}"

## 규칙 (반드시 준수)
1. **SELECT 문만 생성**: 절대로 INSERT, UPDATE, DELETE, DROP 등 데이터 수정 쿼리를 생성하지 마세요.
2. **민감 정보 제외**: 비밀번호, 토큰, 카드번호, 주민번호 등 민감한 컬럼은 SELECT에서 제외하세요.
3. **LIMIT 적용**: 결과 행 수를 {request.max_rows}개로 제한하세요.
4. **명확한 컬럼 선택**: SELECT *는 피하고, 필요한 컬럼만 명시하세요.
5. **JOIN 제한**: {"JOIN을 사용할 수 있습니다." if request.allow_joins else "JOIN은 사용하지 마세요."}
6. **안전한 WHERE 절**: 사용자 입력값은 파라미터로 처리될 것이므로 직접 값을 넣어도 됩니다.

## 응답 형식 (JSON)
```json
{{
  "sql_query": "생성된 SELECT 쿼리",
  "explanation": "쿼리 설명 (한국어)",
  "tables_used": ["사용된 테이블 목록"],
  "estimated_rows": null,
  "warnings": ["주의사항 목록"],
  "confidence": 0.0~1.0
}}
```

## 처리할 수 없는 요청의 경우
```json
{{
  "sql_query": null,
  "explanation": "처리할 수 없는 이유",
  "tables_used": [],
  "estimated_rows": null,
  "warnings": ["경고 메시지"],
  "confidence": 0.0
}}
```"""


async def generate_sql_from_natural_language(
    request: NaturalLanguageToSqlRequest,
    config: LLMConfig = LLMConfig()
) -> GeneratedSqlResult:
    """
    자연어를 SQL 쿼리로 변환
    
    보안 검증 프로세스:
    1. 사용자 질문 의도 검사
    2. LLM을 통한 SQL 생성
    3. 생성된 SQL 보안 검사
    4. SQL 정제 및 LIMIT 적용
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("litellm 라이브러리가 설치되어 있지 않습니다.")
    
    # 1단계: 사용자 질문 의도 검사
    is_question_safe, intent_warnings = check_question_intent(request.question)
    
    if not is_question_safe:
        return GeneratedSqlResult(
            original_question=request.question,
            sql_query="",
            explanation=intent_warnings[0] if intent_warnings else "요청을 처리할 수 없습니다.",
            tables_used=[],
            security_check=SqlSecurityCheckResult(
                is_safe=False,
                risk_level=SecurityRiskLevel.HIGH.value,
                violations=[{
                    "type": SecurityViolationType.MALICIOUS_INTENT.value,
                    "risk_level": SecurityRiskLevel.HIGH.value,
                    "description": intent_warnings[0] if intent_warnings else "악의적 의도 감지",
                    "pattern": ""
                }],
                blocked_reason=intent_warnings[0] if intent_warnings else "요청이 차단되었습니다."
            ),
            execution_allowed=False,
            warnings=intent_warnings
        )
    
    # 2단계: Vertex AI 인증 설정
    if config.vertex_credentials:
        _setup_vertex_auth(config)
    
    # 3단계: LLM을 통한 SQL 생성
    prompt = _build_natural_language_to_sql_prompt(request)
    
    completion_kwargs = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": "당신은 자연어를 안전한 MySQL SELECT 쿼리로 변환하는 전문가입니다. "
                          "보안을 최우선으로 하며, 반드시 유효한 JSON만 반환하세요. "
                          "데이터 수정 쿼리(INSERT, UPDATE, DELETE, DROP 등)는 절대 생성하지 마세요."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,  # 일관성 있는 결과를 위해 낮은 온도
        "max_tokens": config.max_tokens,
    }
    
    if config.model.startswith("vertex_ai/"):
        completion_kwargs["vertex_project"] = config.vertex_project
        completion_kwargs["vertex_location"] = config.vertex_location
    
    if config.api_key:
        completion_kwargs["api_key"] = config.api_key
    
    try:
        response = await litellm.acompletion(**completion_kwargs)
        content = response.choices[0].message.content.strip()
        
        # JSON 추출
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        llm_result = json.loads(content)
        
        # LLM이 쿼리 생성을 거부한 경우
        if not llm_result.get("sql_query"):
            return GeneratedSqlResult(
                original_question=request.question,
                sql_query="",
                explanation=llm_result.get("explanation", "쿼리를 생성할 수 없습니다."),
                tables_used=llm_result.get("tables_used", []),
                security_check=SqlSecurityCheckResult(
                    is_safe=False,
                    risk_level=SecurityRiskLevel.MEDIUM.value,
                    violations=[],
                    blocked_reason=llm_result.get("explanation", "쿼리를 생성할 수 없습니다.")
                ),
                execution_allowed=False,
                warnings=llm_result.get("warnings", [])
            )
        
        sql_query = llm_result.get("sql_query", "")
        
        # 4단계: 생성된 SQL 보안 검사
        security_result = check_sql_security(sql_query, request.question)
        
        # 5단계: 보안 검사 통과 시 SQL 정제
        if security_result.is_safe:
            sql_query = sanitize_sql_query(sql_query, request.max_rows)
            security_result.sanitized_query = sql_query
        
        all_warnings = intent_warnings + llm_result.get("warnings", [])
        
        return GeneratedSqlResult(
            original_question=request.question,
            sql_query=sql_query if security_result.is_safe else "",
            explanation=llm_result.get("explanation", ""),
            tables_used=llm_result.get("tables_used", []),
            estimated_rows=llm_result.get("estimated_rows"),
            security_check=security_result,
            execution_allowed=security_result.is_safe,
            warnings=all_warnings
        )
        
    except json.JSONDecodeError as e:
        return GeneratedSqlResult(
            original_question=request.question,
            sql_query="",
            explanation=f"LLM 응답 파싱 실패: {str(e)}",
            tables_used=[],
            security_check=SqlSecurityCheckResult(
                is_safe=False,
                risk_level=SecurityRiskLevel.MEDIUM.value,
                violations=[],
                blocked_reason="LLM 응답 파싱 실패"
            ),
            execution_allowed=False,
            warnings=[f"JSON 파싱 오류: {str(e)}"]
        )
    except Exception as e:
        raise RuntimeError(f"LLM 호출 실패: {e}")
