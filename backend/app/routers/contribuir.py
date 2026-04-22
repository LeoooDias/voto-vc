"""Endpoints for /contribuir donation page (Stripe Checkout)."""

import logging
import time
from collections import defaultdict
from typing import Annotated

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_stripe() -> None:
    if not settings.stripe_secret_key or not settings.stripe_product_id:
        raise HTTPException(status_code=503, detail="Doação não configurada.")
    stripe.api_key = settings.stripe_secret_key


def _parse_rate_limit(limit_str: str) -> tuple[int, int]:
    count_str, period = limit_str.split("/")
    periods = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    return int(count_str), periods.get(period, 3600)


_ip_timestamps: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> None:
    max_count, window = _parse_rate_limit(settings.contribuir_rate_limit)
    now = time.time()
    cutoff = now - window
    _ip_timestamps[ip] = [t for t in _ip_timestamps[ip] if t > cutoff]
    if len(_ip_timestamps[ip]) >= max_count:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Tente novamente em alguns minutos.",
        )
    _ip_timestamps[ip].append(now)


class CheckoutRequest(BaseModel):
    amount_brl: float = Field(..., gt=0, le=10000)


class CheckoutResponse(BaseModel):
    url: str


class SessionStatusResponse(BaseModel):
    status: str  # "paid" | "pending" | "expired" | "unknown"
    amount_brl: float | None = None


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(body: CheckoutRequest, request: Request):
    _ensure_stripe()
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    unit_amount = int(round(body.amount_brl * 100))

    if unit_amount < 50:
        raise HTTPException(status_code=400, detail="Valor mínimo é R$ 1,00.")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "brl",
                        "product": settings.stripe_product_id,
                        "unit_amount": unit_amount,
                    },
                    "quantity": 1,
                }
            ],
            payment_method_types=["card", "pix"],
            success_url=(
                f"{settings.frontend_url}/contribuir/obrigado?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.frontend_url}/contribuir",
        )
    except stripe.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=502, detail="Erro ao iniciar pagamento.") from e

    return CheckoutResponse(url=session.url)


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def session_status(session_id: str):
    _ensure_stripe()

    if not session_id.startswith("cs_") or len(session_id) > 200:
        raise HTTPException(status_code=400, detail="session_id inválido.")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError as e:
        logger.warning(f"Stripe session retrieve error: {e}")
        raise HTTPException(status_code=404, detail="Sessão não encontrada.") from e

    payment_status = session.payment_status
    status_map = {"paid": "paid", "unpaid": "pending", "no_payment_required": "paid"}
    status = status_map.get(payment_status, "unknown")
    if session.status == "expired":
        status = "expired"

    amount_total = session.amount_total
    amount_brl = amount_total / 100 if amount_total else None
    return SessionStatusResponse(status=status, amount_brl=amount_brl)


@router.post("/webhook")
async def webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
):
    if not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook recebido sem STRIPE_WEBHOOK_SECRET configurado")
        return {"received": True, "verified": False}

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Payload inválido") from e
    except stripe.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Assinatura inválida") from e

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        amount = (obj.amount_total or 0) / 100
        logger.info(
            f"Doação concluída: R$ {amount:.2f} session={obj.id} "
            f"payment_status={obj.payment_status}"
        )
    elif event_type == "checkout.session.async_payment_succeeded":
        amount = (obj.amount_total or 0) / 100
        logger.info(f"Pix confirmado: R$ {amount:.2f} session={obj.id}")
    elif event_type == "checkout.session.async_payment_failed":
        logger.warning(f"Pix falhou: session={obj.id}")
    else:
        logger.debug(f"Stripe webhook não tratado: {event_type}")

    return {"received": True, "verified": True}
