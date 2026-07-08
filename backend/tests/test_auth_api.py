from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.modules.auth.security import hash_password


def test_auth_disabled_allows_existing_api_without_token(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "authEnabled": False,
        "authenticated": True,
        "username": None,
    }
    get_settings.cache_clear()


def test_auth_enabled_rejects_protected_api_without_token(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD_HASH", hash_password("secret"))
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "test-secret")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/options")

    assert response.status_code == 401
    assert response.json()["errorCode"] == "AUTHENTICATION_REQUIRED"
    get_settings.cache_clear()


def test_login_returns_token_and_token_authenticates_request(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD_HASH", hash_password("secret"))
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "test-secret")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "secret"},
        )
        assert login.status_code == 200
        token = login.json()["accessToken"]

        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert me.status_code == 200
    assert me.json() == {
        "authEnabled": True,
        "authenticated": True,
        "username": "admin",
    }
    get_settings.cache_clear()


def test_login_rejects_invalid_password(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD_HASH", hash_password("secret"))
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "test-secret")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )

    assert response.status_code == 401
    assert response.json()["errorCode"] == "AUTHENTICATION_FAILED"
    get_settings.cache_clear()
