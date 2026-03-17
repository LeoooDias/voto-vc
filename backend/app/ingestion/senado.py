import logging

from app.ingestion.base import BaseAPIClient

logger = logging.getLogger(__name__)

SENADO_API = "https://legis.senado.leg.br/dadosabertos"


class SenadoClient(BaseAPIClient):
    def __init__(self):
        super().__init__(SENADO_API)

    async def fetch_senadores(self, legislatura: int | None = None) -> list[dict]:
        path = (
            "senador/lista/atual" if not legislatura else f"senador/lista/legislatura/{legislatura}"
        )
        data = await self.get(f"{path}.json")
        # Senado API nests data differently
        lista = data.get("ListaParlamentarEmExercicio", data.get("ListaParlamentarLegislatura", {}))
        parlamentares = lista.get("Parlamentares", {})
        items = parlamentares.get("Parlamentar", [])
        return items if isinstance(items, list) else [items] if items else []

    async def fetch_votacoes_senador(self, senador_id: str) -> list[dict]:
        data = await self.get(f"senador/{senador_id}/votacoes.json")
        votacao_parlamentar = data.get("VotacaoParlamentar", {})
        parlamentar = votacao_parlamentar.get("Parlamentar", {})
        votacoes = parlamentar.get("Votacoes", {})
        items = votacoes.get("Votacao", [])
        return items if isinstance(items, list) else [items] if items else []

    async def fetch_votacoes_ano(self, ano: int) -> list[dict]:
        """Votações nominais de um ano (nova API, inclui votos inline)."""
        data = await self.get(f"votacao?ano={ano}")
        return data if isinstance(data, list) else []

    async def fetch_materia(self, materia_id: str) -> dict:
        data = await self.get(f"materia/{materia_id}.json")
        return data.get("DetalheMateria", {}).get("Materia", {})
