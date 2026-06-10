from fastapi import FastAPI

from src.core.security_headers import register_security_headers
from src.core.audit_middleware import register_audit_middleware
from src.core.rate_limit_middleware import register_global_rate_limit
from src.core.request_id_middleware import register_request_id
from src.core.cors import register_cors


def register_middlewares(app: FastAPI) -> None:
    register_security_headers(app)
    register_audit_middleware(app)
    register_global_rate_limit(app)
    register_request_id(app)
    register_cors(app)
