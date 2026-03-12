# CLAUDE.md

## Project

voto.vc — Brazilian voter alignment tool for the 2026 federal elections. Monorepo with `frontend/` (SvelteKit 5) and `backend/` (FastAPI).

## Commands

```bash
make dev          # docker compose up (postgres + backend + frontend)
make stop         # docker compose down
make migrate      # alembic upgrade head
make test         # pytest + pnpm test
make lint         # ruff + pnpm lint
```

### Backend (from `backend/`)
```bash
uv run pytest                          # tests
uv run ruff check . && uv run ruff format --check .  # lint
uv run alembic upgrade head            # migrations
uv run alembic revision --autogenerate -m "desc"      # new migration
```

### Frontend (from `frontend/`)
```bash
pnpm dev          # dev server :5173
pnpm build        # production build
pnpm check        # svelte-check
```

## Architecture

- **Backend**: FastAPI, async SQLAlchemy 2.0, asyncpg, PostgreSQL 16, Alembic
- **Frontend**: SvelteKit 5, TypeScript, adapter-node, Svelte 5 runes (`$state`, `$derived`)
- **Infra**: AWS us-east-1, Terraform, EC2 t4g.small (ARM64), CloudFront, Route 53
- **CI/CD**: GitHub Actions on push to main → rsync → docker build → compose up
- **Auth**: JWT (python-jose) + bcrypt (passlib) — not yet active in MVP

## Key conventions

- User prefers Portuguese for communication
- Backend uses `uv` (not pip) for package management
- Frontend uses `pnpm` (not npm/yarn)
- Python 3.12+, type hints throughout
- SQLAlchemy models use `Mapped[]` annotations
- Frontend uses Svelte 5 runes syntax (`$state`, `$derived`, `$effect`), NOT legacy `$:` reactive declarations
- API routes prefixed with `/api/` (e.g., `/api/questionario/items`, `/api/matching/calcular`)
- Enum values in DB are UPPERCASE (e.g., `TipoVoto.SIM`, `Casa.CAMARA`)
- `id_externo` format: `camara_{id}` or `senado_{id}`
- Name normalization: title case with lowercase prepositions (de, da, do, dos, das)

## Data model (key tables)

- `parlamentares` — deputies + senators, `sexo` (M/F), `uf`, `partido_id`
- `proposicoes` — legislative items with `resumo_cidadao`, `descricao_detalhada`, `tema`, `relevancia_score`
- `votacoes` — roll call votes linked to proposições
- `votos_parlamentares` — individual votes (enum: SIM, NAO, ABSTENCAO, AUSENTE, OBSTRUCAO, PRESENTE_SEM_VOTO)
- `partidos` — parties with `sigla`

## Important files

- `backend/app/services/matching.py` — alignment scoring engine
- `backend/app/services/questionario.py` — topic-diverse question selection
- `backend/app/ingestion/normalize.py` — API data normalization
- `backend/app/routers/parlamentares.py` — parlamentar detail + voting history
- `frontend/src/routes/questionario/+page.svelte` — UF selector + question cards
- `frontend/src/routes/resultado/+page.svelte` — ranked results
- `frontend/src/routes/parlamentar/[id]/+page.svelte` — parlamentar profile with expandable votes
- `infra/cloudfront.tf` — CDN + SSL config
- `.github/workflows/deploy.yml` — CI/CD pipeline

## Production

- Domain: voto.vc (CloudFront → EC2 via origin.voto.vc)
- Server: 44.216.159.100, SSH via `ssh -i ~/.ssh/votovc_deploy ec2-user@44.216.159.100`
- App dir on server: `/opt/votovc/app/`
- Docker containers: votovc-backend-1, votovc-frontend-1, votovc-db-1, votovc-nginx-1
- DB access: `docker exec votovc-db-1 psql -U votovc -d votovc`
- Terraform state in `infra/terraform.tfstate` (local, gitignored)

## Don't

- Don't use `pip install` — use `uv` for backend deps
- Don't use Svelte legacy reactive syntax (`$:`, `export let`) — use runes
- Don't commit `terraform.tfvars` or `.env` (contain secrets)
- Don't push force to main
- Don't run `uv run` inside docker exec (hangs) — use `/app/.venv/bin/python` directly
