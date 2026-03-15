from app.ingestion.normalize import normalize_deputado, normalize_senador


def test_normalize_deputado(sample_deputado_raw):
    result = normalize_deputado(sample_deputado_raw)
    assert result["id_externo"] == "camara_12345"
    assert result["casa"] == "camara"
    assert result["nome_parlamentar"] == "Joao da Silva"
    assert result["partido_sigla"] == "PT"
    assert result["uf"] == "SP"


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
