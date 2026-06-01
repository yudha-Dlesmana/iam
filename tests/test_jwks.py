from src.core.keys import all_public_keys


async def test_jwks_endpoint_shape(client):
    res = await client.get("/.well-known/jwks.json")
    assert res.status_code == 200
    body = res.json()
    assert "keys" in body
    assert isinstance(body["keys"], list)
    assert len(body["keys"]) >= 1


async def test_jwks_emits_every_loaded_kid(client):
    res = await client.get("/.well-known/jwks.json")
    kids_in_jwks = {k["kid"] for k in res.json()["keys"]}
    assert kids_in_jwks == set(all_public_keys().keys())


async def test_jwks_each_entry_has_rs256_sig(client):
    res = await client.get("/.well-known/jwks.json")
    for key in res.json()["keys"]:
        assert key["alg"] == "RS256"
        assert key["use"] == "sig"
        assert key["kty"] == "RSA"
        assert "n" in key and "e" in key
        assert "kid" in key


async def test_jwks_is_public(client):
    res = await client.get("/.well-known/jwks.json")
    assert res.status_code == 200
