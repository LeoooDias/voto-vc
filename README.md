# voto.vc — seja representado

Descubra quem vota como você. Vote em proposições reais do Congresso Nacional e descubra quais parlamentares e partidos mais se alinham com seus valores.

Sem viés partidário. Sem coleta de dados pessoais. Sem criar conta. Código totalmente aberto.

**[voto.vc](https://voto.vc)**

## Por que existe

Em 2026, mais de 150 milhões de brasileiros vão às urnas escolher deputados e senadores. A maioria não sabe como seus representantes votam de verdade — apenas o que dizem.

O voto.vc muda isso: usando dados públicos de votações nominais da Câmara dos Deputados e do Senado Federal, comparamos suas posições com os votos reais de cada parlamentar e partido. Em minutos, você descobre quem realmente te representa.

## Como funciona

1. **Escolha seu estado** — selecione sua UF para ver parlamentares da sua região
2. **Vote nas proposições** — diga se é a favor ou contra propostas reais votadas no Congresso
3. **Veja seu alinhamento** — descubra quais políticos e partidos votam como você votaria

10 perguntas · 5 minutos · sem criar conta.

## Código aberto

Este projeto é totalmente aberto — código, metodologia, dados. Acreditamos que uma ferramenta cívica precisa ser transparente para ser confiável.

A [metodologia de alinhamento](https://voto.vc/sobre) é documentada em detalhe: como calculamos a pontuação, o ajuste de confiança estatístico, a classificação temática por IA e o compromisso com neutralidade.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | SvelteKit 5, TypeScript, pnpm |
| Backend | FastAPI, Python 3.12, uv |
| Banco | PostgreSQL 16, async SQLAlchemy 2.0, Alembic |
| Infra | AWS (EC2, CloudFront, Route 53), Terraform |
| CI/CD | GitHub Actions → Docker Compose |
| IA | Claude API (resumos, descrições, classificação temática, chat) |

## Estrutura

```
voto-vc/
├── frontend/          # SvelteKit 5 (adapter-node)
│   └── src/routes/
│       ├── /                    # Landing page
│       ├── /vote                # Seleção de UF + votação em proposições
│       ├── /perfil              # Ranking de parlamentares e partidos alinhados
│       ├── /parlamentar/[id]    # Perfil + histórico de votos
│       ├── /partido/[id]        # Perfil do partido + disciplina partidária
│       ├── /sobre               # Metodologia e quem somos
│       └── /contribuir          # Apoie o projeto
├── backend/           # FastAPI
│   ├── app/
│   │   ├── models/        # SQLAlchemy: parlamentar, proposicao, votacao, partido
│   │   ├── routers/       # API: questionario, matching, parlamentares, partidos, chat
│   │   ├── services/      # Matching engine, questionário, chat (Claude)
│   │   └── ingestion/     # Clientes das APIs da Câmara e Senado + normalização
│   └── alembic/           # Migrations
├── infra/             # Terraform (VPC, EC2, CloudFront, DNS, SSL)
├── docs/              # Documentação da metodologia
├── docker-compose.yml # Dev: postgres + backend + frontend
└── Makefile           # Atalhos: dev, stop, migrate, test, lint
```

## Fontes de dados

- **Câmara dos Deputados** — [dadosabertos.camara.leg.br](https://dadosabertos.camara.leg.br/api/v2/) — deputados, votações nominais, proposições
- **Senado Federal** — [legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos/) — senadores, votações, matérias

Ambas APIs são públicas e não requerem autenticação.

## Rodando localmente

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

Frontend em `localhost:5173`, backend em `localhost:8000/api`, banco em `localhost:54329`.

### Requisitos

- Docker e Docker Compose
- Node.js 20+ e pnpm (frontend)
- Python 3.12+ e uv (backend)

## Deploy

Push em `main` aciona GitHub Actions:

1. rsync do código para o EC2
2. Docker build (backend + frontend)
3. Docker Compose up

CloudFront na frente com SSL e cache de assets estáticos.

## Quem somos

Somos Fabio Minati e Leo Dias, dois engenheiros brasileiros e amigos desde a universidade. Decidimos seguir nossas carreiras em países diferentes — mas sem deixar o Brasil para trás.

Se este site ajudar alguém a refletir melhor antes de votar nas próximas eleições, então todo esse esforço já terá valido a pena.

## Contribua

O voto.vc é gratuito, sem anúncios e sem coleta de dados pessoais. Você pode apoiar o projeto de duas formas:

- **Código** — PRs, issues e sugestões são bem-vindos
- **Doação** — 100% do excedente operacional é doado ao [Lar Casa Bela](https://larcasabela.org.br), instituição que acolhe crianças em situação de vulnerabilidade

## Licença

[MIT](LICENSE)
