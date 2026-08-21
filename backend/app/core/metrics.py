from prometheus_client import Counter, Histogram

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

