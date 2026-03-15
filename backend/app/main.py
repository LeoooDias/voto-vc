import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.core.exceptions import generic_exception_handler, http_exception_handler
from app.database import engine
from app.middleware import RequestIdMiddleware
from app.routers import auth, matching, parlamentares, partidos, proposicoes, questionario

# Structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="voto.vc API",
    description="Ajudando eleitores brasileiros a encontrar políticos alinhados com seus valores",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# State for slowapi
app.state.limiter = limiter

# Middleware (order matters — outermost first)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=429,
        content={
            "erro": "Muitas requisições. Tente novamente em alguns instantes.",
            "status": 429,
            "request_id": request_id,
        },
    )


# Routers
app.include_router(parlamentares.router, prefix="/api/parlamentares", tags=["parlamentares"])
app.include_router(partidos.router, prefix="/api/partidos", tags=["partidos"])
app.include_router(proposicoes.router, prefix="/api/proposicoes", tags=["proposicoes"])
app.include_router(questionario.router, prefix="/api/vote", tags=["vote"])
app.include_router(matching.router, prefix="/api/matching", tags=["matching"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


@app.get("/api/health")
async def health():
    """Health check with DB connectivity verification."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unavailable"},
        )
