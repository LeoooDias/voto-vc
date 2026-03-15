import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Adds a unique request ID to each request and logs request/response info."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 1)

            if not path.startswith("/api/health"):
                logger.info(
                    "request",
                    request_id=request_id,
                    method=method,
                    path=path,
                    status=response.status_code,
                    duration_ms=duration_ms,
                )

            response.headers["X-Request-Id"] = request_id
            return response

        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.error(
                "request_error",
                request_id=request_id,
                method=method,
                path=path,
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise
