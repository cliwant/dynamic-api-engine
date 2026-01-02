"""
요청 파라미터 검증 서비스
request_spec에 정의된 규칙에 따라 입력값을 검증합니다.
"""
from typing import Any, Optional
import re


class ValidationError(Exception):
    """검증 실패 예외"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ValidatorService:
    """요청 파라미터 검증 서비스"""
    
    # 타입 변환 맵핑
    TYPE_CONVERTERS = {
        "string": str,
        "int": int,
        "float": float,
        "bool": lambda v: v if isinstance(v, bool) else str(v).lower() in ("true", "1", "yes"),
        "array": list,
        "object": dict,
    }
    
    @classmethod
    def validate(cls, params: dict[str, Any], spec: Optional[dict[str, Any]]) -> dict[str, Any]:
        """
        파라미터 검증 및 타입 변환
        
        Args:
            params: 사용자 입력 파라미터
            spec: 검증 규칙 (request_spec)
            
        Returns:
            검증 및 타입 변환된 파라미터
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not spec:
            return params
        
        validated = {}
        
        for field_name, field_spec in spec.items():
            value = params.get(field_name)
            field_type = field_spec.get("type", "string")
            is_required = field_spec.get("required", False)
            default = field_spec.get("default")
            
            # 필수 필드 체크
            if value is None:
                if is_required:
                    raise ValidationError(field_name, "필수 필드입니다.")
                if default is not None:
                    value = default
                else:
                    continue  # 선택적 필드이고 값이 없으면 스킵
            
            # 타입 변환
            try:
                converter = cls.TYPE_CONVERTERS.get(field_type, str)
                value = converter(value)
            except (ValueError, TypeError) as e:
                raise ValidationError(field_name, f"타입 변환 실패: {field_type} 타입이어야 합니다.")
            
            # 추가 검증 규칙 적용
            cls._validate_constraints(field_name, value, field_spec)
            
            validated[field_name] = value
        
        return validated
    
    @classmethod
    def _validate_constraints(cls, field_name: str, value: Any, spec: dict) -> None:
        """추가 검증 규칙 적용"""
        field_type = spec.get("type", "string")
        
        # 문자열 검증
        if field_type == "string" and isinstance(value, str):
            min_length = spec.get("min_length")
            max_length = spec.get("max_length")
            pattern = spec.get("pattern")
            
            if min_length is not None and len(value) < min_length:
                raise ValidationError(field_name, f"최소 {min_length}자 이상이어야 합니다.")
            
            if max_length is not None and len(value) > max_length:
                raise ValidationError(field_name, f"최대 {max_length}자까지 허용됩니다.")
            
            if pattern is not None and not re.match(pattern, value):
                raise ValidationError(field_name, f"패턴이 일치하지 않습니다: {pattern}")
        
        # 숫자 검증
        if field_type in ("int", "float") and isinstance(value, (int, float)):
            min_value = spec.get("min_value")
            max_value = spec.get("max_value")
            
            if min_value is not None and value < min_value:
                raise ValidationError(field_name, f"최소값은 {min_value}입니다.")
            
            if max_value is not None and value > max_value:
                raise ValidationError(field_name, f"최대값은 {max_value}입니다.")
        
        # enum 검증
        enum_values = spec.get("enum")
        if enum_values is not None and value not in enum_values:
            raise ValidationError(field_name, f"허용된 값: {enum_values}")

