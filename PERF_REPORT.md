# Performance Report

**Date:** _YYYY-MM-DD_
**Operator:** _Name_
**Cluster:** kind / minikube (local)
**Tool:** k6 v0.50+

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Ramp-up | 30s to 5 VUs |
| Steady state | 60s at 10 VUs |
| Peak | 30s at 20 VUs |
| Ramp-down | 30s to 0 VUs |
| Total duration | ~2.5 min |

---

## Procurement Platform

**Target:** `http://localhost:8001`

| Metric | Value |
|--------|-------|
| Total requests | _____  |
| Requests/s (avg) | _____ |
| p50 latency | _____ ms |
| p95 latency | _____ ms |
| p99 latency | _____ ms |
| Error rate | _____ % |
| Checks passed | _____ % |

### Endpoint Breakdown

| Endpoint | Avg Latency | p95 | Error % |
|----------|-------------|-----|---------|
| GET /health | ___ ms | ___ ms | ___ % |
| POST /graphql (introspection) | ___ ms | ___ ms | ___ % |
| POST /graphql (list PRs) | ___ ms | ___ ms | ___ % |
| GET /metrics | ___ ms | ___ ms | ___ % |

---

## Integrations Hub

**Target:** `http://localhost:8002`

| Metric | Value |
|--------|-------|
| Total requests | _____ |
| Requests/s (avg) | _____ |
| p50 latency | _____ ms |
| p95 latency | _____ ms |
| p99 latency | _____ ms |
| Error rate | _____ % |
| Checks passed | _____ % |

### Endpoint Breakdown

| Endpoint | Avg Latency | p95 | Error % |
|----------|-------------|-----|---------|
| GET /health | ___ ms | ___ ms | ___ % |
| GET /api/v1/subscriptions | ___ ms | ___ ms | ___ % |
| POST /api/v1/events | ___ ms | ___ ms | ___ % |
| GET /metrics | ___ ms | ___ ms | ___ % |

---

## Observations

_Summarize key findings. For example:_

- _Both services handled 10 VUs comfortably with p95 < 100ms._
- _At 20 VUs peak, procurement-platform p95 rose to Xms due to GraphQL resolver complexity._
- _Integrations hub event publishing stayed under Yms p95 throughout._
- _No 5xx errors observed during the entire run._
- _PostgreSQL CPU usage peaked at Z% during the load test._

---

## Recommendations

_List any recommended changes based on results:_

1. _Add connection pooling if p95 degrades under higher concurrency._
2. _Consider caching GraphQL introspection responses._
3. _Webhook delivery worker may need horizontal scaling for production loads._

---

## Example Filled Report

> Below is an example from a test run on a kind cluster (4 CPU, 8GB RAM host):

**Date:** 2026-02-14
**Operator:** Dev
**Cluster:** kind (local, Docker Desktop)

### Procurement Platform

| Metric | Value |
|--------|-------|
| Total requests | 1,847 |
| Requests/s (avg) | 12.3 |
| p50 latency | 18 ms |
| p95 latency | 89 ms |
| p99 latency | 142 ms |
| Error rate | 0.0% |
| Checks passed | 100% |

### Integrations Hub

| Metric | Value |
|--------|-------|
| Total requests | 1,923 |
| Requests/s (avg) | 12.8 |
| p50 latency | 12 ms |
| p95 latency | 45 ms |
| p99 latency | 78 ms |
| Error rate | 0.0% |
| Checks passed | 100% |

### Observations

- Both services performed well within SLO thresholds (p95 < 500ms).
- Procurement platform's GraphQL endpoint is ~4x slower than REST health checks, expected for query resolution.
- Integrations hub event publishing adds minimal overhead (~15ms p50).
- No resource contention observed. PostgreSQL CPU stayed under 10%.

### Recommendations

1. Current resource limits (256Mi/500m CPU) are sufficient for local testing.
2. For production, set up PgBouncer for connection pooling.
3. Consider read replicas if GraphQL query load increases.
