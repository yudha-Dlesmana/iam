import pytest
from pydantic import ValidationError

from src.schemas.user_schema import UserUpdateRequest


# ═══════════════════════════════════
# AT_LEAST_ONE_FIELD — model_validator
# ═══════════════════════════════════

def test_update_request_raises_when_both_fields_none():
    with pytest.raises(ValidationError, match="At least one field"):
        UserUpdateRequest()


def test_update_request_valid_when_only_password():
    req = UserUpdateRequest(password="Newpass1!")

    assert req.password == "Newpass1!"
    assert req.role_id is None


def test_update_request_valid_when_only_role_id():
    req = UserUpdateRequest(role_id=2)

    assert req.role_id == 2
    assert req.password is None


def test_update_request_valid_when_both_set():
    req = UserUpdateRequest(password="Newpass1!", role_id=2)

    assert req.password == "Newpass1!"
    assert req.role_id == 2
