"""
Prometheus metrics module for procurement_platform.

Drop this file into procurement_platform/backend/app/metrics.py
and apply the patch to main.py shown in PATCH_INSTRUCTIONS below.

PATCH_INSTRUCTIONS:
  In backend/app/main.py, add these two lines:

    from app.metrics import metrics_endpoint, PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics_endpoint)

  Place them after the CORS middleware and before the graphql router.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        status = str(response.status_code)

        http_requests_total.labels(method=method, path=path, status_code=status).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)

        return response


async def metrics_endpoint(request: Request) -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
