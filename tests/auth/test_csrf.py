from tests.conftest import REFRESH


async def test_refresh_cross_site_rejected(client):
    """A3: request lintas-situs (Sec-Fetch-Site: cross-site) ditolak 403 sebelum
    logika refresh dijalankan."""
    res = await client.post(REFRESH, headers={"Sec-Fetch-Site": "cross-site"})
    assert res.status_code == 403


async def test_refresh_unknown_origin_rejected(client):
    """A3: Origin di luar daftar (FRONTEND_URLs) ditolak 403."""
    res = await client.post(
        REFRESH,
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"},
    )
    assert res.status_code == 403


async def test_refresh_same_origin_passes_csrf(client):
    """A3: same-origin lolos CSRF — tanpa cookie jadi 401 (bukan 403),
    membuktikan guard tidak menolak request yang sah."""
    # client fixture mengirim Sec-Fetch-Site: same-origin secara default.
    res = await client.post(REFRESH)
    assert res.status_code == 401
