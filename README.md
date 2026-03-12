# voto.vc

Ferramenta para ajudar eleitores brasileiros a encontrar parlamentares alinhados com suas posições, baseado em votações reais do Congresso Nacional.

O usuário responde proposições legislativas reais (como se estivesse votando no Congresso) e recebe um ranking de deputados e senadores por alinhamento.

**Live em [voto.vc](https://voto.vc)**

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | SvelteKit 5, TypeScript, pnpm |
| Backend | FastAPI, Python 3.12, uv |
| Banco | PostgreSQL 16, async SQLAlchemy 2.0, Alembic |
| Infra | AWS (EC2 t4g.small, CloudFront, Route 53, ACM), Terraform |
| CI/CD | GitHub Actions → rsync + Docker Compose |
| AI | Claude API (resumos, descrições, classificação de temas) |

## Estrutura

```
voto-vc/
├── frontend/          # SvelteKit 5 (adapter-node)
│   └── src/routes/
│       ├── /                    # Landing page
│       ├── /questionario        # Seleção de UF + votação em proposições
│       ├── /resultado           # Ranking de parlamentares alinhados
│       ├── /parlamentar/[id]    # Perfil + histórico de votos
│       └── /sobre               # Metodologia
├── backend/           # FastAPI
│   ├── app/
│   │   ├── models/        # SQLAlchemy: parlamentar, proposicao, votacao, partido...
│   │   ├── routers/       # API: questionario, matching, parlamentares, auth
│   │   ├── services/      # Matching engine, montagem do questionário
│   │   ├── ingestion/     # Clientes das APIs da Câmara e Senado + normalização
│   │   └── classification/# Classificação temática
│   ├── alembic/           # Migrations
│   └── *.py               # Scripts de processamento (resumir, enriquecer, classificar)
├── infra/             # Terraform (VPC, EC2, CloudFront, DNS, SSL)
├── docs/              # Exports e revisões
├── docker-compose.yml # Dev: postgres + backend + frontend
├── Dockerfile.*.prod  # Produção: backend (uvicorn) + frontend (node)
└── Makefile           # Atalhos: dev, stop, migrate, test, lint
```

## Dados

- **Câmara dos Deputados**: [dadosabertos.camara.leg.br/api/v2](https://dadosabertos.camara.leg.br/api/v2/) — deputados, votações nominais, proposições
- **Senado Federal**: [legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos/) — senadores, votações, matérias
- Ambas APIs são públicas, sem autenticação

## Dev local

```bash
# Subir banco + backend + frontend
make dev

# Migrations
make migrate

# Testes
make test

# Lint
make lint
```

Acesso: frontend em `localhost:5173`, backend em `localhost:8000/api`, banco em `localhost:54329`.

## Deploy

Push em `main` aciona GitHub Actions:
1. rsync do código pro EC2
2. Docker build (backend + frontend)
3. Docker Compose up (postgres, backend, frontend, nginx)

CloudFront na frente com SSL, cache de assets estáticos (`_app/*`), e tráfego dinâmico sem cache.

## Processamento de dados

Scripts one-off no `backend/`:

```bash
python resumir_proposicoes.py      # Resumos cidadãos via Claude API
python enriquecer_proposicoes.py   # Descrições detalhadas (web search + Claude)
python classificar_temas.py        # Classificação em 17 temas via Claude
python processar_restantes.py      # Pipeline completo para proposições pendentes
python normalizar_nomes.py         # Title case em nomes de parlamentares
```

## Como funciona

1. Usuário escolhe seu estado (UF)
2. Responde ~20 proposições legislativas reais (a favor / contra / pular)
3. Sistema calcula alinhamento com cada parlamentar baseado em seus votos reais
4. Ranking de parlamentares mais alinhados, filtrado pelo estado escolhido
5. Perfil detalhado de cada parlamentar com histórico de votos expansível

Proposições são diversificadas por tema (17 categorias) via round-robin e randomizadas por sessão.
