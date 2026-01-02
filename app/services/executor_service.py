"""
로직 실행 서비스
logic_type에 따라 적절한 로직을 실행합니다.

지원 로직 타입:
- SQL: 단일 MySQL 쿼리 실행
- MULTI_SQL: 다중 MySQL 쿼리 순차 실행
- PIPELINE: 여러 로직을 파이프라인으로 연결
- BIGQUERY: Google BigQuery 쿼리 실행
- OPENSEARCH: OpenSearch 쿼리 실행
- PYTHON_EXPR: 간단한 Python 표현식 실행
- HTTP_CALL: 외부 API 호출
- STATIC_RESPONSE: 정적 JSON 응답

⚠️ 보안 주의사항:
- SQL 실행 시 반드시 파라미터 바인딩을 사용합니다.
- PYTHON_EXPR은 제한된 표현식만 허용합니다.
- 외부 HTTP 호출은 허용된 도메인만 가능합니다.
"""
from typing import Any, Optional
from datetime import datetime, date
from decimal import Decimal
import json
import re
import httpx
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def serialize_value(value: Any) -> Any:
    """SQL 결과값을 JSON 직렬화 가능한 형태로 변환"""
    if isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, date):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value


def serialize_row(row_dict: dict) -> dict:
    """행 딕셔너리의 모든 값을 직렬화"""
    return {k: serialize_value(v) for k, v in row_dict.items()}


class ExecutorError(Exception):
    """실행 오류 예외"""
    def __init__(self, message: str, error_type: str = "EXECUTION_ERROR"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class ExecutorService:
    """로직 실행 서비스"""
    
    # SQL에서 허용하지 않는 위험한 키워드
    DANGEROUS_SQL_KEYWORDS = [
        "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
        "EXEC", "EXECUTE", "XP_", "SP_", "INTO OUTFILE", "INTO DUMPFILE",
        "LOAD_FILE", "BENCHMARK", "SLEEP",
    ]
    
    # Python 표현식에서 허용하지 않는 키워드
    DANGEROUS_PYTHON_KEYWORDS = [
        "__import__", "eval", "exec", "compile", "open", "file",
        "input", "raw_input", "reload", "__builtins__",
        "os.", "sys.", "subprocess", "shutil", "pathlib",
    ]
    
    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        logic_type: str,
        logic_body: str,
        params: dict[str, Any],
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        로직 실행
        
        Args:
            db: 데이터베이스 세션
            logic_type: 로직 타입
            logic_body: 실행할 로직
            params: 파라미터
            config: 추가 설정
            
        Returns:
            실행 결과 {"result": ..., "result_count": ...}
        """
        config = config or {}
        
        if logic_type == "SQL":
            return await cls._execute_sql(db, logic_body, params, config)
        elif logic_type == "MULTI_SQL":
            return await cls._execute_multi_sql(db, logic_body, params, config)
        elif logic_type == "PIPELINE":
            return await cls._execute_pipeline(db, logic_body, params, config)
        elif logic_type == "BIGQUERY":
            return await cls._execute_bigquery(logic_body, params, config)
        elif logic_type == "OPENSEARCH":
            return await cls._execute_opensearch(logic_body, params, config)
        elif logic_type == "PYTHON_EXPR":
            return cls._execute_python_expr(logic_body, params, config)
        elif logic_type == "HTTP_CALL":
            return await cls._execute_http_call(logic_body, params, config)
        elif logic_type == "STATIC_RESPONSE":
            return cls._execute_static_response(logic_body, params)
        else:
            raise ExecutorError(f"지원하지 않는 로직 타입: {logic_type}", "UNSUPPORTED_LOGIC_TYPE")
    
    @classmethod
    def _validate_sql(cls, query: str) -> None:
        """SQL 보안 검증"""
        query_upper = query.upper()
        for keyword in cls.DANGEROUS_SQL_KEYWORDS:
            if keyword in query_upper:
                raise ExecutorError(
                    f"보안 위험: '{keyword}' 키워드는 허용되지 않습니다.",
                    "DANGEROUS_SQL_DETECTED"
                )
        
        # 세미콜론 다중 쿼리 방지 (주석 제외)
        clean_query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
        if clean_query.count(';') > 1:
            raise ExecutorError(
                "보안 위험: 다중 쿼리는 허용되지 않습니다. MULTI_SQL 타입을 사용하세요.",
                "MULTIPLE_QUERIES_DETECTED"
            )
    
    @classmethod
    async def _execute_sql(
        cls,
        db: AsyncSession,
        query: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        단일 SQL 쿼리 실행
        """
        cls._validate_sql(query)
        
        try:
            result = await db.execute(text(query), params)
            
            if query.strip().upper().startswith("SELECT"):
                rows = result.fetchall()
                columns = result.keys()
                data = [serialize_row(dict(zip(columns, row))) for row in rows]
                return {
                    "result": data,
                    "result_count": len(data),
                }
            else:
                await db.commit()
                return {
                    "result": {"affected_rows": result.rowcount},
                    "result_count": result.rowcount,
                }
        except Exception as e:
            await db.rollback()
            raise ExecutorError(f"SQL 실행 오류: {str(e)}", "SQL_EXECUTION_ERROR")
    
    @classmethod
    async def _execute_multi_sql(
        cls,
        db: AsyncSession,
        queries_json: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        다중 SQL 쿼리 순차 실행
        
        queries_json 예시:
        {
            "queries": [
                {"name": "users", "sql": "SELECT * FROM APP_USER_L WHERE CMPNY_ID = :cmpny_id"},
                {"name": "company", "sql": "SELECT * FROM APP_CMPNY_L WHERE CMPNY_ID = :cmpny_id"}
            ]
        }
        
        결과: {"users": [...], "company": [...]}
        """
        try:
            spec = json.loads(queries_json)
        except json.JSONDecodeError:
            raise ExecutorError("MULTI_SQL 스펙이 올바른 JSON 형식이 아닙니다.", "INVALID_MULTI_SQL_SPEC")
        
        queries = spec.get("queries", [])
        if not queries:
            raise ExecutorError("실행할 쿼리가 없습니다.", "NO_QUERIES")
        
        results = {}
        total_count = 0
        
        for query_spec in queries:
            name = query_spec.get("name", f"query_{len(results)}")
            sql = query_spec.get("sql")
            
            if not sql:
                continue
            
            cls._validate_sql(sql)
            
            # 이전 쿼리 결과를 파라미터로 사용 가능
            merged_params = {**params}
            for key, value in results.items():
                if isinstance(value, list) and len(value) > 0:
                    # 첫 번째 결과의 각 컬럼을 파라미터로
                    first_row = value[0]
                    for col, val in first_row.items():
                        merged_params[f"{key}_{col}"] = val
            
            try:
                result = await db.execute(text(sql), merged_params)
                
                if sql.strip().upper().startswith("SELECT"):
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [serialize_row(dict(zip(columns, row))) for row in rows]
                    results[name] = data
                    total_count += len(data)
                else:
                    results[name] = {"affected_rows": result.rowcount}
                    total_count += result.rowcount
            except Exception as e:
                results[name] = {"error": str(e)}
        
        await db.commit()
        
        return {
            "result": results,
            "result_count": total_count,
        }
    
    @classmethod
    async def _execute_pipeline(
        cls,
        db: AsyncSession,
        pipeline_json: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        파이프라인 실행 - 여러 로직을 순차적으로 연결
        
        pipeline_json 예시:
        {
            "steps": [
                {"type": "SQL", "body": "SELECT * FROM APP_USER_L LIMIT :limit", "output": "users"},
                {"type": "PYTHON_EXPR", "body": "len(params['users'])", "output": "user_count"},
                {"type": "STATIC_RESPONSE", "body": "{\"users\": \"$params.users\", \"count\": \"$params.user_count\"}"}
            ]
        }
        """
        try:
            spec = json.loads(pipeline_json)
        except json.JSONDecodeError:
            raise ExecutorError("PIPELINE 스펙이 올바른 JSON 형식이 아닙니다.", "INVALID_PIPELINE_SPEC")
        
        steps = spec.get("steps", [])
        if not steps:
            raise ExecutorError("실행할 스텝이 없습니다.", "NO_STEPS")
        
        current_params = {**params}
        last_result = None
        
        for i, step in enumerate(steps):
            step_type = step.get("type", "SQL")
            step_body = step.get("body", "")
            output_name = step.get("output")
            
            # 재귀적으로 execute 호출 (PIPELINE 제외)
            if step_type == "PIPELINE":
                raise ExecutorError("파이프라인 내에서 파이프라인을 호출할 수 없습니다.", "NESTED_PIPELINE")
            
            step_result = await cls.execute(
                db=db,
                logic_type=step_type,
                logic_body=step_body,
                params=current_params,
                config=config,
            )
            
            last_result = step_result
            
            # 결과를 다음 스텝의 파라미터로 전달
            if output_name:
                current_params[output_name] = step_result.get("result")
        
        return last_result or {"result": None, "result_count": 0}
    
    @classmethod
    async def _execute_bigquery(
        cls,
        query: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        Google BigQuery 쿼리 실행
        
        환경변수 필요:
        - GCP_PROJECT_ID
        - GCP_CREDENTIALS_PATH (서비스 계정 JSON 경로)
        """
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
        except ImportError:
            raise ExecutorError(
                "google-cloud-bigquery 패키지가 설치되지 않았습니다. pip install google-cloud-bigquery",
                "BIGQUERY_NOT_INSTALLED"
            )
        
        project_id = os.getenv("GCP_PROJECT_ID")
        credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
        
        if not project_id:
            raise ExecutorError("GCP_PROJECT_ID 환경변수가 설정되지 않았습니다.", "BIGQUERY_CONFIG_ERROR")
        
        try:
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                client = bigquery.Client(project=project_id, credentials=credentials)
            else:
                client = bigquery.Client(project=project_id)
            
            # 파라미터 바인딩
            query_params = []
            for key, value in params.items():
                if isinstance(value, int):
                    query_params.append(bigquery.ScalarQueryParameter(key, "INT64", value))
                elif isinstance(value, float):
                    query_params.append(bigquery.ScalarQueryParameter(key, "FLOAT64", value))
                elif isinstance(value, bool):
                    query_params.append(bigquery.ScalarQueryParameter(key, "BOOL", value))
                else:
                    query_params.append(bigquery.ScalarQueryParameter(key, "STRING", str(value)))
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            query_job = client.query(query, job_config=job_config)
            
            results = query_job.result()
            data = [serialize_row(dict(row)) for row in results]
            
            return {
                "result": data,
                "result_count": len(data),
            }
        except Exception as e:
            raise ExecutorError(f"BigQuery 실행 오류: {str(e)}", "BIGQUERY_EXECUTION_ERROR")
    
    @classmethod
    async def _execute_opensearch(
        cls,
        query_json: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        OpenSearch 쿼리 실행
        
        query_json 예시:
        {
            "index": "my_index",
            "body": {
                "query": {"match": {"title": "$params.keyword"}}
            }
        }
        
        환경변수 필요:
        - OPENSEARCH_HOST (예: https://localhost:9200)
        - OPENSEARCH_USER (선택)
        - OPENSEARCH_PASSWORD (선택)
        """
        try:
            spec = json.loads(query_json)
        except json.JSONDecodeError:
            raise ExecutorError("OpenSearch 스펙이 올바른 JSON 형식이 아닙니다.", "INVALID_OPENSEARCH_SPEC")
        
        host = os.getenv("OPENSEARCH_HOST", config.get("host"))
        if not host:
            raise ExecutorError("OPENSEARCH_HOST가 설정되지 않았습니다.", "OPENSEARCH_CONFIG_ERROR")
        
        index = spec.get("index")
        body = spec.get("body", {})
        
        if not index:
            raise ExecutorError("OpenSearch 인덱스가 지정되지 않았습니다.", "OPENSEARCH_NO_INDEX")
        
        # 파라미터 치환
        body_str = json.dumps(body)
        for key, value in params.items():
            body_str = body_str.replace(f"$params.{key}", json.dumps(value)[1:-1] if isinstance(value, str) else str(value))
        body = json.loads(body_str)
        
        # HTTP로 OpenSearch 호출
        user = os.getenv("OPENSEARCH_USER", config.get("user"))
        password = os.getenv("OPENSEARCH_PASSWORD", config.get("password"))
        
        url = f"{host}/{index}/_search"
        
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                auth = (user, password) if user and password else None
                response = await client.post(
                    url,
                    json=body,
                    auth=auth,
                    headers={"Content-Type": "application/json"}
                )
                
                result = response.json()
                
                # hits 추출
                hits = result.get("hits", {}).get("hits", [])
                data = [hit.get("_source", {}) for hit in hits]
                
                return {
                    "result": data,
                    "result_count": len(data),
                    "total": result.get("hits", {}).get("total", {}).get("value", len(data)),
                }
        except Exception as e:
            raise ExecutorError(f"OpenSearch 실행 오류: {str(e)}", "OPENSEARCH_EXECUTION_ERROR")
    
    @classmethod
    def _execute_python_expr(
        cls,
        expr: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        Python 표현식 실행 (매우 제한적)
        """
        for keyword in cls.DANGEROUS_PYTHON_KEYWORDS:
            if keyword in expr:
                raise ExecutorError(
                    f"보안 위험: '{keyword}' 키워드는 허용되지 않습니다.",
                    "DANGEROUS_PYTHON_DETECTED"
                )
        
        safe_builtins = {
            "len": len, "str": str, "int": int, "float": float, "bool": bool,
            "list": list, "dict": dict, "sum": sum, "min": min, "max": max,
            "abs": abs, "round": round, "sorted": sorted, "reversed": reversed,
            "enumerate": enumerate, "zip": zip, "range": range,
            "True": True, "False": False, "None": None,
        }
        
        try:
            # Python dict 리터럴로 시작하면 eval
            if expr.strip().startswith("{") or expr.strip().startswith("["):
                result = eval(expr, {"__builtins__": safe_builtins}, {"params": params})
            else:
                result = eval(expr, {"__builtins__": safe_builtins}, {"params": params})
            
            return {
                "result": result,
                "result_count": len(result) if isinstance(result, (list, dict)) else 1,
            }
        except Exception as e:
            raise ExecutorError(f"Python 표현식 실행 오류: {str(e)}", "PYTHON_EXPR_ERROR")
    
    @classmethod
    async def _execute_http_call(
        cls,
        call_spec: str,
        params: dict[str, Any],
        config: dict,
    ) -> dict[str, Any]:
        """
        외부 HTTP 호출
        """
        try:
            spec = json.loads(call_spec)
        except json.JSONDecodeError:
            raise ExecutorError("HTTP 호출 스펙이 올바른 JSON 형식이 아닙니다.", "INVALID_HTTP_SPEC")
        
        url = spec.get("url")
        method = spec.get("method", "GET").upper()
        headers = spec.get("headers", {})
        timeout = config.get("timeout", 30)
        
        if not url:
            raise ExecutorError("HTTP 호출에 URL이 필요합니다.", "MISSING_URL")
        
        for key, value in params.items():
            url = url.replace(f":{key}", str(value))
            url = url.replace(f"{{{key}}}", str(value))
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=params)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=params)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ExecutorError(f"지원하지 않는 HTTP 메서드: {method}", "UNSUPPORTED_HTTP_METHOD")
                
                result = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                
                return {
                    "result": result,
                    "result_count": len(result) if isinstance(result, (list, dict)) else 1,
                    "status_code": response.status_code,
                }
        except httpx.TimeoutException:
            raise ExecutorError("HTTP 호출 타임아웃", "HTTP_TIMEOUT")
        except Exception as e:
            raise ExecutorError(f"HTTP 호출 오류: {str(e)}", "HTTP_CALL_ERROR")
    
    @classmethod
    def _execute_static_response(
        cls,
        response_data: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        정적 응답 반환
        """
        try:
            for key, value in params.items():
                if isinstance(value, str):
                    response_data = response_data.replace(f"$params.{key}", value)
                else:
                    response_data = response_data.replace(f"$params.{key}", json.dumps(value))
            
            result = json.loads(response_data)
            return {
                "result": result,
                "result_count": 1,
            }
        except json.JSONDecodeError:
            return {
                "result": response_data,
                "result_count": 1,
            }
