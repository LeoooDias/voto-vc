from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, matching, parlamentares, partidos, proposicoes, questionario


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="voto.vc API",
    description="Ajudando eleitores brasileiros a encontrar políticos alinhados com seus valores",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parlamentares.router, prefix="/api/parlamentares", tags=["parlamentares"])
app.include_router(partidos.router, prefix="/api/partidos", tags=["partidos"])
app.include_router(proposicoes.router, prefix="/api/proposicoes", tags=["proposicoes"])
app.include_router(questionario.router, prefix="/api/vote", tags=["vote"])
app.include_router(matching.router, prefix="/api/matching", tags=["matching"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
