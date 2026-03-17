"""Shared utilities."""

_CAMARA_BASE = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao="
_SENADO_BASE = "https://www25.senado.leg.br/web/atividade/materias/-/materia/"


def url_proposicao(id_externo: str | None) -> str | None:
    """Gera URL da proposição na Câmara ou Senado a partir do id_externo."""
    if not id_externo:
        return None
    if id_externo.startswith("camara_prop_"):
        return _CAMARA_BASE + id_externo.removeprefix("camara_prop_")
    if id_externo.startswith("senado_mat_"):
        return _SENADO_BASE + id_externo.removeprefix("senado_mat_")
    return None
