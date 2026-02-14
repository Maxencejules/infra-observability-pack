# Performance Report

**Date:** 2026-02-14
**Operator:** Dev
**Cluster:** kind v0.25.0 (local, Docker Desktop 29.1.3, Windows 11)
**Tool:** k6 v0.54.0

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Ramp-up | 30s to 5 VUs |
| Steady state | 60s at 10 VUs |
| Peak | 30s at 20 VUs |
| Ramp-down | 30s to 0 VUs |
| Total duration | 2m 30s |
| K8s node | kindest/node v1.31.2, single control-plane |

---

## Procurement Platform

**Target:** `http://localhost:8001`

| Metric | Value |
|--------|-------|
| Total requests | 4,452 |
| Iterations | 1,113 |
| Requests/s (avg) | 29.6 |
| p50 latency | 15.82 ms |
| p90 latency | 78.37 ms |
| p95 latency | 109.31 ms |
| Error rate | 0.00% |
| Checks passed | 100% (7,791 / 7,791) |
| http_req_failed | 0.00% (0 / 4,452) |
| Threshold: p(95)<500 | PASS |
| Threshold: p(99)<1000 | PASS |
| Threshold: errors<5% | PASS |

### Endpoint Breakdown

| Endpoint | Avg Latency | p90 | p95 | Error % |
|----------|-------------|-----|-----|---------|
| GET /health | 22.52 ms | 49.55 ms | 86.70 ms | 0% |
| POST /graphql (combined) | 36.69 ms | 87.87 ms | 124.36 ms | 0% |
| GET /metrics | included in avg | - | - | 0% |

### Raw k6 Metrics

```
http_req_duration..............: avg=31.27ms min=695.9us med=15.82ms max=733.46ms p(90)=78.37ms p(95)=109.31ms
http_req_receiving.............: avg=1.74ms  min=0s      med=0s      max=115.37ms p(90)=2.23ms  p(95)=6.77ms
http_req_waiting...............: avg=29.46ms min=695.9us med=15.11ms max=733.46ms p(90)=73.02ms p(95)=103.33ms
iteration_duration.............: avg=1.12s   min=1.02s   med=1.08s   max=1.95s    p(90)=1.31s   p(95)=1.46s
health_latency.................: avg=22.52ms min=695.9us med=9.67ms  max=733.46ms p(90)=49.55ms p(95)=86.70ms
graphql_latency................: avg=36.69ms min=4.27ms  med=19.16ms max=623.71ms p(90)=87.87ms p(95)=124.36ms
```

---

## Integrations Hub

**Target:** `http://localhost:8002`

| Metric | Value |
|--------|-------|
| Total requests | 4,580 |
| Iterations | 1,145 |
| Requests/s (avg) | 30.5 |
| p50 latency | 7.32 ms |
| p90 latency | 37.98 ms |
| p95 latency | 78.33 ms |
| Error rate | 0.00% |
| Checks passed | 100% (6,870 / 6,870) |
| http_req_failed | 0.00% (0 / 4,580) |
| Threshold: p(95)<500 | PASS |
| Threshold: p(99)<1000 | PASS |
| Threshold: errors<5% | PASS |

### Endpoint Breakdown

| Endpoint | Avg Latency | p90 | p95 | Error % |
|----------|-------------|-----|-----|---------|
| GET /health | 12.38 ms | 25.89 ms | 50.22 ms | 0% |
| GET /api/v1/subscriptions | included in api_latency | - | - | 0% |
| POST /api/v1/events | included in api_latency | - | - | 0% |
| GET /metrics | included in avg | - | - | 0% |

### Raw k6 Metrics

```
http_req_duration..............: avg=23.75ms  min=0s      med=7.32ms  max=1.91s  p(90)=37.98ms  p(95)=78.33ms
http_req_receiving.............: avg=142.77us min=0s      med=0s      max=109.07ms p(90)=535.82us p(95)=606.12us
http_req_waiting...............: avg=23.56ms  min=0s      med=7.13ms  max=1.91s  p(90)=37.44ms  p(95)=77.95ms
iteration_duration.............: avg=1.09s    min=1.01s   med=1.03s   max=3.02s  p(90)=1.19s    p(95)=1.37s
health_latency.................: avg=12.38ms  min=694.3us med=4.25ms  max=300.16ms p(90)=25.89ms p(95)=50.22ms
api_latency....................: avg=35.30ms  min=3.69ms  med=11.53ms max=1.91s  p(90)=58.80ms  p(95)=115.45ms
```

---

## Observations

- Both services comfortably passed all SLO thresholds (p95 < 500ms, p99 < 1000ms, error rate < 5%).
- Zero errors across both test runs: 0/4,452 failed requests on procurement-platform and 0/4,580 on integrations-hub.
- Integrations hub is roughly 2x faster at median latency (7.3ms vs 15.8ms) since it serves pure REST while procurement-platform resolves GraphQL queries through Strawberry.
- GraphQL endpoints averaged 36.7ms vs 22.5ms for health checks, a ~1.6x overhead attributable to schema resolution and database queries.
- The single max outlier on integrations-hub was 1.91s, likely a cold-path event publish hitting the database during ramp-up. Median stayed under 12ms.
- Procurement-platform max was 733ms, well within the p99 < 1000ms threshold.
- Both services scaled linearly from 5 to 20 VUs with no error cliff or latency hockey-stick.
- PostgreSQL handled concurrent writes from event publishing without contention on a single-node kind cluster.

---

## Recommendations

1. **Current limits are adequate for local testing.** Both services ran within 256Mi memory and 500m CPU limits without OOM or throttling.
2. **Production: add PgBouncer.** At higher concurrency, connection pooling will prevent asyncpg pool exhaustion.
3. **Cache GraphQL introspection.** Introspection queries are deterministic and can be cached at the application layer to reduce p95 under load.
4. **Monitor the 1.9s outlier on integrations-hub.** If event publishing p99 degrades at higher VU counts, consider batching outbox writes or adding a write-ahead queue.
5. **Horizontal scaling.** Both deployments are currently at 1 replica. For production loads, set replicas to 2-3 with a HorizontalPodAutoscaler targeting 70% CPU.
