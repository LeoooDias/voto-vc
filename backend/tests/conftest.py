from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, StaticPool, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import all models so metadata.create_all picks them up
import app.models  # noqa: F401
from app.models.base import Base, Casa, TipoVoto
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao, VotoParlamentar


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def engine():
    """Create an async in-memory SQLite engine for testing."""
    # Replace JSONB with JSON for SQLite compatibility before creating tables
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()

    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite needs special handling for enums — store as strings
    @event.listens_for(test_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture()
async def db(engine):
    """Create an async session for testing."""
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def client(engine):
    """Create an httpx AsyncClient with FastAPI app using test DB."""
    from app.database import get_db
    from app.main import app

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Data fixtures ──


@pytest.fixture()
async def test_partido(db: AsyncSession) -> Partido:
    partido = Partido(id=1, sigla="PT", nome="Partido dos Trabalhadores")
    db.add(partido)
    await db.commit()
    await db.refresh(partido)
    return partido


@pytest.fixture()
async def test_partido2(db: AsyncSession) -> Partido:
    partido = Partido(id=2, sigla="PL", nome="Partido Liberal")
    db.add(partido)
    await db.commit()
    await db.refresh(partido)
    return partido


@pytest.fixture()
async def test_parlamentar(db: AsyncSession, test_partido: Partido) -> Parlamentar:
    parlamentar = Parlamentar(
        id=1,
        id_externo="camara_101",
        casa=Casa.CAMARA,
        nome_civil="Maria da Silva",
        nome_parlamentar="Maria Silva",
        sexo="F",
        uf="SP",
        partido_id=test_partido.id,
        legislatura_atual=True,
    )
    db.add(parlamentar)
    await db.commit()
    await db.refresh(parlamentar)
    return parlamentar


@pytest.fixture()
async def test_parlamentar2(db: AsyncSession, test_partido2: Partido) -> Parlamentar:
    parlamentar = Parlamentar(
        id=2,
        id_externo="camara_102",
        casa=Casa.CAMARA,
        nome_civil="Jose dos Santos",
        nome_parlamentar="Jose Santos",
        sexo="M",
        uf="SP",
        partido_id=test_partido2.id,
        legislatura_atual=True,
    )
    db.add(parlamentar)
    await db.commit()
    await db.refresh(parlamentar)
    return parlamentar


@pytest.fixture()
async def test_proposicao(db: AsyncSession) -> Proposicao:
    proposicao = Proposicao(
        id=1,
        id_externo="camara_prop_1001",
        casa_origem=Casa.CAMARA,
        tipo="PL",
        numero=100,
        ano=2025,
        ementa="Projeto de lei sobre educacao publica",
        resumo_cidadao="Melhora a educacao publica no Brasil",
        tema="educacao",
        relevancia_score=0.9,
    )
    db.add(proposicao)
    await db.commit()
    await db.refresh(proposicao)
    return proposicao


@pytest.fixture()
async def test_proposicao2(db: AsyncSession) -> Proposicao:
    proposicao = Proposicao(
        id=2,
        id_externo="camara_prop_1002",
        casa_origem=Casa.CAMARA,
        tipo="PEC",
        numero=200,
        ano=2025,
        ementa="Emenda constitucional sobre saude",
        resumo_cidadao="Amplia investimentos em saude",
        tema="saude",
        relevancia_score=0.85,
    )
    db.add(proposicao)
    await db.commit()
    await db.refresh(proposicao)
    return proposicao


@pytest.fixture()
async def test_proposicao3(db: AsyncSession) -> Proposicao:
    proposicao = Proposicao(
        id=3,
        id_externo="camara_prop_1003",
        casa_origem=Casa.CAMARA,
        tipo="PL",
        numero=300,
        ano=2025,
        ementa="Projeto sobre meio ambiente",
        resumo_cidadao="Protege florestas nativas",
        tema="meio_ambiente",
        relevancia_score=0.8,
    )
    db.add(proposicao)
    await db.commit()
    await db.refresh(proposicao)
    return proposicao


@pytest.fixture()
async def test_votacao(db: AsyncSession, test_proposicao: Proposicao) -> Votacao:
    votacao = Votacao(
        id=1,
        id_externo="camara_vot_1",
        proposicao_id=test_proposicao.id,
        casa=Casa.CAMARA,
        data=datetime(2025, 6, 15, 14, 0),
        descricao="Votacao do PL 100/2025",
        resultado="Aprovado",
        total_sim=300,
        total_nao=150,
        total_abstencao=10,
    )
    db.add(votacao)
    await db.commit()
    await db.refresh(votacao)
    return votacao


@pytest.fixture()
async def test_votacao2(db: AsyncSession, test_proposicao2: Proposicao) -> Votacao:
    votacao = Votacao(
        id=2,
        id_externo="camara_vot_2",
        proposicao_id=test_proposicao2.id,
        casa=Casa.CAMARA,
        data=datetime(2025, 7, 20, 10, 0),
        descricao="Votacao da PEC 200/2025",
        resultado="Aprovado",
        total_sim=350,
        total_nao=100,
        total_abstencao=5,
    )
    db.add(votacao)
    await db.commit()
    await db.refresh(votacao)
    return votacao


@pytest.fixture()
async def test_votacao3(db: AsyncSession, test_proposicao3: Proposicao) -> Votacao:
    votacao = Votacao(
        id=3,
        id_externo="camara_vot_3",
        proposicao_id=test_proposicao3.id,
        casa=Casa.CAMARA,
        data=datetime(2025, 8, 10, 16, 0),
        descricao="Votacao do PL 300/2025",
        resultado="Rejeitado",
        total_sim=200,
        total_nao=250,
        total_abstencao=15,
    )
    db.add(votacao)
    await db.commit()
    await db.refresh(votacao)
    return votacao


@pytest.fixture()
async def test_voto_parlamentar(
    db: AsyncSession,
    test_votacao: Votacao,
    test_parlamentar: Parlamentar,
) -> VotoParlamentar:
    voto = VotoParlamentar(
        id=1,
        votacao_id=test_votacao.id,
        parlamentar_id=test_parlamentar.id,
        voto=TipoVoto.SIM,
        partido_na_epoca="PT",
    )
    db.add(voto)
    await db.commit()
    await db.refresh(voto)
    return voto


@pytest.fixture
def sample_ementa():
    return (
        "Altera a legislacao tributaria para reduzir aliquota do ICMS"
        " sobre produtos da cesta basica"
    )


@pytest.fixture
def sample_deputado_raw():
    return {
        "id": 12345,
        "nome": "Joao da Silva",
        "nomeCivil": "Joao Pereira da Silva",
        "siglaPartido": "PT",
        "siglaUf": "SP",
        "urlFoto": "https://example.com/foto.jpg",
        "email": "joao@camara.leg.br",
        "cpf": "12345678901",
        "sexo": "M",
    }
