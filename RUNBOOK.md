# Runbook - Portfolio Infrastructure

## Service Overview

| Service | Port | Health | Metrics |
|---------|------|--------|---------|
| procurement-platform | 8001 (forwarded) | `/health` | `/metrics` |
| integrations-hub | 8002 (forwarded) | `/health` | `/metrics` |
| PostgreSQL | 5432 | `pg_isready` | - |
| Prometheus | 9090 | `/-/ready` | - |
| Grafana | 3000 | `/api/health` | - |

---

## Common Issues

### 1. Pod stuck in CrashLoopBackOff

**Symptoms:** `kubectl -n portfolio get pods` shows `CrashLoopBackOff` status.

**Diagnosis:**
```bash
# Check pod logs
kubectl -n portfolio logs <pod-name> --previous

# Check events
kubectl -n portfolio describe pod <pod-name>
```

**Common causes:**
- **Database not ready:** The init container `wait-for-postgres` should handle this. If postgres itself is crashing, check its logs first.
- **Missing env var:** Compare the deployment's env section with what the app expects. Check `kubectl -n portfolio get secret <name> -o yaml`.
- **OOM killed:** Check `kubectl -n portfolio describe pod <pod-name>` for `OOMKilled`. Increase memory limits in the deployment manifest.

**Resolution:**
```bash
# If postgres is the issue
kubectl -n portfolio rollout restart statefulset/postgres

# If an app is the issue after fixing config
kubectl -n portfolio rollout restart deployment/<app-name>
```

---

### 2. Database connection refused

**Symptoms:** App logs show `Connection refused` or `could not connect to server`.

**Diagnosis:**
```bash
# Check postgres pod
kubectl -n portfolio get pods -l app=postgres

# Check postgres logs
kubectl -n portfolio logs postgres-0

# Test connectivity from app pod
kubectl -n portfolio exec -it deployment/procurement-platform -- \
  sh -c "nc -z postgres 5432 && echo OK || echo FAIL"
```

**Common causes:**
- PostgreSQL pod not running or not ready.
- Init script failed (database not created). Check logs for the init container.
- Wrong connection string in secret.

**Resolution:**
```bash
# Recreate databases manually if init failed
kubectl -n portfolio exec -it postgres-0 -- psql -U postgres -c "CREATE DATABASE procurement;"
kubectl -n portfolio exec -it postgres-0 -- psql -U postgres -c "CREATE DATABASE integrations_hub;"

# Restart apps
kubectl -n portfolio rollout restart deployment/procurement-platform
kubectl -n portfolio rollout restart deployment/integrations-hub
```

---

### 3. Prometheus not scraping targets

**Symptoms:** Grafana dashboards show "No data". Prometheus targets page shows targets as DOWN.

**Diagnosis:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Check if app metrics endpoint works
curl http://localhost:8001/metrics
curl http://localhost:8002/metrics
```

**Common causes:**
- App pod not ready (readiness probe failing).
- Wrong service name or port in `prometheus.yml` ConfigMap.
- Metrics endpoint not mounted in the app.

**Resolution:**
```bash
# Edit prometheus config
kubectl -n portfolio edit configmap prometheus-config

# Reload Prometheus (lifecycle API enabled)
curl -X POST http://localhost:9090/-/reload
```

---

### 4. Grafana shows "No data" on panels

**Symptoms:** Dashboard loads but panels show "No data".

**Diagnosis:**
1. Open Grafana (http://localhost:3000) > Explore.
2. Select the Prometheus datasource.
3. Try a simple query: `up`.
4. If `up` returns data, the issue is with the specific metric name.

**Common causes:**
- Prometheus datasource URL wrong. Check Settings > Data sources.
- App hasn't received traffic yet (counters start at 0, rates show nothing).
- Dashboard uses metric names that don't match what the app exports.

**Resolution:**
```bash
# Generate some traffic
curl http://localhost:8001/health
curl http://localhost:8002/health

# Check what metrics exist
curl -s http://localhost:8001/metrics | head -30
curl -s http://localhost:8002/metrics | head -30
```

---

### 5. High latency / slow responses

**Symptoms:** p95 latency exceeds SLO threshold on Grafana dashboard.

**Diagnosis:**
```bash
# Check pod resource usage
kubectl -n portfolio top pods

# Check if postgres is the bottleneck
kubectl -n portfolio exec -it postgres-0 -- \
  psql -U postgres -c "SELECT * FROM pg_stat_activity WHERE state != 'idle';"

# Check app logs for slow queries
kubectl -n portfolio logs deployment/procurement-platform | grep -i slow
```

**Common causes:**
- Resource limits too low for load.
- Database queries not optimized (missing indexes).
- Connection pool exhaustion.

**Resolution:**
- Increase resource limits in deployment manifests.
- Add database indexes.
- Tune connection pool settings via environment variables.

---

### 6. Port forward disconnects

**Symptoms:** `port-forward.sh` exits or connections drop.

**Resolution:**
```bash
# Just re-run it
./scripts/port-forward.sh

# Or forward a single service
kubectl -n portfolio port-forward svc/grafana 3000:3000
```

---

## Alerting Thresholds (Reference)

These are the thresholds used in the Grafana dashboard. They're informational for a local setup but would map to alerts in production.

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate (5xx/s) | > 0.1 | > 1.0 |
| p95 latency | > 500ms | > 1000ms |
| Webhook queue depth | > 50 | > 200 |
| Pod restarts (5m) | > 2 | > 5 |

---

## Useful Commands Cheat Sheet

```bash
# All pods
kubectl -n portfolio get pods -o wide

# Logs (follow)
kubectl -n portfolio logs -f deployment/procurement-platform

# Shell into pod
kubectl -n portfolio exec -it deployment/integrations-hub -- /bin/sh

# Restart a deployment
kubectl -n portfolio rollout restart deployment/<name>

# Scale up
kubectl -n portfolio scale deployment/<name> --replicas=3

# Check resource usage
kubectl -n portfolio top pods

# Delete and redeploy everything
kubectl delete namespace portfolio
./scripts/deploy-all.sh
```
