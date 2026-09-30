# Infra Observability Pack

A local Kubernetes lab for checking the path from HTTP traffic to Prometheus recording rules and a provisioned Grafana dashboard. The default demo uses two small, explicitly synthetic API fixtures so the experiment is reproducible without sibling repositories, API credentials or cloud infrastructure.

The pack checks telemetry wiring and diagnostic interpretation. Its fixtures do not implement procurement workflows, a durable event store, a queue or a webhook worker, and their response times are not application capacity measurements.

## What the dashboard measures

| Panel | Measurement and limits |
|---|---|
| Request rate | Instrumented HTTP counter rate per job over one minute, in requests/second. Scrapes are excluded by the fixture. |
| HTTP errors | HTTP 5xx/second. HTTP-200 GraphQL errors are detected separately by k6 semantic checks. |
| HTTP latency | p50/p95/p99 histogram estimates over five minutes, in seconds. Histogram bucket boundaries limit precision. |
| Webhook attempts | Completed attempts/second by status, including retries; the underlying counter cannot measure queue depth or unique deliveries. |
| Webhook duration | Observed attempt duration p95 from the worker histogram. |
| Scrape availability | Prometheus `up`; a successful metrics scrape does not prove API, database or business health. |
| Events accepted | Accepted event receipts/second by event type; a fixture receipt provides no durability evidence. |

Missing series remain unavailable. The fixture has no worker and therefore emits no webhook attempt/duration series. An optional real application must export the metric families used by the rules; existing `integrations_hub` instrumentation does not supply the HTTP histogram assumed by the old dashboard. There is no fabricated zero for an absent HTTP counter. A measured HTTP counter with no 5xx series yields zero HTTP errors.

The canonical configuration lives in `observability/prometheus/` and `observability/grafana/dashboard.json`. Kustomize generates content-hashed ConfigMaps and rewrites deployment references, so a monitoring configuration change triggers a rollout. There is no placeholder dashboard or second copy of the scrape configuration.

## Local cluster demo

Use Bash, Docker with a running daemon, kind 0.33.0, kubectl 1.37.x, Python 3.12 and k6 2.3.0. Allocate enough Docker resources for one kind node, PostgreSQL, two fixtures, Prometheus and Grafana; this lab has not established a minimum capacity guarantee.

Pinned monitoring versions are Prometheus LTS 3.13.3 and Grafana 13.2.3. The kind Kubernetes 1.37.0 node image is pinned by digest. Other images have explicit version tags; the cluster proof records resolved image IDs because tags can change.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-checks.txt
bash ci/lint-yaml.sh
bash ci/validate-manifests.sh

bash scripts/setup-cluster.sh
bash scripts/build-images.sh --fixtures
bash scripts/deploy-all.sh
bash scripts/port-forward.sh
```

Keep the forwarding terminal open. In another terminal:

```sh
. .venv/bin/activate
bash ci/smoke-test.sh
ITERATIONS=10 PROCUREMENT_TOKEN=synthetic-fixture-token bash load-testing/run-load-test.sh
```

Ports bind to loopback: procurement fixture 8001, integrations fixture 8002, Prometheus 9090 and Grafana 3000. Grafana's local demo login is `admin/admin`; open [the dashboard](http://127.0.0.1:3000/d/portfolio-overview). These plaintext demo credentials and ClusterIP services are for a local lab. This repository does not configure a public ingress or a production secret system.

All cluster commands explicitly use `.local/kubeconfig` and `kind-portfolio-observability`. Optional `CLUSTER_NAME` and `KUBECONFIG_PATH` overrides are deliberate operator choices; the default context is never used or changed. On Windows, use Git Bash with its own `/usr/bin` ahead of System32, activate `.venv/Scripts/activate`, and export `PYTHON="$PWD/.venv/Scripts/python.exe"`. Docker is required for the cluster portion.

Stop forwards with Ctrl+C. Delete the named local cluster and its data with:

```sh
bash scripts/teardown.sh
```

The interactive prompt requires the cluster name. PostgreSQL has a local PVC; deleting the kind cluster deletes that data. Prometheus uses `emptyDir` and Grafana has no persistent volume. A seven-day Prometheus retention setting does not survive pod replacement. No backups, high availability or alert delivery are configured.

## Optional application images

The fixture mode is the verified default. You may build caller-provided application checkouts instead:

```sh
PROCUREMENT_PATH=/absolute/path/procurement_platform \
INTEGRATIONS_PATH=/absolute/path/integrations_hub \
bash scripts/build-images.sh --apps
bash scripts/deploy-all.sh
```

The script builds their existing Dockerfiles without modifying their source, requirements or entry points. The supplied manifests retain the PostgreSQL/env contract of the original lab. Application revisions, migrations, authentication, instrumentation and outbound integration configuration remain the caller's responsibility; this upgrade did not test those external checkouts. Use only disposable local application data.

The procurement smoke covers public health, GraphQL schema introspection and metrics. Supply `PROCUREMENT_TOKEN` only if you want the additional authenticated `purchaseRequests` page query. It is passed to k6 without being written into report metadata. Integrations smoke reads subscriptions and **creates a request_submitted event**; real application webhook side effects depend on its configuration. URLs are restricted to loopback origins. The fixture never calls another service or a cloud API.

## Reproducible checks

```sh
bash ci/validate-manifests.sh
python -m unittest discover -s tests -v
node --test tests/k6-contracts.mjs
shellcheck --severity=warning scripts/*.sh ci/*.sh load-testing/*.sh
promtool check config --syntax-only observability/prometheus/prometheus.yml
promtool check rules observability/prometheus/rules.yml
promtool test rules observability/prometheus/rules.test.yml
python ci/check_k6.py --k6 k6
python ci/check_prometheus.py --prometheus prometheus --k6 k6
```

Node 24 is needed only for the dependency-free JavaScript contract tests. PyYAML/yamllint are exactly pinned in `requirements-checks.txt`. Offline manifest checks validate duplicate keys/objects, selectors, target ports, configuration references, generated content and datasource/query wiring. They are structural checks, **not Kubernetes API-schema validation**; the actual cluster deploy also performs server-side dry-run.

The native Prometheus proof starts its own loopback fixtures and a fresh temporary TSDB, runs ten smoke iterations per service, checks positive recorded rates/finite latency, stops one target and observes `up=0`, then restarts it and observes `up=1`. It retains configuration, raw k6 points, logs, versions and measured values under `.local/prometheus-proof`, and stops only the processes it started.

A complete disposable cluster proof is:

```sh
bash ci/kind-proof.sh
```

It uses a new `portfolio-observability-proof` cluster/private kubeconfig, refuses a pre-existing cluster before enabling cleanup, builds fixtures, waits for rollouts, verifies Grafana provisioning and datasource proxy queries, generates 80 semantically successful HTTP requests, and proves scrape down/recovery by scaling one fixture. It cleans up its own cluster and forwards on exit. Evidence includes source HEAD, versions, pod/node resources, resolved image IDs, raw points and logs under `.local/kind-proof`.

CI runs on master pushes and pull requests. Its checks job runs lint, adversarial structural/HTTP/JavaScript tests, promtool fixtures and real native Prometheus/k6 proofs. A dependent Ubuntu kind job exercises deployment and Grafana. Artifacts upload on failure as well as success. Linux tools are downloaded from official release assets with SHA256 verification. Remote CI results must be checked on the particular commit; workflow configuration alone is not a passing run.

## Evidence and limits

The recorded Windows run used Python 3.12.10, Node 24.12.0, Prometheus 3.13.3 and k6 2.3.0. It passed 24 Python tests, 5 JavaScript tests, shell lint, YAML lint, offline wiring validation, 14 promtool expression checks in four scenarios, seven real k6 failure/success scenarios, and the native collection/down/recovery proof. The native proof generated 30 procurement and 40 integrations requests with zero semantic failures. See [the evidence record](docs/native-proof.json) and [experiment notes](PERF_REPORT.md).

Docker was unavailable on that Windows host. The full kind/Grafana deployment is exercised by Ubuntu CI; no local cluster or visual Grafana check is claimed. Throughput, database bottlenecks, durable delivery, queue health, production sizing and linear scaling have not been measured. The old screenshot and unsupported performance numbers were removed.

## Primary references

- [Prometheus metric names and units](https://prometheus.io/docs/practices/naming/) and [histogram interpretation](https://prometheus.io/docs/practices/histograms/).
- [Prometheus rule unit tests](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/) and [Prometheus LTS downloads](https://prometheus.io/download/).
- [k6 Rate denominator](https://grafana.com/docs/k6/latest/javascript-api/k6-metrics/rate/), [checks and thresholds](https://grafana.com/docs/k6/latest/using-k6/checks/), and [raw JSON points](https://grafana.com/docs/k6/latest/results-output/real-time/json/).
- [Kustomize ConfigMap generation](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/) and [kind 0.33.0 node images](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0).
- [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/), [dashboard resource API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/dashboard/), [datasource API/proxy compatibility](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/) and [Grafana 13.2.3 release](https://github.com/grafana/grafana/releases/tag/v13.2.3).

MIT license. See [RUNBOOK.md](RUNBOOK.md) for diagnosis and [TASKS.md](TASKS.md) for remaining work.
