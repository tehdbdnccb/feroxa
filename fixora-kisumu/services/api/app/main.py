from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import settings
from .db import Base, engine
from .routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    if settings.environment == "production":
        if settings.jwt_secret == "change-me-in-production" or len(settings.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be a strong value in production")
        if not settings.session_cookie_secure:
            raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")
    yield


app = FastAPI(title=settings.app_name, version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
if settings.allowed_hosts_list != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)


@app.middleware("http")
async def security_headers_and_csrf(request: Request, call_next):
    unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
    cookie_auth = request.cookies.get(settings.session_cookie_name)
    bearer_auth = request.headers.get("Authorization", "")
    csrf_exempt = request.url.path in {
        "/v1/auth/login",
        "/v1/auth/register",
        "/v1/auth/logout",
        "/v1/payments/mpesa/callback",
    } or request.url.path.startswith("/v1/payments/mpesa/callback/")
    if unsafe and cookie_auth and not bearer_auth and not csrf_exempt:
        expected = request.cookies.get(settings.csrf_cookie_name)
        received = request.headers.get("X-CSRF-Token")
        if not expected or not received or not secrets_compare(expected, received):
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), geolocation=(self), microphone=()"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def secrets_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)


app.include_router(router)
