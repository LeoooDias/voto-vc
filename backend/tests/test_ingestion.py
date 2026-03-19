from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.normalize import normalize_deputado, normalize_senador
from app.ingestion.sync import sync_parlamentares
from app.models.parlamentar import Parlamentar


def test_normalize_deputado(sample_deputado_raw):
    result = normalize_deputado(sample_deputado_raw)
    assert result["id_externo"] == "camara_12345"
    assert result["casa"] == "camara"
    assert result["nome_parlamentar"] == "Joao da Silva"
    assert result["nome_civil"] == "Joao Pereira da Silva"
    assert result["partido_sigla"] == "PT"
    assert result["uf"] == "SP"


def test_normalize_deputado_nome_civil_prefers_nome_civil():
    """nome_civil should use nomeCivil when available, not nome."""
    raw = {
        "id": 99,
        "nome": "Apelido Politico",
        "nomeCivil": "Nome Completo Real",
        "siglaPartido": "PT",
        "siglaUf": "RJ",
    }
    result = normalize_deputado(raw)
    assert result["nome_civil"] == "Nome Completo Real"
    assert result["nome_parlamentar"] == "Apelido Politico"


def test_normalize_deputado_nome_civil_fallback():
    """nome_civil should fall back to nome if nomeCivil is absent."""
    raw = {
        "id": 99,
        "nome": "Joao da Silva",
        "siglaPartido": "PT",
        "siglaUf": "RJ",
    }
    result = normalize_deputado(raw)
    assert result["nome_civil"] == "Joao da Silva"


def test_normalize_senador():
    raw = {
        "IdentificacaoParlamentar": {
            "CodigoParlamentar": "5678",
            "NomeCompletoParlamentar": "Maria Santos",
            "NomeParlamentar": "Maria",
            "SexoParlamentar": "F",
            "SiglaPartidoParlamentar": "PL",
            "UfParlamentar": "RJ",
            "UrlFotoParlamentar": "https://example.com/foto.jpg",
            "EmailParlamentar": "maria@senado.leg.br",
        },
        "MandatoAtual": {
            "UfParlamentar": "RJ",
        },
    }
    result = normalize_senador(raw)
    assert result["id_externo"] == "senado_5678"
    assert result["casa"] == "senado"
    assert result["nome_parlamentar"] == "Maria"
    assert result["partido_sigla"] == "PL"


class TestSyncParlamentares:
    """Tests for upsert logic in sync_parlamentares."""

    async def test_upsert_updates_legislatura_atual(self, db: AsyncSession):
        """Existing parlamentar should get legislatura_atual updated on re-sync."""
        # Insert initially
        data = [
            {
                "id_externo": "camara_999",
                "casa": "camara",
                "nome_civil": "Teste Civil",
                "nome_parlamentar": "Teste Parl",
                "uf": "SP",
                "partido_sigla": "PT",
                "legislatura_atual": True,
                "sexo": "M",
            }
        ]
        await sync_parlamentares(db, data)

        # Re-sync with legislatura_atual=False and updated fields
        data[0]["legislatura_atual"] = False
        data[0]["nome_civil"] = "Teste Civil Atualizado"
        data[0]["sexo"] = "F"
        data[0]["email"] = "novo@email.com"
        await sync_parlamentares(db, data)

        result = await db.execute(select(Parlamentar).where(Parlamentar.id_externo == "camara_999"))
        parl = result.scalar_one()
        assert parl.legislatura_atual is False
        assert parl.nome_civil == "Teste Civil Atualizado"
        assert parl.sexo == "F"
        assert parl.email == "novo@email.com"
