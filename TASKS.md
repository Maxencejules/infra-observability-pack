# Tasks

## 1. Kubernetes Manifests
- [x] Namespace definition
- [x] PostgreSQL StatefulSet (shared instance, separate databases)
- [x] procurement-platform Deployment + Service + ConfigMap + Secret
- [x] integrations-hub Deployment + Service + ConfigMap + Secret
- [x] Port-forward instructions in README

## 2. Observability
- [x] Prometheus ConfigMap with scrape targets
- [x] Prometheus Deployment + Service
- [x] Grafana Deployment + Service with datasource provisioning
- [x] Grafana dashboard JSON (request rate, error rate, latency, queue depth)
- [x] RUNBOOK.md with common debugging procedures

## 3. Load Testing
- [x] k6 script for procurement-platform endpoints
- [x] k6 script for integrations-hub endpoints
- [x] Runner script
- [x] PERF_REPORT.md template with example results

## 4. CI
- [x] YAML lint script
- [x] Manifest validation script
- [x] Smoke test script
- [x] GitHub Actions workflow

## 5. Documentation
- [x] README.md with full setup instructions
- [x] RUNBOOK.md for incident response
- [x] PERF_REPORT.md template

## 6. App Enhancement
- [x] Add Prometheus metrics to procurement_platform backend
