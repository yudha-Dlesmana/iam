import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError

from src.core.exception_handler import (
    database_error_handler,
    http_exception_handler,
    integrity_error_handler,
    internal_error_handler,
    operational_error_handler,
    register_exception_handlers,
    validation_error_handler,
)


def parse_body(response):
    return json.loads(bytes(response.body).decode())


@pytest.fixture
def request_mock():
    req = MagicMock()
    req.method = "GET"
    req.url.path = "/test"
    return req


def make_integrity_error(code: int, msg: str) -> IntegrityError:
    orig = MagicMock()
    orig.args = (code, msg)
    return IntegrityError(statement="...", params={}, orig=orig)


# ═══════════════════════════════════
# HTTP EXCEPTION
# ═══════════════════════════════════

async def test_http_exception_handler_formats_response(request_mock):
    exc = HTTPException(status_code=404, detail="Not found")

    response = await http_exception_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 404
    assert body == {"success": False, "message": "Not found", "data": None}


# ═══════════════════════════════════
# VALIDATION ERROR
# ═══════════════════════════════════

async def test_validation_error_handler_joins_errors(request_mock):
    exc = RequestValidationError(
        errors=[
            {"loc": ("body", "email"), "msg": "field required", "type": "missing"},
            {"loc": ("body", "password"), "msg": "too short", "type": "value_error"},
        ]
    )

    response = await validation_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 422
    assert "body -> email: field required" in body["message"]
    assert "body -> password: too short" in body["message"]
    assert body["success"] is False


# ═══════════════════════════════════
# INTEGRITY ERROR — duplicate (1062)
# ═══════════════════════════════════

async def test_integrity_duplicate_extracts_column_name(request_mock):
    exc = make_integrity_error(
        1062,
        "Duplicate entry 'a@x.com' for key 'users.email'",
    )

    response = await integrity_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 409
    assert body["message"] == "email already exists"


async def test_integrity_duplicate_falls_back_to_field_when_regex_no_match(request_mock):
    exc = make_integrity_error(1062, "Duplicate entry without key clause")

    response = await integrity_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 409
    assert body["message"] == "field already exists"


# ═══════════════════════════════════
# INTEGRITY ERROR — foreign key (1452)
# ═══════════════════════════════════

async def test_integrity_foreign_key_extracts_column_name(request_mock):
    exc = make_integrity_error(
        1452,
        "Cannot add or update a child row: a foreign key constraint fails "
        "FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`)",
    )

    response = await integrity_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 404
    assert body["message"] == "role_id not found"


async def test_integrity_foreign_key_falls_back_to_field(request_mock):
    exc = make_integrity_error(1452, "FK constraint failed without column info")

    response = await integrity_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 404
    assert body["message"] == "field not found"


# ═══════════════════════════════════
# INTEGRITY ERROR — fallback
# ═══════════════════════════════════

async def test_integrity_unknown_code_returns_generic_conflict(request_mock):
    exc = make_integrity_error(9999, "Some other integrity issue")

    response = await integrity_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 409
    assert body["message"] == "Conflict"


async def test_integrity_no_orig_returns_generic_conflict(request_mock):
    exc = IntegrityError(statement="...", params={}, orig=None)

    response = await integrity_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 409
    assert body["message"] == "Conflict"


# ═══════════════════════════════════
# OPERATIONAL & DATABASE ERROR
# ═══════════════════════════════════

async def test_operational_error_returns_503(request_mock):
    exc = OperationalError(statement="...", params={}, orig=Exception("conn refused"))

    response = await operational_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 503
    assert body["message"] == "Database unavailable"


async def test_database_error_returns_503(request_mock):
    exc = DatabaseError(statement="...", params={}, orig=Exception("db error"))

    response = await database_error_handler(request_mock, exc)
    body = parse_body(response)

    assert response.status_code == 503
    assert body["message"] == "Database error"


# ═══════════════════════════════════
# INTERNAL ERROR — dev vs prod
# ═══════════════════════════════════

async def test_internal_error_exposes_detail_in_development(request_mock):
    exc = ValueError("secret stack trace")

    with patch("src.core.exception_handler.settings") as mock_settings:
        mock_settings.ENV = "development"
        response = await internal_error_handler(request_mock, exc)

    body = parse_body(response)

    assert response.status_code == 500
    assert body["message"] == "Internal server error"
    assert body["data"] == "secret stack trace"


async def test_internal_error_hides_detail_in_production(request_mock):
    exc = ValueError("secret stack trace")

    with patch("src.core.exception_handler.settings") as mock_settings:
        mock_settings.ENV = "production"
        response = await internal_error_handler(request_mock, exc)

    body = parse_body(response)

    assert response.status_code == 500
    assert body["message"] == "Internal server error"
    assert body["data"] is None


# ═══════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════

def test_register_exception_handlers_registers_all_handlers():
    app = FastAPI()
    register_exception_handlers(app)

    registered = app.exception_handlers

    assert HTTPException in registered
    assert RequestValidationError in registered
    assert IntegrityError in registered
    assert OperationalError in registered
    assert DatabaseError in registered
    assert Exception in registered
