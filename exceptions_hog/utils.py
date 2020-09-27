from enum import Enum
from typing import Any, Callable

from django.utils.encoding import force_str


def ensure_string(func: Callable) -> Callable:
    def function_wrapper(*args, **kwargs) -> str:
        return_value: Any = func(*args, **kwargs)
        if isinstance(return_value, Enum):
            return force_str(return_value.value)
        return force_str(return_value)

    return function_wrapper
