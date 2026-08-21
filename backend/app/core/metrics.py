import time

from prometheus_client import Counter, Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

PUBLIC_REQUESTS = Counter(
    "stockstack_public_product_requests_total", "Public product requests", ["result"]
)
CACHE_RESULTS = Counter(
    "stockstack_product_cache_total", "Product cache operations", ["result"]
)
DB_FALLBACKS = Counter(
    "stockstack_product_db_fallback_total", "Protected direct DB fallbacks", ["reason"]
)
LOCK_CONTENTION = Counter(
    "stockstack_product_lock_contention_total", "Product cache lock contention"
)
RATE_LIMIT_RESULTS = Counter(
    "stockstack_public_rate_limit_total", "Public rate limit decisions", ["result"]
)
DEPENDENCY_ERRORS = Counter(
    "stockstack_dependency_errors_total", "Dependency failures", ["dependency", "operation"]
)
PUBLIC_LATENCY = Histogram(
    "stockstack_public_product_latency_seconds", "Public product request latency"
)


class PublicProductMetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(
            "/api/v1/public/products/"
        ):
            await self.app(scope, receive, send)
            return

        started = time.monotonic()
        status_code = 500

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            PUBLIC_REQUESTS.labels(str(status_code)).inc()
            PUBLIC_LATENCY.observe(time.monotonic() - started)
