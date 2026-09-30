# Scope and follow-up

Completed in this upgrade:

- Canonical content-hashed monitoring configuration and an explicit Grafana datasource UID.
- Numerically checked rate/reset/idle/missing/histogram rules; no counter presented as queue depth.
- Semantic k6 checks with one error-rate sample for every request and retained raw points.
- Synthetic fixtures with bounded route labels and no cloud calls.
- Dedicated kind contexts/private kubeconfigs, source-preserving optional app builds and owned-process cleanup.
- Offline adversarial tests plus native Prometheus/k6 collection/down/recovery evidence.
- A full disposable kind/Grafana API proof in Ubuntu CI, triggered on the actual master branch.

Remaining work requires a separate measured scope:

- Exercise a pinned real procurement/integrations revision and dataset, including authentication, migrations and webhook outcomes.
- Add a real queue gauge if queue depth is needed; define retry versus unique-delivery semantics before choosing alerts.
- Measure representative workloads/resources before proposing production sizing or capacity.
- Establish backups, persistence, TLS/identity, secrets, alert routing and failure recovery for any production deployment.
- Perform visual Grafana review in a running cluster; current proof checks configuration and APIs.

CI configuration does not itself prove these follow-ups or a successful remote run.
