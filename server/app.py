"""Application composition; creating an app never enables demo implicitly."""
import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from .db import initialize, closing_connection
from .errors import DomainError
from .routes import router
from .seed import seed

ROOT = Path(__file__).resolve().parents[1]


def error_response(status, code, message):
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def create_app(db_path=None, demo=None, production=None):
    demo = os.getenv("TONGPING_DEMO", "0") == "1" if demo is None else demo
    production = os.getenv("TONGPING_ENV", "development") == "production" if production is None else production
    if production and demo:
        raise ValueError("Demo login is forbidden in production")
    path = Path(db_path or os.getenv("TONGPING_DB", str(ROOT / "data" / "tongping.sqlite")))
    initialize(path)
    with closing_connection(path) as db:
        if demo:
            seed(db)
        marker = db.execute("SELECT value FROM meta WHERE key='mode'").fetchone()
        if demo and (not marker or marker[0] != "demo"):
            raise ValueError("Demo must use a dedicated demo database")
        if production and marker and marker[0] == "demo":
            raise ValueError("A demo database cannot be opened in production")
    app = FastAPI(title="同频 API", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.db_path, app.state.demo = path, demo

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo payloads, login codes, or provider secrets in validation errors.
        return error_response(422, "VALIDATION_ERROR", "输入不符合接口要求，请检查必填项、长度和时间")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(exc.status_code, "HTTP_ERROR", "请求的资源或方法不可用")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logging.getLogger("tongping").error("Unhandled %s at %s", type(exc).__name__, request.url.path)
        return error_response(500, "INTERNAL_ERROR", "服务暂不可用，请稍后重试")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    app.include_router(router)
    if (ROOT / "web" / "index.html").exists():
        app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
    return app
