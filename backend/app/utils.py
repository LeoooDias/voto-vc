"""Shared utilities."""

from urllib.parse import quote

_CAMARA_FICHA = (
    "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao="
)
_CAMARA_BUSCA = "https://www.camara.leg.br/propostas-legislativas/busca?termo="
_SENADO_FICHA = "https://www25.senado.leg.br/web/atividade/materias/-/materia/"
_SENADO_BUSCA = (
    "https://www25.senado.leg.br/web/atividade/materias?"
    "p_p_id=materia_WAR_atividadeportlet&tipo={tipo}&numero={numero}&ano={ano}"
)


def url_proposicao(id_externo: str | None) -> str | None:
    """Gera URL da proposição na Câmara ou Senado a partir do id_externo."""
    if not id_externo:
        return None
    if id_externo.startswith("camara_prop_"):
        return _CAMARA_FICHA + id_externo.removeprefix("camara_prop_")
    if id_externo.startswith("senado_mat_"):
        return _SENADO_FICHA + id_externo.removeprefix("senado_mat_")
    return None


def urls_por_casa(
    id_externo: str | None,
    tipo: str | None = None,
    numero: int | None = None,
    ano: int | None = None,
) -> dict[str, str | None]:
    """Gera URLs para Câmara e Senado.

    Usa URL direta quando temos o id, e URL de busca como fallback.
    """
    camara_url: str | None = None
    senado_url: str | None = None

    if id_externo:
        if id_externo.startswith("camara_prop_"):
            camara_url = _CAMARA_FICHA + id_externo.removeprefix("camara_prop_")
        elif id_externo.startswith("senado_mat_"):
            senado_url = _SENADO_FICHA + id_externo.removeprefix("senado_mat_")

    # Fallback: busca por tipo/numero/ano
    if tipo and numero and ano:
        if not camara_url:
            termo = quote(f"{tipo} {numero}/{ano}")
            camara_url = _CAMARA_BUSCA + termo
        if not senado_url:
            senado_url = _SENADO_BUSCA.format(tipo=tipo, numero=numero, ano=ano)

    return {"camara": camara_url, "senado": senado_url}
