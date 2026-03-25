# Cobertura do Senado nas Posições Temáticas

**Data:** 2026-03-24
**Commit:** `a0a2715`

## Problema

Após completar o questionário completo (20 posições temáticas), nenhum senador aparecia nos resultados de matching. O app cobria apenas a Câmara dos Deputados.

## Diagnóstico

As 20 posições temáticas (`posicoes`) mapeiam para proposições específicas via `posicao_proposicoes`. O matching expande as respostas do usuário nessas proposições e cruza com os votos dos parlamentares.

**Estado anterior:** das 55 proposições mapeadas, apenas 8 tinham votações do Senado — e 12 das 20 posições tinham **zero** cobertura senatorial. Sem votos para comparar, senadores não atingiam o limiar mínimo de confiança do matching engine (`min_compared`).

Paradoxalmente, o banco possuía 473 proposições com votações do Senado, resumo e relevância. Os dados existiam, só não estavam vinculados às posições.

## Solução

Adicionamos 30 proposições com votações do Senado ao mapeamento das posições temáticas em `backend/scripts/seed_posicoes.py`. As proposições foram selecionadas por:

1. **Relevância temática** — conteúdo alinhado com a posição (ex: Reforma da Previdência para "Reforma da previdência")
2. **Votações no Senado** — proposições com registro de votos nominais de senadores
3. **Direção clara** — possível determinar se votar SIM alinha ou opõe à posição

Cada proposição recebe uma `direcao` (`sim` ou `nao`) que indica: "votar SIM nesta proposição significa concordar (`sim`) ou discordar (`nao`) com a posição temática?"

## Proposições adicionadas por posição

| # | Posição | Proposições adicionadas | Votos Senado |
|---|---------|------------------------|--------------|
| 1 | Privatização de estatais | Saneamento Básico (1653), Energia Elétrica (1508) | 81 cada |
| 6 | Endurecimento penal | Endurecimento da Execução Penal (1862) | 162 |
| 7 | Controle de armas | Anulação do Decreto das Armas (1632) | 81 |
| 9 | Proteção ambiental | Barragens (1655), Áreas Protegidas PA (1611), Marco Temporal (1871) | 81–243 |
| 10 | Compromissos climáticos | Eólica no Mar (1837), Carbono (1892), Hidrogênio Verde (1882) | 81 cada |
| 11 | Igualdade de gênero | Emprega+Mulheres (1852), Financ. Racial (1884), Cotas (1798) | 81–162 |
| 12 | Proteção à infância | Celular nas Escolas (1897), Saúde Mental nas Escolas (1819) | 81 cada |
| 13 | Violência digital | Fake News (1720), Crimes Digitais (1765) | 81–243 |
| 14 | Trabalhadores vulneráveis | Vale-Alimentação (1851), Suporte a Empregos (1175), Emprega+ (1852) | 80–81 |
| 15 | Serviço público | Salários Servidores Ex-Territórios (1626) | 81 |
| 16 | Reforma da previdência | Reforma 2019 (1119), Reforma 2003 (1506), PEC Paralela 2003 (1503) | 729–972 |
| 17 | Fortalecimento do SUS | Saúde fora do Teto (1420), Preço de Medicamentos (1500) | 81 cada |
| 18 | Quebra de patentes | Quebra de Patentes em Emergências (1226) | 162 |
| 19 | Investimento em educação | FUNDEB (1541), FIES (1050), Cotas Universidades (1784) | 81–243 |
| 20 | Incentivo à cultura | Aldir Blanc Emergencial (1814), Aldir Blanc Permanente (1823), Plano Nacional de Cultura (1510) | 81–162 |

**Posições 2, 3, 4, 5, 8** já possuíam cobertura adequada do Senado e não precisaram de adições.

## Resultado

| Métrica | Antes | Depois |
|---------|-------|--------|
| Posições com votos do Senado | 8/20 | **20/20** |
| Senadores com votos comparáveis | ~0 efetivo | **267** |
| Total de votos de senadores | ~200 | **8.099** |
| Proposições mapeadas | 55 | **85** |

## Arquivos alterados

- `backend/scripts/seed_posicoes.py` — seed idempotente (upsert) das posições e seus mapeamentos

## Como funciona o fluxo

```
Usuário responde posições    →  expandir_posicoes_para_respostas()
                                    ↓
                             Respostas por proposição (incluindo as do Senado)
                                    ↓
                             calcular_matching() carrega votos de AMBAS as casas
                                    ↓
                             Senadores aparecem nos resultados
```

## Referências

- Modelo: `backend/app/models/posicao.py` (Posicao, PosicaoProposicao)
- Expansão: `backend/app/services/posicoes.py` → `expandir_posicoes_para_respostas()`
- Matching: `backend/app/services/matching.py` → `calcular_matching()`
- Router: `backend/app/routers/matching.py` → `POST /api/matching/calcular`
