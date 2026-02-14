# Infra & Observability Pack

Local Kubernetes deployment with Prometheus monitoring, Grafana dashboards, and load testing for the portfolio services.

## What's Included

```
infra-observability-pack/
├── kubernetes/                  # K8s manifests
│   ├── namespace.yaml
│   ├── postgres/                # Shared PostgreSQL (separate DBs)
│   ├── procurement-platform/    # Deployment, Service, ConfigMap, Secret
│   └── integrations-hub/        # Deployment, Service, ConfigMap, Secret
├── observability/
│   ├── prometheus/              # Scrape config + deployment
│   └── grafana/                 # Datasource, dashboard, deployment
├── load-testing/
│   ├── k6-procurement.js        # k6 script for procurement-platform
│   ├── k6-integrations.js       # k6 script for integrations-hub
│   └── run-load-test.sh         # Runner
├── scripts/
│   ├── setup-cluster.sh         # Create kind/minikube cluster
│   ├── build-images.sh          # Build & load Docker images
│   ├── deploy-all.sh            # Deploy entire stack
│   ├── port-forward.sh          # Forward all ports to localhost
│   └── teardown.sh              # Clean up
├── ci/
│   ├── lint-yaml.sh             # YAML linting
│   ├── validate-manifests.sh    # kubectl dry-run validation
│   └── smoke-test.sh            # Health check all endpoints
├── patches/
│   └── procurement-platform-metrics.py  # Prometheus metrics for procurement_platform
├── RUNBOOK.md                   # Incident debugging guide
├── PERF_REPORT.md               # Load test report template + example
└── TASKS.md                     # Task tracking
```

## Prerequisites

- **Docker** (Docker Desktop or equivalent)
- **kubectl** (v1.28+)
- **kind** or **minikube** (for local cluster)
- **k6** (for load testing) - [install](https://grafana.com/docs/k6/latest/set-up/install-k6/)

Verify:
```bash
docker version
kubectl version --client
kind version    # or: minikube version
```

## Quick Start

### 1. Create the cluster

```bash
./scripts/setup-cluster.sh
```

Creates a `kind` cluster named `portfolio` (falls back to minikube if kind isn't available).

### 2. Build and load images

```bash
./scripts/build-images.sh
```

This will:
- Patch `procurement_platform` to add Prometheus metrics (if not already patched)
- Fix the Dockerfile to remove `--reload`
- Build `procurement-platform:local` and `integrations-hub:local`
- Load images into the cluster

### 3. Deploy everything

```bash
./scripts/deploy-all.sh
```

Deploys in order: namespace -> PostgreSQL -> apps -> Prometheus -> Grafana.

### 4. Access services

```bash
./scripts/port-forward.sh
```

| Service | URL |
|---------|-----|
| Procurement Platform | http://localhost:8001 |
| Integrations Hub | http://localhost:8002 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Grafana credentials: `admin` / `admin`

### 5. Verify with smoke tests

```bash
./ci/smoke-test.sh
```

### 6. Run load tests

```bash
./load-testing/run-load-test.sh
```

Results are saved to `load-testing/results/`. Copy numbers into `PERF_REPORT.md`.

### 7. Tear down

```bash
./scripts/teardown.sh
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  kind / minikube                      │
│                  namespace: portfolio                 │
│                                                      │
│  ┌─────────────────┐    ┌──────────────────┐        │
│  │ procurement-     │    │ integrations-    │        │
│  │ platform         │    │ hub              │        │
│  │ :8000            │    │ :8000            │        │
│  │ /health          │    │ /health          │        │
│  │ /graphql         │    │ /api/v1/*        │        │
│  │ /metrics ────────┼────│ /metrics ────────┼──┐    │
│  └────────┬─────────┘    └────────┬─────────┘  │    │
│           │                       │             │    │
│           └───────┬───────────────┘             │    │
│                   │                             │    │
│          ┌────────▼─────────┐          ┌───────▼──┐ │
│          │ PostgreSQL       │          │Prometheus│ │
│          │ :5432            │          │ :9090    │ │
│          │ - procurement    │          └────┬─────┘ │
│          │ - integrations_  │               │       │
│          │   hub            │          ┌────▼─────┐ │
│          └──────────────────┘          │ Grafana  │ │
│                                        │ :3000    │ │
│                                        └──────────┘ │
└──────────────────────────────────────────────────────┘

Port forwards:
  localhost:8001 → procurement-platform:8000
  localhost:8002 → integrations-hub:8000
  localhost:9090 → prometheus:9090
  localhost:3000 → grafana:3000
```

## Secrets Management

For local development, secrets are stored as plaintext in `stringData` within Secret manifests. This is intentional for ease of use.

**For production:** replace with:
- Sealed Secrets
- External Secrets Operator
- Vault integration

The Secret manifests are `.gitignore`-safe patterns. Rotate credentials before any non-local use.

## Grafana Dashboard

The pre-built dashboard ("Portfolio Overview") shows:

| Panel | Metrics |
|-------|---------|
| Request Rate | `http_requests_total` per service |
| Error Rate | `http_requests_total{status_code=~"5.."}` |
| Latency Percentiles | `http_request_duration_seconds_bucket` p50/p95/p99 |
| Webhook Queue Depth | `webhook_deliveries_total`, `events_published_total` |
| Webhook Delivery Duration | `webhook_delivery_duration_seconds_bucket` |
| Service Health | `up{}` per scrape target |

## Customization

### Add a new service

1. Create a directory under `kubernetes/<service-name>/`
2. Add `deployment.yaml`, `service.yaml`, `configmap.yaml`, `secret.yaml`
3. Add a scrape job in `observability/prometheus/configmap.yaml`
4. Add panels to `observability/grafana/dashboard.json`
5. Create a k6 script in `load-testing/`

### Adjust resource limits

Edit the `resources` block in the relevant deployment manifest. For local clusters, the defaults (128Mi-256Mi RAM, 100m-500m CPU) are conservative.

### Change database configuration

Edit `kubernetes/postgres/secret.yaml` for credentials and `kubernetes/postgres/configmap.yaml` for the init script.

## Troubleshooting

See [RUNBOOK.md](RUNBOOK.md) for detailed debugging procedures.

Quick checks:
```bash
# Pod status
kubectl -n portfolio get pods

# Logs
kubectl -n portfolio logs deployment/<name>

# Events
kubectl -n portfolio get events --sort-by='.lastTimestamp'
```
