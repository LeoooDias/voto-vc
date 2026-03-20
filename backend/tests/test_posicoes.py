"""Tests for posicoes service — expansion logic and inference."""

from app.services.posicoes import expandir_posicoes_para_respostas


def test_expansion_basic():
    """Posição com 3 props, peso=1.0 → cada prop peso=0.33."""
    posicao_respostas = [{"posicao_id": 1, "voto": "sim", "peso": 1.0}]
    posicoes_map = {
        1: [
            {"proposicao_id": 10, "direcao": "sim"},
            {"proposicao_id": 20, "direcao": "sim"},
            {"proposicao_id": 30, "direcao": "sim"},
        ]
    }
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map)
    assert len(result) == 3
    for r in result:
        assert r["voto"] == "sim"
        assert abs(r["peso"] - 1.0 / 3) < 0.001


def test_expansion_direcao_invertida():
    """direcao=nao flips the vote."""
    posicao_respostas = [{"posicao_id": 1, "voto": "sim", "peso": 1.0}]
    posicoes_map = {
        1: [
            {"proposicao_id": 10, "direcao": "nao"},
        ]
    }
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map)
    assert len(result) == 1
    assert result[0]["voto"] == "nao"  # flipped


def test_expansion_nao_with_direcao_nao():
    """voto=nao + direcao=nao → prop_voto=sim."""
    posicao_respostas = [{"posicao_id": 1, "voto": "nao", "peso": 0.5}]
    posicoes_map = {
        1: [
            {"proposicao_id": 10, "direcao": "nao"},
        ]
    }
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map)
    assert result[0]["voto"] == "sim"


def test_expansion_override():
    """Override substitui voto virtual por voto direto."""
    posicao_respostas = [{"posicao_id": 1, "voto": "sim", "peso": 1.0}]
    posicoes_map = {
        1: [
            {"proposicao_id": 10, "direcao": "sim"},
            {"proposicao_id": 20, "direcao": "sim"},
        ]
    }
    overrides = {10: {"proposicao_id": 10, "voto": "nao", "peso": 1.0}}
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map, overrides)
    assert len(result) == 2
    r10 = next(r for r in result if r["proposicao_id"] == 10)
    assert r10["voto"] == "nao"
    assert r10["peso"] == 1.0  # override peso, not normalized


def test_expansion_neutro():
    """Neutro (peso=0) gera votos com peso 0."""
    posicao_respostas = [{"posicao_id": 1, "voto": "sim", "peso": 0.0}]
    posicoes_map = {
        1: [
            {"proposicao_id": 10, "direcao": "sim"},
            {"proposicao_id": 20, "direcao": "sim"},
        ]
    }
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map)
    assert len(result) == 2
    for r in result:
        assert r["peso"] == 0.0


def test_expansion_pular():
    """Pular propagates as pular."""
    posicao_respostas = [{"posicao_id": 1, "voto": "pular", "peso": 1.0}]
    posicoes_map = {
        1: [
            {"proposicao_id": 10, "direcao": "sim"},
        ]
    }
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map)
    assert result[0]["voto"] == "pular"


def test_expansion_dedup():
    """Same proposicao in two positions → only appears once."""
    posicao_respostas = [
        {"posicao_id": 1, "voto": "sim", "peso": 1.0},
        {"posicao_id": 2, "voto": "nao", "peso": 1.0},
    ]
    posicoes_map = {
        1: [{"proposicao_id": 10, "direcao": "sim"}],
        2: [{"proposicao_id": 10, "direcao": "sim"}],  # same prop
    }
    result = expandir_posicoes_para_respostas(posicao_respostas, posicoes_map)
    assert len(result) == 1  # deduped
