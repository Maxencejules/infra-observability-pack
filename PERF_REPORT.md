# Reproducible monitoring experiment

This report describes a telemetry-wiring experiment. The two standard-library HTTP fixtures are in memory and do not execute real procurement, SQL or webhook delivery work. Their speeds cannot justify production throughput, scaling or database bottleneck claims.

## Recorded local evidence

On Windows with Python 3.12.10, Prometheus 3.13.3 and k6 2.3.0, the native proof generated ten sequential smoke iterations per service: 30 procurement requests and 40 integrations requests, with zero semantic failures. Prometheus produced finite HTTP rates and histogram estimates, and a positive accepted-event rate. Stopping procurement changed its scrape signal to zero while integrations remained up; restarting restored procurement's scrape signal. Worker metrics remained absent.

The committed [native evidence record](docs/native-proof.json) preserves the actual query results, run time, executable versions and relevant source-file hashes. Its two-second local scrape interval differs from the cluster's ten-second interval. Timestamps, sampled rates, handler durations and operating-system scheduling vary across reruns. Fixed contract tests and analytic promtool fixtures are deterministic; runtime evidence is an observed run.

Seven additional actual k6 scenarios assert the exact error-rate denominator. HTTP-200 GraphQL errors, malformed health JSON and invalid 201 event receipts cause expected nonzero exits. Successful observations add zeros as well as failed observations adding ones.

## Profiles and evidence retention

The default `PROFILE=smoke` uses one VU and `ITERATIONS=1` (configurable integer 1–100000). Every evaluated request adds one `request_errors` Rate observation and one `evaluated_requests` Counter observation. Smoke requires semantic and transport failure rates to be zero.

`PROFILE=load` explicitly selects 30 seconds to 5 VUs, one minute to 10, 30 seconds to 20, then 30 seconds to zero: 150 seconds total, with one-second pacing per iteration. Illustrative local gates are semantic/transport failure rates below 5%, HTTP duration p95 below 500 ms and p99 below 1000 ms. These are demonstration thresholds, not an adopted service-level objective. VUs are concurrency, not a guaranteed request rate. This load profile has not been used to publish a capacity result.

```sh
PROFILE=load OUTPUT_DIR="$PWD/.local/my-load-run" bash load-testing/run-load-test.sh
```

The runner captures both services' raw NDJSON points, summaries/logs, UTC start/end, k6 version and source HEAD, and returns failure if either service fails its gates. It does not hide a first service's failure behind a later successful run. Inherited k6 configuration/output options are cleared in the child shell, an empty config is used, usage reporting is disabled, and test URLs remain loopback.

For a real-app capacity report, record the exact application revisions, datasets/database state, authentication/workload mix, resolved image digests, host/node CPU and memory, limits, tool versions, requested profile, source commit and all successful/failed runs. Add actual observation windows and raw latency/error distributions. Correlate metrics and logs before attributing a bottleneck. This repository supplies that collection path but publishes no real-app capacity estimate.

## Cluster evidence

The Ubuntu CI proof records API-server dry-run, rollout readiness, provisioned dashboard/datasource API responses, successful datasource proxy queries, 80 k6 semantic request checks, finite recording-rule values, and target down/recovery. Pod/node JSON includes runtime/resource settings and resolved image IDs. Artifacts are retained even if the proof fails. A passing native test suite does not substitute for inspecting the kind job on the same commit.
