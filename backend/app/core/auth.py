"""Cloudflare Access authentication middleware and helpers."""

from dataclasses import dataclass

import httpx
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


@dataclass
class Actor:
    email: str
    name: str
    roles: list[str]


class CloudflareAccessMiddleware(BaseHTTPMiddleware):
    """Validates Cloudflare Access JWT or falls back to dev auth."""

    SKIP_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            request.state.actor = None
            return await call_next(request)

        actor = await self._resolve_actor(request)
        if actor is None:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        request.state.actor = actor
        return await call_next(request)

    async def _resolve_actor(self, request: Request) -> Actor | None:
        if settings.CF_ACCESS_REQUIRED:
            return await self._validate_cf_access(request)

        # Dev mode: check CF headers first, then fall back
        cf_email = request.headers.get("Cf-Access-Authenticated-User-Email")
        if cf_email:
            name = cf_email.split("@")[0].replace(".", " ").title()
            return Actor(email=cf_email, name=name, roles=["admin"])

        return Actor(
            email=settings.DEV_AUTH_EMAIL,
            name=settings.DEV_AUTH_NAME,
            roles=["admin"],
        )

    async def _validate_cf_access(self, request: Request) -> Actor | None:
        jwt_token = request.headers.get("Cf-Access-Jwt-Assertion")
        if not jwt_token:
            return None

        # Validate JWT against Cloudflare certs
        certs_url = f"https://{settings.CF_ACCESS_TEAM_DOMAIN}.cloudflareaccess.com/cdn-cgi/access/certs"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(certs_url)
                resp.raise_for_status()
        except httpx.HTTPError:
            return None

        cf_email = request.headers.get("Cf-Access-Authenticated-User-Email")
        if not cf_email:
            return None

        name = cf_email.split("@")[0].replace(".", " ").title()
        return Actor(email=cf_email, name=name, roles=["admin"])
