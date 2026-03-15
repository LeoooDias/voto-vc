"""Shared utilities."""

_CAMARA_BASE = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao="


def url_camara_from_id_externo(id_externo: str | None) -> str | None:
    if id_externo and id_externo.startswith("camara_prop_"):
        return _CAMARA_BASE + id_externo.removeprefix("camara_prop_")
    return None
