"""Tests for the matching service — alignment scoring engine."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Casa, TipoVoto, VotoUsuario
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao, VotoParlamentar
from app.services.matching import _score_parlamentar, calcular_matching

# ── Tests for _score_parlamentar (pure function, no DB) ──


class TestScoreParlamentar:
    """Unit tests for the _score_parlamentar scoring function."""

    def test_perfect_agreement_score_100(self):
        """When user and parlamentar agree on all votes, score should be 100."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
            2: (VotoUsuario.NAO, 1.0),
            3: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            1: [TipoVoto.SIM],
            2: [TipoVoto.NAO],
            3: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, n_compared, _concordou = result
        assert score == 100.0
        assert n_compared == 3

    def test_perfect_disagreement_score_0(self):
        """When user and parlamentar disagree on all votes, score should be 0."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
            2: (VotoUsuario.NAO, 1.0),
            3: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            1: [TipoVoto.NAO],
            2: [TipoVoto.SIM],
            3: [TipoVoto.NAO],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, n_compared, _concordou = result
        assert score == 0.0
        assert n_compared == 3

    def test_mixed_votes_intermediate_score(self):
        """Mixed agreement and disagreement should yield an intermediate score."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
            2: (VotoUsuario.NAO, 1.0),
            3: (VotoUsuario.SIM, 1.0),
            4: (VotoUsuario.NAO, 1.0),
        }
        # Agree on 1, 2; disagree on 3, 4
        prop_votes = {
            1: [TipoVoto.SIM],
            2: [TipoVoto.NAO],
            3: [TipoVoto.NAO],
            4: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, n_compared, _concordou = result
        # 2 agree (+2), 2 disagree (-2) => total_score=0, normalized = (0/4 + 1)*50 = 50
        assert score == 50.0
        assert n_compared == 4

    def test_weighted_votes(self):
        """Votes with higher weight should have more impact on the score."""
        user_votes = {
            1: (VotoUsuario.SIM, 3.0),  # high weight, agrees
            2: (VotoUsuario.NAO, 1.0),  # low weight, disagrees
        }
        prop_votes = {
            1: [TipoVoto.SIM],
            2: [TipoVoto.SIM],  # user said NAO, parl said SIM -> disagree
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, n_compared, _concordou = result
        # total_score = 3.0 - 1.0 = 2.0, total_weight = 4.0
        # normalized = (2/4 + 1) * 50 = 75.0
        assert score == 75.0
        assert n_compared == 2

    def test_min_compared_threshold_not_met(self):
        """Return None when fewer propositions compared than min_compared."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            1: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=3)
        assert result is None

    def test_min_compared_threshold_met(self):
        """Return score when exactly meeting min_compared threshold."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
            2: (VotoUsuario.NAO, 1.0),
            3: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            1: [TipoVoto.SIM],
            2: [TipoVoto.NAO],
            3: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=3)
        assert result is not None

    def test_no_overlapping_proposicoes(self):
        """Return None when user and parlamentar voted on different proposicoes."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            99: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is None

    def test_skip_votes_ignored(self):
        """User votes with PULAR should not count towards the score."""
        user_votes = {
            1: (VotoUsuario.PULAR, 1.0),
            2: (VotoUsuario.SIM, 1.0),
            3: (VotoUsuario.SIM, 1.0),
            4: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            1: [TipoVoto.SIM],
            2: [TipoVoto.SIM],
            3: [TipoVoto.SIM],
            4: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, n_compared, _concordou = result
        assert score == 100.0
        assert n_compared == 3  # prop 1 was skipped

    def test_parlamentar_abstention_ignored(self):
        """Parlamentar votes that are not SIM/NAO should be ignored."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
            2: (VotoUsuario.SIM, 1.0),
            3: (VotoUsuario.SIM, 1.0),
        }
        prop_votes = {
            1: [TipoVoto.ABSTENCAO],  # not SIM/NAO, skipped
            2: [TipoVoto.SIM],
            3: [TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, n_compared, _concordou = result
        assert score == 100.0
        assert n_compared == 2  # prop 1 abstention ignored

    def test_multiple_votes_same_proposicao(self):
        """When parlamentar has multiple votes on same proposicao, first SIM/NAO wins."""
        user_votes = {
            1: (VotoUsuario.SIM, 1.0),
        }
        # parlamentar voted ABSTENCAO first, then SIM
        prop_votes = {
            1: [TipoVoto.ABSTENCAO, TipoVoto.SIM],
        }
        result = _score_parlamentar(user_votes, prop_votes, min_compared=1)
        assert result is not None
        score, _, _ = result
        assert score == 100.0


# ── Tests for calcular_matching (requires DB) ──


class TestCalcularMatching:
    """Integration tests for the full matching calculation."""

    async def _create_test_data(
        self,
        db: AsyncSession,
        n_props: int = 4,
        parl1_votes: list[TipoVoto] | None = None,
        parl2_votes: list[TipoVoto] | None = None,
    ):
        """Helper to create test data with two parlamentares voting on n proposicoes."""
        partido1 = Partido(id=10, sigla="PT", nome="Partido dos Trabalhadores")
        partido2 = Partido(id=11, sigla="PL", nome="Partido Liberal")
        db.add_all([partido1, partido2])
        await db.flush()

        parl1 = Parlamentar(
            id=10,
            id_externo="camara_201",
            casa=Casa.CAMARA,
            nome_civil="Ana Oliveira",
            nome_parlamentar="Ana Oliveira",
            sexo="F",
            uf="RJ",
            partido_id=partido1.id,
            legislatura_atual=True,
        )
        parl2 = Parlamentar(
            id=11,
            id_externo="camara_202",
            casa=Casa.CAMARA,
            nome_civil="Carlos Souza",
            nome_parlamentar="Carlos Souza",
            sexo="M",
            uf="RJ",
            partido_id=partido2.id,
            legislatura_atual=True,
        )
        db.add_all([parl1, parl2])
        await db.flush()

        props = []
        votacoes = []
        for i in range(1, n_props + 1):
            prop = Proposicao(
                id=100 + i,
                id_externo=f"camara_prop_{2000 + i}",
                casa_origem=Casa.CAMARA,
                tipo="PL",
                numero=1000 + i,
                ano=2025,
                ementa=f"Proposicao de teste {i}",
                resumo_cidadao=f"Resumo {i}",
                tema="teste",
                relevancia_score=0.9,
            )
            props.append(prop)
        db.add_all(props)
        await db.flush()

        for i, prop in enumerate(props):
            vot = Votacao(
                id=100 + i + 1,
                id_externo=f"camara_vot_{3000 + i}",
                proposicao_id=prop.id,
                casa=Casa.CAMARA,
                data=datetime(2025, 1, 1, 14, 0) + timedelta(days=i),
                descricao=f"Votacao {i}",
                total_sim=300,
                total_nao=150,
                total_abstencao=10,
            )
            votacoes.append(vot)
        db.add_all(votacoes)
        await db.flush()

        if parl1_votes is None:
            parl1_votes = [TipoVoto.SIM] * n_props
        if parl2_votes is None:
            parl2_votes = [TipoVoto.NAO] * n_props

        voto_id = 100
        for i, (vot, v1, v2) in enumerate(zip(votacoes, parl1_votes, parl2_votes)):
            voto_id += 1
            db.add(
                VotoParlamentar(
                    id=voto_id,
                    votacao_id=vot.id,
                    parlamentar_id=parl1.id,
                    voto=v1,
                )
            )
            voto_id += 1
            db.add(
                VotoParlamentar(
                    id=voto_id,
                    votacao_id=vot.id,
                    parlamentar_id=parl2.id,
                    voto=v2,
                )
            )
        await db.commit()

        return props, parl1, parl2, partido1, partido2

    async def test_empty_respostas_returns_empty(self, db: AsyncSession):
        """With no user answers, return empty results."""
        result = await calcular_matching(db, respostas=[])
        assert result == {"parlamentares": [], "partidos": []}

    async def test_perfect_agreement_parlamentar(self, db: AsyncSession):
        """Parlamentar who agrees on everything should score 100."""
        props, parl1, parl2, _, _ = await self._create_test_data(db, n_props=4)

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        result = await calcular_matching(db, respostas=respostas)
        parlamentares = result["parlamentares"]

        # parl1 voted SIM on all => should score 100
        parl1_result = next((p for p in parlamentares if p["parlamentar_id"] == parl1.id), None)
        assert parl1_result is not None
        assert parl1_result["score"] == 100.0

    async def test_perfect_disagreement_parlamentar(self, db: AsyncSession):
        """Parlamentar who disagrees on everything should score 0."""
        props, parl1, parl2, _, _ = await self._create_test_data(db, n_props=4)

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        result = await calcular_matching(db, respostas=respostas)
        parlamentares = result["parlamentares"]

        # parl2 voted NAO on all while user voted SIM => should score 0
        parl2_result = next((p for p in parlamentares if p["parlamentar_id"] == parl2.id), None)
        assert parl2_result is not None
        assert parl2_result["score"] == 0.0

    async def test_mixed_votes_intermediate_score(self, db: AsyncSession):
        """Mixed agreement should produce an intermediate score."""
        # parl1: SIM, SIM, NAO, NAO — user: SIM on all => 2 agree, 2 disagree => 50
        props, parl1, parl2, _, _ = await self._create_test_data(
            db,
            n_props=4,
            parl1_votes=[TipoVoto.SIM, TipoVoto.SIM, TipoVoto.NAO, TipoVoto.NAO],
            parl2_votes=[TipoVoto.SIM, TipoVoto.SIM, TipoVoto.SIM, TipoVoto.SIM],
        )

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        result = await calcular_matching(db, respostas=respostas)
        parlamentares = result["parlamentares"]

        parl1_result = next((p for p in parlamentares if p["parlamentar_id"] == parl1.id), None)
        assert parl1_result is not None
        assert parl1_result["score"] == 50.0

    async def test_min_compared_filters_parlamentares(self, db: AsyncSession):
        """Parlamentares below min_compared threshold should be excluded.

        min_compared = max(3, len(user_votes) // 4).
        With 12 user votes, min_compared = 3.
        A parlamentar who only has votes on 2 props should be excluded.
        """
        # Create 4 proposicoes but parl2 only votes on 2
        props, parl1, parl2, _, _ = await self._create_test_data(
            db,
            n_props=12,
            parl1_votes=[TipoVoto.SIM] * 12,
            # parl2 votes SIM on first 2, then ABSTENCAO on rest (won't count)
            parl2_votes=[TipoVoto.SIM, TipoVoto.SIM] + [TipoVoto.ABSTENCAO] * 10,
        )

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        result = await calcular_matching(db, respostas=respostas)
        parlamentares = result["parlamentares"]

        # parl2 only compared 2 props, min_compared = max(3, 12//4) = 3 => excluded
        parl2_result = next((p for p in parlamentares if p["parlamentar_id"] == parl2.id), None)
        assert parl2_result is None

    async def test_partido_aggregation(self, db: AsyncSession):
        """Partido scores should be averages of their parlamentares' scores."""
        props, parl1, parl2, partido1, partido2 = await self._create_test_data(
            db,
            n_props=4,
            parl1_votes=[TipoVoto.SIM] * 4,
            parl2_votes=[TipoVoto.NAO] * 4,
        )

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        result = await calcular_matching(db, respostas=respostas)
        partidos = result["partidos"]

        pt = next((p for p in partidos if p["partido_id"] == partido1.id), None)
        pl = next((p for p in partidos if p["partido_id"] == partido2.id), None)

        assert pt is not None
        assert pt["score"] == 100.0
        assert pt["parlamentares_comparados"] == 1

        assert pl is not None
        assert pl["score"] == 0.0
        assert pl["parlamentares_comparados"] == 1

    async def test_uf_filter(self, db: AsyncSession):
        """UF filter should only return parlamentares from the given state."""
        props, parl1, parl2, _, _ = await self._create_test_data(db, n_props=4)

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        # Both parlamentares are from RJ, so filtering by SP should return empty
        result = await calcular_matching(db, respostas=respostas, uf="SP")
        assert result["parlamentares"] == []

        # Filtering by RJ should return results
        result = await calcular_matching(db, respostas=respostas, uf="RJ")
        assert len(result["parlamentares"]) > 0

    async def test_pular_does_not_inflate_min_compared(self, db: AsyncSession):
        """PULAR votes should not increase the min_compared threshold.

        With 4 sim votes + 16 pular votes, min_compared should be max(3, 4//4)=3
        not max(3, 20//4)=5. A parlamentar with 3 overlapping votes should appear.
        """
        n_total = 20
        props, parl1, parl2, _, _ = await self._create_test_data(
            db,
            n_props=n_total,
            parl1_votes=[TipoVoto.SIM] * n_total,
            parl2_votes=[TipoVoto.NAO] * n_total,
        )

        # 4 sim + 16 pular
        respostas = []
        for i, p in enumerate(props):
            voto = VotoUsuario.SIM if i < 4 else VotoUsuario.PULAR
            respostas.append(MagicMock(proposicao_id=p.id, voto=voto, peso=1.0))

        result = await calcular_matching(db, respostas=respostas)
        parlamentares = result["parlamentares"]

        # min_compared = max(3, 4//4) = 3, parl1 has 4 SIM overlaps => should appear
        parl1_result = next((p for p in parlamentares if p["parlamentar_id"] == parl1.id), None)
        assert parl1_result is not None
        assert parl1_result["score"] == 100.0
        assert parl1_result["votos_comparados"] == 4

    async def test_results_sorted_by_score_desc(self, db: AsyncSession):
        """Results should be sorted by score in descending order."""
        props, parl1, parl2, _, _ = await self._create_test_data(
            db,
            n_props=4,
            parl1_votes=[TipoVoto.SIM, TipoVoto.SIM, TipoVoto.NAO, TipoVoto.NAO],
            parl2_votes=[TipoVoto.SIM] * 4,
        )

        respostas = [MagicMock(proposicao_id=p.id, voto=VotoUsuario.SIM, peso=1.0) for p in props]

        result = await calcular_matching(db, respostas=respostas)
        parlamentares = result["parlamentares"]
        scores = [p["score"] for p in parlamentares]
        assert scores == sorted(scores, reverse=True)
