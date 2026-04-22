# Doações (`/contribuir`) — Configuração e Operação

> Arquivos principais:
> - Backend: `backend/app/routers/contribuir.py`, `backend/app/config.py`
> - Frontend: `frontend/src/routes/contribuir/+page.svelte`, `frontend/src/routes/contribuir/obrigado/+page.svelte`
> Conta Stripe: **ClearWorks Foundry Inc.** (`acct_1ShdatJeksT2bjKE`, sediada no Canadá)

---

## Visão geral

A página `/contribuir` aceita doações em BRL via **Stripe Checkout** com cartão e Pix. Como a conta Stripe é canadense, os pagamentos são tratados como **cross-border**: o donor vê o valor em R$, mas o repasse para a conta bancária CAD é feito com câmbio do Stripe (e o banco do donor cobra IOF por cima — disclosure já aparece na página).

Fluxo:

1. Usuário escolhe valor → `POST /api/contribuir/checkout` cria uma `Checkout Session` com `payment_method_types=["card","pix"]` e redireciona para Stripe Checkout.
2. Stripe processa pagamento → redireciona para `/contribuir/obrigado?session_id={CHECKOUT_SESSION_ID}`.
3. Página de obrigado faz `GET /api/contribuir/session/{id}` para mostrar status (`paid`/`pending`/`expired`).
4. Stripe envia webhook para `POST /api/contribuir/webhook` com eventos do ciclo de vida da sessão (registramos no log).

Sem persistência em DB — tudo registrado apenas no Stripe Dashboard. Página é **invisível na navegação** (acesso direto pela URL) até decidirmos abrir.

---

## Variáveis de ambiente

Todas opcionais — se ausentes, `/api/contribuir/*` retorna 503.

| Var | Uso | Onde obter |
|---|---|---|
| `STRIPE_SECRET_KEY` | Auth nas chamadas server-side (Checkout, retrieve, etc.) | Dashboard → Developers → API keys |
| `STRIPE_PRODUCT_ID` | Produto associado ao line item do Checkout (descrição visível ao donor) | Dashboard → Product catalog |
| `STRIPE_WEBHOOK_SECRET` | Verificação de assinatura HMAC dos webhooks recebidos | Dashboard → Developers → Webhooks → endpoint → signing secret |
| `CONTRIBUIR_RATE_LIMIT` | Limite por IP (default `10/hour`) | — |

**Locais:**

- **Local (dev):** `/Users/leo/source/voto-vc/.env` — chaves test mode (`sk_test_...`, `whsec_...` do `stripe listen`)
- **Produção:** `/opt/votovc/.env` no servidor (44.216.159.100) — chaves live mode

⚠️ O `.env` em `/opt/votovc/app/.env` (dentro do diretório de código) **não é lido em produção**. O `docker-compose.yml` de prod fica em `/opt/votovc/` e usa `env_file: .env` relativo a esse diretório. Editar o errado é um foot-gun comum.

---

## Configuração inicial (one-time, já feito)

Realizado em 2026-04-22. Documentado para quem tiver que refazer (nova conta, environment isolado, etc.).

### 1. Criar produto live

```bash
stripe products create --api-key sk_live_... \
  -d "name=Contribuição voto.vc" \
  -d "description=Doação para o projeto voto.vc — apoia custos operacionais do site e o Lar Casa Bela"
# → prod_UNdQX49vVuiDDw
```

### 2. Criar webhook endpoint

```bash
stripe webhook_endpoints create --api-key sk_live_... \
  -d "url=https://voto.vc/api/contribuir/webhook" \
  -d "enabled_events[]=checkout.session.completed" \
  -d "enabled_events[]=checkout.session.async_payment_succeeded" \
  -d "enabled_events[]=checkout.session.async_payment_failed" \
  -d "description=voto.vc /contribuir donations"
# → we_..., secret whsec_...
```

### 3. Popular `.env` de produção

```bash
ssh -i ~/.ssh/votovc_deploy ec2-user@44.216.159.100 "cat >> /opt/votovc/.env" <<EOF
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PRODUCT_ID=prod_...
STRIPE_WEBHOOK_SECRET=whsec_...
EOF
```

### 4. Reiniciar backend pra carregar o `.env`

```bash
ssh -i ~/.ssh/votovc_deploy ec2-user@44.216.159.100 "cd /opt/votovc && docker compose restart backend"
```

(O deploy via GitHub Actions faz isso automaticamente, mas se você só editou o `.env`, precisa restart manual.)

---

## Rotação de chaves

### `STRIPE_SECRET_KEY`

Use quando suspeitar de exposição (ex.: chave foi parar em log, repo, conversa pública).

```bash
# 1. Cria nova chave no Dashboard
#    https://dashboard.stripe.com/apikeys → "Create restricted key" ou "Roll" na standard key
# 2. Atualiza local
sed -i '' 's|^STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=sk_live_NEW|' /Users/leo/source/voto-vc/.env
# 3. Atualiza prod
ssh -i ~/.ssh/votovc_deploy ec2-user@44.216.159.100 \
  "sed -i 's|^STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=sk_live_NEW|' /opt/votovc/.env && cd /opt/votovc && docker compose restart backend"
# 4. Revoga a chave antiga no Dashboard
```

### `STRIPE_WEBHOOK_SECRET`

Cada webhook endpoint tem seu próprio secret. Pra rotacionar:

```bash
# 1. Recria o endpoint (gera novo secret)
stripe webhook_endpoints delete we_OLD --api-key sk_live_...
stripe webhook_endpoints create --api-key sk_live_... \
  -d "url=https://voto.vc/api/contribuir/webhook" \
  -d "enabled_events[]=checkout.session.completed" \
  -d "enabled_events[]=checkout.session.async_payment_succeeded" \
  -d "enabled_events[]=checkout.session.async_payment_failed"
# → novo whsec_...
# 2. Atualiza prod (mesmo padrão de sed acima) e restart backend
```

Alternativa: criar novo endpoint, atualizar `.env`, e só depois deletar o antigo (evita janela onde webhooks falham).

### `STRIPE_PRODUCT_ID`

Geralmente não rotaciona. Se quiser trocar (ex.: novo nome/descrição visível no Checkout), basta criar produto novo e atualizar a env var. Produtos antigos podem ser arquivados no Dashboard.

---

## Dev local

```bash
# Terminal 1: forward webhooks Stripe → local
stripe listen --forward-to localhost:8000/api/contribuir/webhook
# Copia o whsec_... que aparece e coloca em .env como STRIPE_WEBHOOK_SECRET

# Terminal 2: backend + frontend
make dev

# Cartão de teste: 4242 4242 4242 4242, qualquer CVC/data futura
# Pix: Stripe Checkout dá um QR fake; clicar "Simular pagamento" no Dashboard
```

⚠️ Em test mode, **não use** chaves live mode. O `.env` local deve ter `sk_test_...` e `whsec_...` do `stripe listen`. As chaves live só ficam em `/opt/votovc/.env` no servidor.

---

## Observabilidade

- **Logs do backend:** `docker logs voto-vc-backend-1 --tail 100 | grep contribuir`
- **Stripe Dashboard:** https://dashboard.stripe.com/payments — lista todas as sessões/pagamentos
- **Webhook deliveries:** Dashboard → Developers → Webhooks → endpoint → "Recent events" (mostra payload, status code da resposta, retries)

Se um pagamento for confirmado e o webhook falhar, o Stripe **retenta** automaticamente por até 3 dias (exponential backoff). Sem perda de dados.

---

## Endpoints

### `POST /api/contribuir/checkout`

```json
// Request
{ "amount_brl": 20 }

// Response
{ "url": "https://checkout.stripe.com/c/pay/cs_live_..." }
```

Validações: `amount_brl` em (0, 10000]; valor mínimo 50 centavos. Rate limit por IP (`CONTRIBUIR_RATE_LIMIT`).

### `GET /api/contribuir/session/{session_id}`

```json
// Response
{ "status": "paid" | "pending" | "expired" | "unknown", "amount_brl": 20.0 }
```

Usado pela página `/contribuir/obrigado` pra confirmar o status após retorno do Checkout.

### `POST /api/contribuir/webhook`

Recebe eventos do Stripe. Validação por assinatura HMAC (`STRIPE_WEBHOOK_SECRET`). Eventos tratados:

- `checkout.session.completed` — pagamento finalizado (cartão = imediato; Pix = sessão criada, pagamento ainda assíncrono)
- `checkout.session.async_payment_succeeded` — Pix confirmado pelo banco
- `checkout.session.async_payment_failed` — Pix expirou ou foi rejeitado

Hoje só logamos. Se quisermos persistir doações em DB no futuro, é onde ganchar.
