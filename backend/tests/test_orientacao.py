"""Tests for the orientacao service — alignment via party guidance."""

from datetime import datetime
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Casa, Orientacao, TipoVoto, VotoUsuario
from app.models.parlamentar import Parlamentar
from app.models.partido import BlocoParlamentar, OrientacaoBancada, Partido, bloco_partido
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao, VotoParlamentar
from app.services.orientacao import (
    alinhamento_por_orientacao,
    calcular_disciplina,
    orientacoes_por_proposicao,
)


async def _setup_base(db: AsyncSession):
    """Create base data: 2 partidos, 1 bloco, 3 proposições, 3 votações."""
    pt = Partido(id=50, sigla="PT", nome="Partido dos Trabalhadores")
    pl = Partido(id=51, sigla="PL", nome="Partido Liberal")
    pcdob = Partido(id=52, sigla="PCdoB", nome="Partido Comunista do Brasil")
    db.add_all([pt, pl, pcdob])
    await db.flush()

    # Bloco federação PT-PCdoB-PV
    bloco = BlocoParlamentar(
        id=100,
        nome="Federação Brasil da Esperança",
        casa=Casa.CAMARA,
        legislatura=57,
        federacao=True,
        sigla_csv="Fdr PT-PCdoB-PV",
    )
    db.add(bloco)
    await db.flush()

    # Associar PT e PCdoB ao bloco
    await db.execute(bloco_partido.insert().values(bloco_id=100, partido_id=50))
    await db.execute(bloco_partido.insert().values(bloco_id=100, partido_id=52))
    await db.flush()

    # Parlamentares
    parl_pt = Parlamentar(
        id=50,
        id_externo="camara_501",
        casa=Casa.CAMARA,
        nome_civil="Ana PT",
        nome_parlamentar="Ana PT",
        sexo="F",
        uf="SP",
        partido_id=50,
        legislatura_atual=True,
    )
    parl_pt2 = Parlamentar(
        id=53,
        id_externo="camara_503",
        casa=Casa.CAMARA,
        nome_civil="Carlos PT",
        nome_parlamentar="Carlos PT",
        sexo="M",
        uf="SP",
        partido_id=50,
        legislatura_atual=True,
    )
    parl_pl = Parlamentar(
        id=51,
        id_externo="camara_502",
        casa=Casa.CAMARA,
        nome_civil="Bruno PL",
        nome_parlamentar="Bruno PL",
        sexo="M",
        uf="SP",
        partido_id=51,
        legislatura_atual=True,
    )
    db.add_all([parl_pt, parl_pt2, parl_pl])
    await db.flush()

    # 3 proposições + votações
    props = []
    votacoes = []
    for i in range(1, 4):
        prop = Proposicao(
            id=500 + i,
            id_externo=f"camara_prop_500{i}",
            casa_origem=Casa.CAMARA,
            tipo="PL",
            numero=500 + i,
            ano=2025,
            ementa=f"Proposicao {i}",
            tema="teste",
            relevancia_score=0.9,
        )
        props.append(prop)
    db.add_all(props)
    await db.flush()

    for i, prop in enumerate(props):
        vot = Votacao(
            id=500 + i + 1,
            id_externo=f"vot-500{i + 1}",
            proposicao_id=prop.id,
            casa=Casa.CAMARA,
            data=datetime(2025, 6, 15 + i, 14, 0),
            descricao=f"Votacao prop {i + 1}",
            total_sim=300,
            total_nao=150,
            total_abstencao=10,
        )
        votacoes.append(vot)
    db.add_all(votacoes)
    await db.flush()

    # Votos dos parlamentares (todos votam SIM)
    voto_id = 500
    for vot in votacoes:
        for parl in [parl_pt, parl_pt2, parl_pl]:
            voto_id += 1
            db.add(
                VotoParlamentar(
                    id=voto_id,
                    votacao_id=vot.id,
                    parlamentar_id=parl.id,
                    voto=TipoVoto.SIM,
                    partido_na_epoca="PT" if parl.partido_id == 50 else "PL",
                )
            )
    await db.commit()

    return {
        "pt": pt,
        "pl": pl,
        "pcdob": pcdob,
        "bloco": bloco,
        "props": props,
        "votacoes": votacoes,
        "parl_pt": parl_pt,
        "parl_pt2": parl_pt2,
        "parl_pl": parl_pl,
    }


def _make_respostas(props, voto=VotoUsuario.SIM):
    """Create mock user responses for given proposições."""
    return [MagicMock(proposicao_id=p.id, voto=voto, peso=1.0) for p in props]


class TestAlinhamentoPorOrientacaoDireta:
    """Orientação direta do partido (sem bloco)."""

    async def test_orientacao_direta_concordancia_total(self, db: AsyncSession):
        """Partido orienta SIM, usuário vota SIM → score 100."""
        data = await _setup_base(db)

        # PL orienta SIM nas 3 votações
        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="PL",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
        await db.commit()

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PL", respostas)

        assert result["alinhamento_score"] == 100.0
        assert result["votacoes_consideradas"] == 3
        assert result["metodo"] == "orientacao"

    async def test_orientacao_direta_discordancia_total(self, db: AsyncSession):
        """Partido orienta NAO, usuário vota SIM → score 0.

        Parlamentar do PL vota NAO (consistente com orientação) para
        não disparar detecção de divergência.
        """
        data = await _setup_base(db)

        # Ajustar voto do PL para NAO (consistente com orientação)
        from sqlalchemy import update

        await db.execute(
            update(VotoParlamentar)
            .where(VotoParlamentar.parlamentar_id == data["parl_pl"].id)
            .values(voto=TipoVoto.NAO)
        )

        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="PL",
                    orientacao_raw="Não",
                    orientacao=Orientacao.NAO,
                )
            )
        await db.commit()

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PL", respostas)

        assert result["alinhamento_score"] == 0.0
        assert result["votacoes_consideradas"] == 3


class TestAlinhamentoViaBloco:
    """Orientação resolvida via bloco/federação."""

    async def test_orientacao_via_bloco(self, db: AsyncSession):
        """PT não tem orientação direta mas seu bloco orienta SIM."""
        data = await _setup_base(db)

        # Orientação do bloco (não do PT diretamente)
        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="Fdr PT-PCdoB-PV",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
        await db.commit()

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PT", respostas)

        assert result["alinhamento_score"] == 100.0
        assert result["votacoes_consideradas"] == 3

    async def test_orientacao_direta_prevalece_sobre_bloco(self, db: AsyncSession):
        """Se PT tem orientação direta E via bloco, a direta prevalece."""
        data = await _setup_base(db)

        # Ajustar votos do PT para NAO (consistente com orientação direta)
        from sqlalchemy import update

        await db.execute(
            update(VotoParlamentar)
            .where(VotoParlamentar.parlamentar_id.in_([50, 53]))
            .values(voto=TipoVoto.NAO)
        )

        for vot in data["votacoes"]:
            # Bloco orienta SIM
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="Fdr PT-PCdoB-PV",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
            # PT orienta NAO diretamente
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="PT",
                    orientacao_raw="Não",
                    orientacao=Orientacao.NAO,
                )
            )
        await db.commit()

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PT", respostas)

        # Orientação direta NAO vs usuário SIM → score 0
        assert result["alinhamento_score"] == 0.0


class TestOrientacaoLiberado:
    """Orientação 'liberado' deve ser excluída do denominador."""

    async def test_liberado_excluido_do_denominador(self, db: AsyncSession):
        """Votações com orientação 'liberado' não contam no cálculo."""
        data = await _setup_base(db)

        # Votação 1: orienta SIM (conta)
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][0].id_externo,
                sigla_bancada="PL",
                orientacao_raw="Sim",
                orientacao=Orientacao.SIM,
            )
        )
        # Votação 2: liberado (não conta)
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][1].id_externo,
                sigla_bancada="PL",
                orientacao_raw="Liberado",
                orientacao=Orientacao.LIBERADO,
            )
        )
        # Votação 3: orienta SIM (conta)
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][2].id_externo,
                sigla_bancada="PL",
                orientacao_raw="Sim",
                orientacao=Orientacao.SIM,
            )
        )
        await db.commit()

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PL", respostas)

        assert result["alinhamento_score"] == 100.0
        assert result["votacoes_consideradas"] == 2
        assert result["votacoes_liberadas"] == 1


class TestDivergenciaDetectada:
    """Divergência entre orientação e votos reais → fallback."""

    async def test_divergencia_exclui_votacao(self, db: AsyncSession):
        """Quando >30% dos parlamentares divergem, orientação é descartada
        e fallback por distribuição de votos é usado."""
        data = await _setup_base(db)

        # PT orienta SIM nas 3 votações
        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="PT",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
        await db.flush()

        # Mas na votação 1, os 2 parlamentares do PT votam NAO (100% divergência)
        from sqlalchemy import update

        await db.execute(
            update(VotoParlamentar)
            .where(
                VotoParlamentar.votacao_id == data["votacoes"][0].id,
                VotoParlamentar.parlamentar_id.in_([50, 53]),
            )
            .values(voto=TipoVoto.NAO)
        )
        await db.commit()

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PT", respostas)

        # Votação 1 tem divergência detectada
        assert result["votacoes_com_divergencia"] >= 1
        # Fallback resolve votação 1 via distribuição (100% NAO → infere NAO)
        assert result["votacoes_fallback_distribuicao"] >= 1
        # 3 votações consideradas: 2 via orientação + 1 via fallback
        assert result["votacoes_consideradas"] == 3


class TestSemOrientacao:
    """Sem orientação disponível para o partido."""

    async def test_sem_orientacao_usa_fallback(self, db: AsyncSession):
        """Sem orientações oficiais, fallback por distribuição de votos é usado.

        No setup todos os parlamentares PT votam SIM, então o fallback
        infere orientação SIM. Usuário vota SIM → score 100.
        """
        data = await _setup_base(db)
        # Nenhuma orientação inserida

        respostas = _make_respostas(data["props"], VotoUsuario.SIM)
        result = await alinhamento_por_orientacao(db, "PT", respostas)

        assert result["alinhamento_score"] == 100.0
        assert result["votacoes_fallback_distribuicao"] == 3
        assert result["votacoes_consideradas"] == 3
        assert result["metodo"] == "fallback_distribuicao"


class TestOrientacoesPorProposicao:
    """Endpoint GET /proposicoes/{id}/partidos."""

    async def test_retorna_orientacoes_e_distribuicao(self, db: AsyncSession):
        """Deve retornar orientações e distribuição de votos por partido."""
        data = await _setup_base(db)

        # Orientação direta PL e via bloco PT
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][0].id_externo,
                sigla_bancada="PL",
                orientacao_raw="Não",
                orientacao=Orientacao.NAO,
            )
        )
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][0].id_externo,
                sigla_bancada="Fdr PT-PCdoB-PV",
                orientacao_raw="Sim",
                orientacao=Orientacao.SIM,
            )
        )
        await db.commit()

        result = await orientacoes_por_proposicao(db, data["props"][0].id)

        assert result["proposicao_id"] == data["props"][0].id
        assert len(result["votacoes"]) == 1

        votacao = result["votacoes"][0]
        assert votacao["id_votacao"] == data["votacoes"][0].id_externo

        # Deve ter ao menos PT e PL nos partidos
        siglas = {p["sigla"] for p in votacao["partidos"]}
        assert "PT" in siglas
        assert "PL" in siglas

        # PL orienta NAO diretamente
        pl_info = next(p for p in votacao["partidos"] if p["sigla"] == "PL")
        assert pl_info["orientacao"] == "nao"
        assert pl_info["orientacao_via"] == "partido"

        # PT orienta via bloco
        pt_info = next(p for p in votacao["partidos"] if p["sigla"] == "PT")
        assert pt_info["orientacao"] == "sim"
        assert pt_info["orientacao_via"] == "bloco"
        assert pt_info["sigla_bloco"] == "Fdr PT-PCdoB-PV"


class TestRespostasVazias:
    """Edge cases com respostas vazias ou apenas PULAR."""

    async def test_respostas_vazias(self, db: AsyncSession):
        await _setup_base(db)
        result = await alinhamento_por_orientacao(db, "PT", [])
        assert result["alinhamento_score"] is None
        assert result["votacoes_consideradas"] == 0

    async def test_todas_pular(self, db: AsyncSession):
        data = await _setup_base(db)
        respostas = _make_respostas(data["props"], VotoUsuario.PULAR)
        result = await alinhamento_por_orientacao(db, "PT", respostas)
        assert result["alinhamento_score"] is None


class TestDisciplina:
    """Cálculo de disciplina partidária."""

    async def test_disciplina_total_quando_todos_seguem(self, db: AsyncSession):
        """100% disciplina quando todos parlamentares votam conforme orientação."""
        data = await _setup_base(db)

        # PT orienta SIM nas 3 votações — parlamentares PT já votam SIM no setup
        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="PT",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
        await db.commit()

        result = await calcular_disciplina(db, "PT")
        assert result["disciplina"] == 100.0
        assert result["votacoes_analisadas"] == 3

    async def test_disciplina_parcial(self, db: AsyncSession):
        """Disciplina < 100% quando alguns parlamentares divergem."""
        data = await _setup_base(db)

        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="PT",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
        await db.flush()

        # Um dos 2 parlamentares PT vota NAO em todas as votações
        from sqlalchemy import update

        await db.execute(
            update(VotoParlamentar)
            .where(VotoParlamentar.parlamentar_id == 53)
            .values(voto=TipoVoto.NAO)
        )
        await db.commit()

        result = await calcular_disciplina(db, "PT")
        # 3 votações × 2 parlamentares = 6 votos substantivos
        # 3 alinhados (parl_pt SIM) + 3 divergentes (parl_pt2 NAO) = 50%
        assert result["disciplina"] == 50.0
        assert result["votacoes_analisadas"] == 3

    async def test_disciplina_via_bloco(self, db: AsyncSession):
        """Disciplina calculada via orientação de bloco quando não há direta."""
        data = await _setup_base(db)

        # Orientação via bloco
        for vot in data["votacoes"]:
            db.add(
                OrientacaoBancada(
                    id_votacao=vot.id_externo,
                    sigla_bancada="Fdr PT-PCdoB-PV",
                    orientacao_raw="Sim",
                    orientacao=Orientacao.SIM,
                )
            )
        await db.commit()

        result = await calcular_disciplina(db, "PT")
        assert result["disciplina"] == 100.0

    async def test_disciplina_sem_orientacao(self, db: AsyncSession):
        """Sem orientações, disciplina é None."""
        await _setup_base(db)
        result = await calcular_disciplina(db, "PT")
        assert result["disciplina"] is None
        assert result["votacoes_analisadas"] == 0

    async def test_disciplina_exclui_liberado(self, db: AsyncSession):
        """Votações com orientação 'liberado' não entram no cálculo."""
        data = await _setup_base(db)

        # Votação 1: SIM (conta)
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][0].id_externo,
                sigla_bancada="PT",
                orientacao_raw="Sim",
                orientacao=Orientacao.SIM,
            )
        )
        # Votação 2: Liberado (não conta)
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][1].id_externo,
                sigla_bancada="PT",
                orientacao_raw="Liberado",
                orientacao=Orientacao.LIBERADO,
            )
        )
        # Votação 3: SIM (conta)
        db.add(
            OrientacaoBancada(
                id_votacao=data["votacoes"][2].id_externo,
                sigla_bancada="PT",
                orientacao_raw="Sim",
                orientacao=Orientacao.SIM,
            )
        )
        await db.commit()

        result = await calcular_disciplina(db, "PT")
        assert result["disciplina"] == 100.0
        assert result["votacoes_analisadas"] == 2
        assert result["votacoes_liberadas"] == 1
