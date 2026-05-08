import pytest

from src.schemas.validators import Validators


# ═══════════════════════════════════
# VALID PASSWORDS
# ═══════════════════════════════════

def test_password_valid_with_letter_digit_symbol():
    assert Validators.password("Abcd1234!") == "Abcd1234!"


def test_password_valid_with_minimal_chars():
    assert Validators.password("a1!") == "a1!"


@pytest.mark.parametrize("symbol", list("!@#$%^&*()_+-=[]{}|;':\",./<>?"))
def test_password_valid_with_each_allowed_symbol(symbol):
    pwd = f"abc1{symbol}"

    assert Validators.password(pwd) == pwd


# ═══════════════════════════════════
# INVALID PASSWORDS
# ═══════════════════════════════════

def test_password_raises_when_missing_letter():
    with pytest.raises(ValueError, match="letter, number and symbol"):
        Validators.password("12345!")


def test_password_raises_when_missing_digit():
    with pytest.raises(ValueError, match="letter, number and symbol"):
        Validators.password("abcdef!")


def test_password_raises_when_missing_symbol():
    with pytest.raises(ValueError, match="letter, number and symbol"):
        Validators.password("abc1234")


def test_password_raises_when_only_letters():
    with pytest.raises(ValueError):
        Validators.password("abcdefgh")


def test_password_raises_when_only_digits():
    with pytest.raises(ValueError):
        Validators.password("12345678")


def test_password_raises_when_only_symbols():
    with pytest.raises(ValueError):
        Validators.password("!@#$%^&*")


# ═══════════════════════════════════
# OPTIONAL FLAG
# ═══════════════════════════════════

def test_password_none_required_raises():
    with pytest.raises(ValueError, match="Password is required"):
        Validators.password(None)


def test_password_none_optional_returns_none():
    assert Validators.password(None, optional=True) is None


def test_password_invalid_value_raises_even_when_optional():
    with pytest.raises(ValueError, match="letter, number and symbol"):
        Validators.password("invalid", optional=True)
