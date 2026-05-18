import re 
from typing import Annotated
from pydantic import AfterValidator, Field

def _validate_password_strength(v: str) -> str:
    if not re.search(r"[A-Z]", v):
        raise ValueError("must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("must contain at least one lowercase letter")
    if not re.search(r"[\d]", v):
        raise ValueError("must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("must contain at least one symbol")
    return v

StrongPassword = Annotated[
    str,
    Field(min_length=8, max_length=64),
    AfterValidator(_validate_password_strength)
]