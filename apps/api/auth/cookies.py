"""Refresh-token cookie handling.

The refresh token is delivered to browsers as an HttpOnly cookie so client-side
JavaScript can never read it — the single most effective mitigation against
token theft via XSS. These attributes are deliberately fixed constants rather
than configuration: every deployment wants the same hardened settings.

  HttpOnly       JS cannot read the cookie (XSS cannot exfiltrate it).
  Secure         Only sent over HTTPS. Browsers treat localhost as secure, so
                 this also holds in local development.
  SameSite=Lax   Not sent on cross-site POSTs, blunting CSRF. Lax (not Strict)
                 so a top-level navigation back to the app still carries it.
  Path=/auth     Scoped to the auth endpoints (login/refresh/logout); never
                 attached to ordinary API calls, shrinking its exposure.
"""

from fastapi import Response

from config import settings

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/auth"
_MAX_AGE_SECONDS = settings.refresh_token_expire_days * 24 * 60 * 60


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path=COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    # Path must match the one used when setting the cookie for the browser to
    # consider them the same cookie and drop it.
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
        path=COOKIE_PATH,
    )
