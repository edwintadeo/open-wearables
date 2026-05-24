import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.database import DbSession
from app.config import settings
from app.schemas.auth import AuthenticationMethod
from app.schemas.enums import ProviderName
from app.schemas.model_crud.credentials import (
    OAuthTokenResponse,
    ProviderCredentials,
    ProviderEndpoints,
)
from app.services.providers.templates.base_oauth import BaseOAuthTemplate
from app.utils.structured_logging import log_structured

logger = logging.getLogger(__name__)


class WithingsOAuth(BaseOAuthTemplate):
    """Withings OAuth 2.0 implementation.

    Withings returns OAuth token data nested under a `body` key and requires
    `action=requesttoken` on token and refresh requests, so the default
    Open Wearables OAuth token exchange is intentionally overridden.
    """

    auth_method: AuthenticationMethod = AuthenticationMethod.BODY

    @property
    def endpoints(self) -> ProviderEndpoints:
        return ProviderEndpoints(
            authorize_url="https://account.withings.com/oauth2_user/authorize2",
            token_url=f"{self.api_base_url}/v2/oauth2",
        )

    @property
    def credentials(self) -> ProviderCredentials:
        return ProviderCredentials(
            client_id=settings.withings_client_id or "",
            client_secret=(
                settings.withings_client_secret.get_secret_value() if settings.withings_client_secret else ""
            ),
            redirect_uri=settings.oauth_redirect_uri(ProviderName.WITHINGS),
            default_scope=settings.withings_default_scope,
        )

    def _prepare_token_request(self, code: str, code_verifier: str | None) -> tuple[dict[str, Any], dict[str, str]]:
        token_data = {
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "code": code,
            "redirect_uri": self.credentials.redirect_uri,
        }
        return token_data, {"Content-Type": "application/x-www-form-urlencoded"}

    def _prepare_refresh_request(self, refresh_token: str) -> tuple[dict[str, Any], dict[str, str]]:
        token_data = {
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "refresh_token": refresh_token,
        }
        return token_data, {"Content-Type": "application/x-www-form-urlencoded"}

    def _exchange_token(self, code: str, code_verifier: str | None) -> OAuthTokenResponse:
        data, headers = self._prepare_token_request(code, code_verifier)
        return self._request_token(data, headers, "exchange_token")

    def refresh_access_token(
        self,
        db: DbSession,
        user_id: UUID,
        refresh_token: str,
    ) -> OAuthTokenResponse:
        data, headers = self._prepare_refresh_request(refresh_token)
        token_response = self._request_token(data, headers, "refresh_token")

        connection = self.connection_repo.get_by_user_and_provider(db, user_id, self.provider_name)
        if connection:
            self.connection_repo.update_tokens(
                db,
                connection,
                token_response.access_token,
                token_response.refresh_token or refresh_token,
                token_response.expires_in,
            )
        return token_response

    def _request_token(self, data: dict[str, Any], headers: dict[str, str], task: str) -> OAuthTokenResponse:
        try:
            response = httpx.post(self.endpoints.token_url, data=data, headers=headers, timeout=30.0)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status not in (0, "0", None):
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Withings token error: {payload.get('error') or payload}",
                )
            body = payload.get("body", payload)
            return OAuthTokenResponse.model_validate(body)
        except HTTPException:
            raise
        except httpx.HTTPStatusError as e:
            log_structured(
                logger,
                "error",
                f"Withings OAuth HTTP error: {e.response.text}",
                provider=self.provider_name,
                task=task,
                status_code=e.response.status_code,
            )
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Withings OAuth error: {e.response.text}",
            )
        except Exception as e:
            log_structured(
                logger,
                "error",
                f"Withings OAuth request failed: {e}",
                provider=self.provider_name,
                task=task,
            )
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Withings OAuth failed: {str(e)}")

    def _get_provider_user_info(self, token_response: OAuthTokenResponse, user_id: str) -> dict[str, str | None]:
        provider_user_id = token_response.model_extra.get("userid") if token_response.model_extra else None
        scope = token_response.scope
        return {
            "user_id": str(provider_user_id) if provider_user_id is not None else None,
            "username": None,
            "scope": str(scope) if scope is not None else None,
        }
