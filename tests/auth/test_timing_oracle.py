from src.services.auth import _DUMMY_HASH
from tests.conftest import LOGIN


async def test_unknown_email_still_runs_verify_password(client, mocker):
    """A1: login dengan email tak terdaftar tetap memanggil verify_password
    (terhadap dummy hash) supaya waktu respons sama dengan jalur user-ada —
    menutup timing oracle / user enumeration."""
    spy = mocker.patch("src.services.auth.verify_password", return_value=False)

    res = await client.post(
        LOGIN, json={"email": "nobody@starter.com", "password": "whatever"}
    )

    assert res.status_code == 401
    spy.assert_called_once_with(_DUMMY_HASH, plain="whatever")
