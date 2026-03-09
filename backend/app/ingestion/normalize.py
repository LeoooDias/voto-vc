"""Transform raw API data from Câmara and Senado into unified model-ready dicts."""


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
        "nome_civil": raw.get("nome", raw.get("nomeCivil", "")),
        "nome_parlamentar": raw.get("nome", ""),
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
        "nome_civil": identidade.get("NomeCompletoParlamentar", ""),
        "nome_parlamentar": identidade.get("NomeParlamentar", ""),
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


def _map_voto_camara(tipo_voto: str) -> str:
    mapping = {
        "Sim": "sim",
        "Não": "nao",
        "Abstenção": "abstencao",
        "Obstrução": "obstrucao",
    }
    return mapping.get(tipo_voto, "ausente")
