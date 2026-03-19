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
- **Auth**: JWT (python-jose) + bcrypt (passlib) + Google OAuth 2.0
- **Chat**: Anthropic Claude Haiku 4.5 (proposição Q&A with tool use)

## Key conventions

- User prefers Portuguese for communication
- Backend uses `uv` (not pip) for package management
- Frontend uses `pnpm` (not npm/yarn)
- Python 3.12+, type hints throughout
- SQLAlchemy models use `Mapped[]` annotations
- Frontend uses Svelte 5 runes syntax (`$state`, `$derived`, `$effect`), NOT legacy `$:` reactive declarations
- API routes prefixed with `/api/` (e.g., `/api/vote/items`, `/api/matching/calcular`)
- Enum values in DB are UPPERCASE (e.g., `TipoVoto.SIM`, `Casa.CAMARA`)
- `id_externo` format: `camara_{id}` or `senado_{id}`
- Name normalization: title case with lowercase prepositions (de, da, do, dos, das)

## Data model (key tables)

- `parlamentares` — deputies + senators, `sexo` (M/F), `uf`, `partido_id`
- `proposicoes` — legislative items with `resumo_cidadao`, `descricao_detalhada`, `tema`, `relevancia_score`
- `votacoes` — roll call votes linked to proposições
- `votos_parlamentares` — individual votes (enum: SIM, NAO, ABSTENCAO, AUSENTE, OBSTRUCAO, PRESENTE_SEM_VOTO)
- `partidos` — parties with `sigla`
- `usuarios` — user accounts (Google OAuth or email/password), `uf`, `provedor_auth`
- `respostas_usuarios` — user answers to proposições (`usuario_id`, `proposicao_id`, `voto`, `peso`)

## Important files

- `backend/app/services/matching.py` — alignment scoring engine
- `backend/app/services/questionario.py` — topic-diverse question selection (anchors + round-robin by tema)
- `backend/app/ingestion/normalize.py` — API data normalization
- `backend/app/routers/parlamentares.py` — parlamentar detail + voting history
- `backend/app/routers/partidos.py` — partido detail + aggregated voting + disciplina
- `backend/app/routers/auth.py` — Google OAuth + JWT auth + user profile
- `backend/app/routers/questionario.py` — vote endpoints (items, responder, respostas)
- `backend/app/services/chat.py` — proposição chatbot (Claude Haiku 4.5 with tool use)
- `backend/app/routers/chat.py` — SSE streaming chat endpoint
- `backend/app/utils.py` — URL generation (`url_proposicao`, `urls_por_casa`)
- `frontend/src/lib/components/VoteSlider.svelte` — 5-position vote intensity slider
- `frontend/src/lib/components/ChatWidget.svelte` — floating chat widget for proposição Q&A
- `frontend/src/lib/utils/vote.ts` — vote position ↔ voto/peso mapping utilities
- `frontend/src/routes/vote/+page.svelte` — UF selector + question cards + slider + chat
- `frontend/src/routes/perfil/+page.svelte` — ranked results (parlamentares, partidos, votos tabs)
- `frontend/src/routes/parlamentar/[id]/+page.svelte` — parlamentar profile with expandable votes
- `frontend/src/routes/partido/[id]/+page.svelte` — partido profile with aggregated votes + disciplina
- `frontend/src/lib/stores/questionario.ts` — respostas/UF stores with localStorage persistence
- `frontend/src/lib/stores/auth.ts` — auth state (authUser, checkAuth, logout)
- `frontend/src/routes/auth/callback/+page.svelte` — OAuth callback + anonymous data migration
- `infra/cloudfront.tf` — CDN + SSL config
- `.github/workflows/deploy.yml` — CI/CD pipeline

## Production

- Domain: voto.vc (CloudFront → EC2 via origin.voto.vc)
- Server: 44.216.159.100, SSH via `ssh -i ~/.ssh/votovc_deploy ec2-user@44.216.159.100`
- App dir on server: `/opt/votovc/app/`
- Docker containers: votovc-backend-1, votovc-frontend-1, votovc-db-1, votovc-nginx-1
- DB access: `docker exec votovc-db-1 psql -U votovc -d votovc`
- Terraform state in `infra/terraform.tfstate` (local, gitignored)

## Key patterns

- Anonymous users: respostas + UF persisted in localStorage, migrated to DB on login
- Questionnaire: backend accepts `exclude` param with already-answered IDs to always serve fresh questions
- Casa pills: proposições link to both Câmara and Senado pages via `urls_por_casa()` (direct URL or search fallback)
- Vote endpoints mounted at `/api/vote/` (router in `questionario.py`)
- Chat endpoint at `/api/chat/proposicao/{id}` — SSE streaming, auth required, rate limited (30/hour)
- Vote slider: 5 positions map to voto (sim/nao) + peso (0.0–1.0); Neutro = sim with peso=0
- Chat requires `ANTHROPIC_API_KEY` env var; without it, endpoint returns 503

## Don't

- Don't use `pip install` — use `uv` for backend deps
- Don't use Svelte legacy reactive syntax (`$:`, `export let`) — use runes
- Don't commit `terraform.tfvars` or `.env` (contain secrets)
- Don't push force to main
- Don't run `uv run` inside docker exec (hangs) — use `/app/.venv/bin/python` directly
