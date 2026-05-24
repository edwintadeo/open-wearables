from unittest.mock import MagicMock

from app.schemas.enums import ProviderName
from app.services.providers.withings.oauth import WithingsOAuth


def _oauth() -> WithingsOAuth:
    return WithingsOAuth(
        user_repo=MagicMock(),
        connection_repo=MagicMock(),
        provider_name=ProviderName.WITHINGS.value,
        api_base_url="https://wbsapi.withings.net",
    )


def test_endpoints() -> None:
    endpoints = _oauth().endpoints
    assert endpoints.authorize_url == "https://account.withings.com/oauth2_user/authorize2"
    assert endpoints.token_url == "https://wbsapi.withings.net/v2/oauth2"


def test_token_request_includes_withings_action() -> None:
    data, headers = _oauth()._prepare_token_request("code-123", None)
    assert data["action"] == "requesttoken"
    assert data["grant_type"] == "authorization_code"
    assert data["code"] == "code-123"
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"


def test_refresh_request_includes_withings_action() -> None:
    data, headers = _oauth()._prepare_refresh_request("refresh-123")
    assert data["action"] == "requesttoken"
    assert data["grant_type"] == "refresh_token"
    assert data["refresh_token"] == "refresh-123"
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"


def test_provider_user_info_extracts_userid_and_scope() -> None:
    token_response = MagicMock()
    token_response.model_extra = {"userid": 12345}
    token_response.scope = "user.metrics,user.activity"
    result = _oauth()._get_provider_user_info(token_response, "internal-user")
    assert result["user_id"] == "12345"
    assert result["scope"] == "user.metrics,user.activity"
