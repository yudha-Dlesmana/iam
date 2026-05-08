import pytest
from pydantic import ValidationError

from src.core.config import Settings


REQUIRED_FIELDS = {
    "FRONTEND_URL": "https://app.example.com",
    "FRONTEND_URL_DEV": "http://localhost:3000",
    "DB_URL": "sqlite:///test.db",
    "REDIS_URL": "redis://localhost:6379",
    "JWT_SECRET_KEY": "test-secret",
    "GOOGLE_CLIENT_ID": "google-id",
    "GOOGLE_CLIENT_SECRET": "google-secret",
    "GOOGLE_REDIRECT_URI": "https://example.com/callback",
}


def make_settings(**overrides) -> Settings:
    data = {**REQUIRED_FIELDS, **overrides}
    return Settings(_env_file=None, **data)


# ═══════════════════════════════════
# DEFAULTS — verify default values applied
# ═══════════════════════════════════

def test_defaults_applied_when_not_set():
    s = make_settings()

    assert s.ENV == "development"
    assert s.PORT == 8000
    assert s.HOST == "0.0.0.0"
    assert s.JWT_ALGORITHM == "HS256"
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert s.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert s.TEST_DB_URL is None


def test_overrides_replace_defaults():
    s = make_settings(ENV="production", PORT=9000, JWT_ALGORITHM="RS256")

    assert s.ENV == "production"
    assert s.PORT == 9000
    assert s.JWT_ALGORITHM == "RS256"


# ═══════════════════════════════════
# REQUIRED FIELDS — missing field validation
# ═══════════════════════════════════

@pytest.mark.parametrize("missing_field", list(REQUIRED_FIELDS.keys()))
def test_required_field_raises_validation_error(missing_field):
    data = {k: v for k, v in REQUIRED_FIELDS.items() if k != missing_field}

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, **data)

    assert missing_field in str(exc.value)


# ═══════════════════════════════════
# OPTIONAL FIELDS — can be overridden
# ═══════════════════════════════════

def test_test_db_url_can_be_set():
    s = make_settings(TEST_DB_URL="sqlite:///mytest.db")

    assert s.TEST_DB_URL == "sqlite:///mytest.db"


# ═══════════════════════════════════
# IS_PRODUCTION — property logic
# ═══════════════════════════════════

def test_is_production_true_when_env_production():
    s = make_settings(ENV="production")

    assert s.is_production is True


def test_is_production_false_when_env_development():
    s = make_settings(ENV="development")

    assert s.is_production is False


def test_is_production_false_for_other_envs():
    s = make_settings(ENV="staging")

    assert s.is_production is False


# ═══════════════════════════════════
# VALIDATION & COERCION — type handling
# ═══════════════════════════════════

def test_port_coerced_from_string():
    s = make_settings(PORT="9090")

    assert s.PORT == 9090
    assert isinstance(s.PORT, int)


def test_port_invalid_type_raises_validation_error():
    with pytest.raises(ValidationError):
        make_settings(PORT="not-a-number")


# ═══════════════════════════════════
# MODEL CONFIG — extra="ignore"
# ═══════════════════════════════════

def test_extra_fields_ignored():
    s = make_settings(UNKNOWN_VAR="anything")

    assert not hasattr(s, "UNKNOWN_VAR")
