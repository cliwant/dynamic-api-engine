"""
LLM 서비스
LiteLLM을 사용하여 다양한 LLM 모델을 호출합니다.
API 생성을 위한 프롬프트 엔지니어링을 담당합니다.
"""
import json
import os
from typing import Optional, Any
from pydantic import BaseModel

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class LLMConfig(BaseModel):
    """LLM 설정"""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    # 인증 설정
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    vertex_credentials: Optional[str] = None  # gcloud-key.json 내용


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


# LiteLLM 지원 모델 목록 (주요 프로바이더)
SUPPORTED_MODELS = [
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
    
    # Google AI (Gemini)
    {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "google", "auth": "api_key"},
    {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "google", "auth": "api_key"},
    {"id": "gemini/gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash", "provider": "google", "auth": "api_key"},
    {"id": "gemini/gemini-pro", "name": "Gemini Pro", "provider": "google", "auth": "api_key"},
    
    # Vertex AI (Google Cloud)
    {"id": "vertex_ai/gemini-1.5-pro", "name": "Gemini 1.5 Pro (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/gemini-1.5-flash", "name": "Gemini 1.5 Flash (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/gemini-pro", "name": "Gemini Pro (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/claude-3-5-sonnet@20241022", "name": "Claude 3.5 Sonnet (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    {"id": "vertex_ai/claude-3-5-haiku@20241022", "name": "Claude 3.5 Haiku (Vertex)", "provider": "vertex_ai", "auth": "vertex"},
    
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
    if config.vertex_credentials:
        import tempfile
        # JSON 문자열을 임시 파일로 저장
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
