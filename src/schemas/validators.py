import re 
from typing import Annotated
from pydantic import AfterValidator, Field

def _validate_password_strength(v: str) -> str:
    if not re.search(r"[A-Z]", v):
        raise ValueError("uppercase")
    if not re.search(r"[a-z]", v):
        raise ValueError('lowercase')
    if not re.search(r"[\d]", v):
        raise ValueError('number')
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("symbol")
    return v

StrongPassword = Annotated[
    str,
    Field(min_length=8, max_length=64),
    AfterValidator(_validate_password_strength)
]