# backend/app/main.py

import logging
import sys
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db.database import init_db, close_db
from app.middleware.cors import add_cors_middleware
from app.routers import auth, agent, history, analytics, repos
from config.settings import settings

# ── Request ID context var ────────────────────────────────
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


# ── Logging setup ─────────────────────────────────────────
def setup_logging():
    """Configure logging based on environment."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        # Production: JSON format for structured logging
        try:
            from pythonjsonlogger import jsonlogger

            class CustomJsonFormatter(jsonlogger.JsonFormatter):
                def add_fields(self, log_record, record, message_dict):
                    super().add_fields(log_record, record, message_dict)
                    log_record["timestamp"] = record.created
                    log_record["level"] = record.levelname
                    log_record["logger"] = record.name
                    req_id = request_id_var.get()
                    if req_id:
                        log_record["request_id"] = req_id

            formatter = CustomJsonFormatter(
                "%(timestamp)s %(level)s %(name)s %(message)s"
            )
            handler.setFormatter(formatter)
        except ImportError:
            # Fallback to basic format if json logger not available
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
    else:
        # Development: human-readable format
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root_logger.addHandler(handler)


setup_logging()
logger = logging.getLogger(__name__)


# ── Rate Limiter ──────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────
    logger.info("Starting %s [%s]", settings.APP_NAME, settings.APP_ENV)

    if settings.is_production:
        # Run Alembic migrations automatically on every prod startup.
        # This is safe: `upgrade head` is idempotent when already at head.
        import subprocess
        import sys
        logger.info("Running Alembic migrations…")
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Alembic migration failed:\n%s", result.stderr)
            raise RuntimeError("Database migration failed — aborting startup")
        logger.info("Migrations complete:\n%s", result.stdout.strip())
    else:
        # Auto-create tables in dev — Alembic handles prod
        await init_db()
        logger.info("Database ready (dev auto-create)")

    logger.info("Backend startup complete")
    yield

    # ── Shutdown ──────────────────────────────────────────
    await close_db()
    logger.info("Backend shutdown complete")


# ── App factory ───────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="CI Healer Backend API",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Rate limiter state ────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Request ID middleware ─────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for log correlation."""
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# ── Middleware ────────────────────────────────────────────
add_cors_middleware(app)

# ── Routers ───────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(agent.router)
app.include_router(repos.router)
app.include_router(history.router)
app.include_router(analytics.router)


# ── Root + health ─────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "env": settings.APP_ENV,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "ai_engine_url": settings.AI_ENGINE_URL,
    }


# ── Global exception handler ──────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Entrypoint ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
