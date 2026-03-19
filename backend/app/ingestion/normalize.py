"""Transform raw API data from Câmara and Senado into unified model-ready dicts."""

# Prepositions and articles that stay lowercase in Brazilian names
_LOWERCASE_PARTS = {"de", "da", "do", "dos", "das", "e", "di", "del"}


def normalize_nome(nome: str) -> str:
    """Title-case a Brazilian name, keeping prepositions lowercase."""
    if not nome:
        return nome
    parts = nome.strip().split()
    result = []
    for i, part in enumerate(parts):
        lower = part.lower()
        if i > 0 and lower in _LOWERCASE_PARTS:
            result.append(lower)
        else:
            result.append(part.capitalize())
    return " ".join(result)


def _normalize_sexo(valor: str | None) -> str | None:
    if not valor:
        return None
    valor = valor.strip().upper()
    if valor.startswith("M"):
        return "M"
    if valor.startswith("F"):
        return "F"
    return valor[0] if valor else None


def normalize_deputado(raw: dict) -> dict:
    return {
        "id_externo": f"camara_{raw['id']}",
        "casa": "camara",
        "nome_civil": normalize_nome(raw.get("nomeCivil", raw.get("nome", ""))),
        "nome_parlamentar": normalize_nome(raw.get("nome", "")),
        "cpf": raw.get("cpf"),
        "sexo": _normalize_sexo(raw.get("sexo")),
        "uf": raw.get("siglaUf", ""),
        "foto_url": raw.get("urlFoto"),
        "email": raw.get("email"),
        "partido_sigla": raw.get("siglaPartido", ""),
        "legislatura_atual": True,
        "dados_brutos": raw,
    }


def normalize_senador(raw: dict) -> dict:
    identidade = raw.get("IdentificacaoParlamentar", {})
    mandato = raw.get("Mandato", raw.get("MandatoAtual", {}))
    return {
        "id_externo": f"senado_{identidade.get('CodigoParlamentar', '')}",
        "casa": "senado",
        "nome_civil": normalize_nome(identidade.get("NomeCompletoParlamentar", "")),
        "nome_parlamentar": normalize_nome(identidade.get("NomeParlamentar", "")),
        "sexo": _normalize_sexo(identidade.get("SexoParlamentar")),
        "uf": mandato.get("UfParlamentar", identidade.get("UfParlamentar", "")),
        "foto_url": identidade.get("UrlFotoParlamentar"),
        "email": identidade.get("EmailParlamentar"),
        "partido_sigla": identidade.get("SiglaPartidoParlamentar", ""),
        "legislatura_atual": True,
        "dados_brutos": raw,
    }


def normalize_voto_camara(raw: dict, votacao_id: str) -> dict:
    deputado = raw.get("deputado_", {})
    return {
        "parlamentar_id_externo": f"camara_{deputado.get('id', '')}",
        "votacao_id_externo": f"camara_{votacao_id}",
        "voto": _map_voto_camara(raw.get("tipoVoto", "")),
        "partido_na_epoca": deputado.get("siglaPartido"),
        "dados_brutos": raw,
    }


def normalize_votacao_camara(raw: dict) -> dict:
    return {
        "id_externo": f"camara_{raw['id']}",
        "casa": "camara",
        "data": raw.get("dataHoraRegistro") or raw.get("data"),
        "descricao": raw.get("descricao"),
        "resultado": str(raw.get("aprovacao", "")) if raw.get("aprovacao") is not None else None,
        "dados_brutos": raw,
    }


def normalize_votacao_senado(raw: dict) -> dict:
    """Transforma votação da nova API do Senado (/votacao?ano=)."""
    return {
        "id_externo": f"senado_{raw['codigoSessaoVotacao']}",
        "casa": "senado",
        "data": raw.get("dataSessao"),
        "descricao": raw.get("descricaoVotacao"),
        "resultado": raw.get("resultadoVotacao"),
        "total_sim": raw.get("totalVotosSim", 0),
        "total_nao": raw.get("totalVotosNao", 0),
        "total_abstencao": raw.get("totalVotosAbstencao", 0),
        "dados_brutos": raw,
        # Metadados para linkagem com proposições existentes
        "sigla_tipo": raw.get("sigla"),  # PL, PEC, PLP...
        "numero": raw.get("numero"),
        "ano": raw.get("ano"),
        "codigo_materia": raw.get("codigoMateria"),
        "ementa": raw.get("ementa"),
    }


def normalize_voto_senado(raw: dict, votacao_id_externo: str) -> dict:
    """Transforma voto individual da nova API do Senado."""
    return {
        "parlamentar_id_externo": f"senado_{raw['codigoParlamentar']}",
        "votacao_id_externo": votacao_id_externo,
        "voto": _map_voto_senado(raw.get("siglaVotoParlamentar", "")),
        "partido_na_epoca": raw.get("siglaPartidoParlamentar"),
        "dados_brutos": raw,
    }


def _map_voto_senado(voto: str) -> str:
    mapping = {
        "Sim": "sim",
        "Não": "nao",
        "Abstenção": "abstencao",
        "P-NRV": "presente_sem_voto",
        "Presidente (art. 51 RISF)": "presente_sem_voto",
    }
    return mapping.get(voto, "ausente")


def _map_voto_camara(tipo_voto: str) -> str:
    mapping = {
        "Sim": "sim",
        "Não": "nao",
        "Abstenção": "abstencao",
        "Obstrução": "obstrucao",
    }
    return mapping.get(tipo_voto, "ausente")
