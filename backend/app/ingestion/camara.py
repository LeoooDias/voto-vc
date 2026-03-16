import logging

from app.ingestion.base import BaseAPIClient

logger = logging.getLogger(__name__)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"


class CamaraClient(BaseAPIClient):
    def __init__(self):
        super().__init__(CAMARA_API)

    async def fetch_deputados(self, legislatura: int | None = None) -> list[dict]:
        params = {}
        if legislatura:
            params["idLegislatura"] = legislatura
        return await self.get_paginated("deputados", params=params)

    async def fetch_votacoes(
        self, data_inicio: str | None = None, data_fim: str | None = None
    ) -> list[dict]:
        params = {}
        if data_inicio:
            params["dataInicio"] = data_inicio
        if data_fim:
            params["dataFim"] = data_fim
        return await self.get_paginated("votacoes", params=params)

    async def fetch_votacoes_recent(self, max_pages: int = 10) -> list[dict]:
        """Fetch recent votações without date filter, ordered by most recent."""
        params = {"ordem": "DESC", "ordenarPor": "dataHoraRegistro"}
        return await self.get_paginated(
            "votacoes",
            params=params,
            items_per_page=100,
            max_pages=max_pages,
        )

    async def fetch_votos(self, votacao_id: str) -> list[dict]:
        data = await self.get(f"votacoes/{votacao_id}/votos")
        return data.get("dados", [])

    async def fetch_orientacoes(self, votacao_id: str) -> list[dict]:
        data = await self.get(f"votacoes/{votacao_id}/orientacoes")
        return data.get("dados", [])

    async def fetch_proposicao(self, proposicao_id: str) -> dict:
        data = await self.get(f"proposicoes/{proposicao_id}")
        return data.get("dados", {})

    async def fetch_proposicoes(
        self, ano: int | None = None, tipo: str | None = None
    ) -> list[dict]:
        params = {}
        if ano:
            params["ano"] = ano
        if tipo:
            params["siglaTipo"] = tipo
        return await self.get_paginated("proposicoes", params=params)
