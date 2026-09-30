# Local monitoring runbook

Use the project kubeconfig/context explicitly. These commands operate on the disposable local lab:

```sh
kubectl --kubeconfig .local/kubeconfig --context kind-portfolio-observability -n portfolio get pods
kubectl --kubeconfig .local/kubeconfig --context kind-portfolio-observability -n portfolio get events --sort-by=.lastTimestamp
```

If you chose another `CLUSTER_NAME`/`KUBECONFIG_PATH`, substitute both deliberately. The automatic proof uses its own `kind-portfolio-observability-proof` context and `.local/kind-proof/kubeconfig`.

## Missing metrics

1. Check the API health response separately from Prometheus `up`. `up=1` describes a successful scrape, not database or business health.
2. In Prometheus Targets, inspect the target URL, last scrape and last error. A DNS/connection/parse failure makes `up=0`; absent job configuration produces no `up` series.
3. Read the local metrics endpoint. Verify the exact metric family, units and labels against `observability/prometheus/rules.yml`. An app missing the HTTP histogram cannot supply an HTTP p95.
4. Generate smoke traffic and wait at least two scrapes plus a recording-rule evaluation. An idle counter can have zero rate; a histogram with no observations may have an undefined quantile.
5. Check Prometheus logs and `promtool check/test rules` before changing a dashboard query.

```sh
kubectl --kubeconfig .local/kubeconfig --context kind-portfolio-observability -n portfolio logs deployment/prometheus
curl --fail http://127.0.0.1:9090/api/v1/targets
```

The one-minute counter window and five-minute histogram window can retain past activity after a target goes down. Use `up` alongside rate panels; an old rate is not proof of current health. Counter resets are handled by `rate` before aggregation. Histogram quantiles are interpolated estimates, not exact k6 client latency percentiles.

## Grafana shows no data

Run `bash ci/smoke-test.sh` with forwarding active. It checks the provisioned datasource UID, dashboard panels and Grafana's datasource proxy, so a reachable Grafana login page alone cannot pass. The canonical UID is `portfolio-prometheus`; queries reference tested recording rules. A blank worker panel is expected in synthetic mode.

Monitoring ConfigMap changes are content-hashed by Kustomize and cause monitoring deployments to roll. The API smoke uses Grafana 13's dashboard resource API; the documented legacy datasource/proxy endpoints remain supported in that pinned version. This repository has not visually certified the dashboard.

## k6 failure

Inspect `.local/load-test/procurement.log`, `integrations.log` and their raw JSON points. Separate transport failures from `request_errors`: HTTP-200 GraphQL errors and malformed success receipts fail semantic checks even when `http_req_failed` is zero.

Smoke performs three public procurement requests, four when `PROCUREMENT_TOKEN` is supplied, and four integrations requests per iteration. Only exact loopback origins are allowed. A real integrations application may deliver webhooks after the POST, so use disposable local data/configuration. Do not include tokens in shared logs or reports.

## Pod failure

```sh
kubectl --kubeconfig .local/kubeconfig --context kind-portfolio-observability -n portfolio describe pod POD_NAME
kubectl --kubeconfig .local/kubeconfig --context kind-portfolio-observability -n portfolio logs deployment/grafana
kubectl --kubeconfig .local/kubeconfig --context kind-portfolio-observability -n portfolio logs statefulset/postgres
```

Check image loading, readiness/liveness failures, resource limits and PostgreSQL initialization. Fixture apps wait for PostgreSQL's port but do not use SQL; fixture success does not validate schemas, migrations or query health. Avoid dumping Secret objects into diagnostic artifacts. If optional app configuration or secrets change, explicitly roll those application deployments after review.

## Recovery and data boundaries

Restarting a local monitoring pod can discard Prometheus/Grafana local state. PostgreSQL's local PVC survives a pod restart, but cluster deletion removes the entire lab's data. No backup/restore workflow is implemented or validated.

Stop only this script's forwards with Ctrl+C. Use `bash scripts/teardown.sh` to delete the named lab; it asks you to type its name. The automatic proof refuses an existing cluster and only tears down the cluster it successfully created. Never substitute a production kubeconfig into this lab.
