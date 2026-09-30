"""Run the real k6 executable against bounded local HTTP fixtures.

Prove rate denominators and rejection of HTTP-200 GraphQL failures, malformed
JSON and invalid accepted-event receipts. This is contract evidence, not load
capacity evidence. Raw k6 points are retained even for expected failed runs.
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.service import State, make_server  # noqa: E402


def read_points(path):
    points = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("type") == "Point":
            points.setdefault(item["metric"], []).append(item["data"]["value"])
    return points


def run_case(k6, output, name, service, fault=None, expected_errors=0, token=False):
    state = State(service, fault)
    server = make_server(state)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    raw = output.resolve() / f"{name}.jsonl"
    config = output.resolve() / "k6-empty.json"
    config.write_text("{}\n", encoding="utf-8")
    command = [k6, "--config", str(config), "run", "--quiet", "--no-usage-report", "--include-system-env-vars=false", "--summary-mode", "disabled", "--out", f"json={raw}",
               "-e", f"BASE_URL=http://127.0.0.1:{server.server_port}",
               "-e", "PROFILE=smoke", "-e", "ITERATIONS=1"]
    if token:
        command += ["-e", "PROCUREMENT_TOKEN=synthetic-fixture-token"]
    command += [str(ROOT / "load-testing" / f"k6-{service.split('-')[0]}.js")]
    # The integrations filename is shorter than its job name.
    if service == "integrations-hub":
        command[-1] = str(ROOT / "load-testing/k6-integrations.js")
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                timeout=90, env={k:v for k,v in os.environ.items() if not k.upper().startswith("K6_")})
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    (output / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    points = read_points(raw)
    errors = points.get("request_errors", [])
    expected_requests = 4 if service == "integrations-hub" or token else 3
    assert len(errors) == expected_requests, f"{name}: expected {expected_requests} denominator samples, got {errors}"
    assert Counter(errors) == Counter({0: expected_requests - expected_errors, 1: expected_errors}) - Counter({0: 0, 1: 0}), f"{name}: wrong failure observations {errors}"
    assert sum(points.get("evaluated_requests", [])) == expected_requests, f"{name}: request counter missing"
    assert (result.returncode == 0) == (expected_errors == 0), f"{name}: unexpected exit {result.returncode}\n{result.stdout}\n{result.stderr}"
    assert not points.get("errors"), f"{name}: obsolete failure-only metric remains"
    return {"case": name, "requests": expected_requests, "failures": expected_errors, "exit_code": result.returncode}


def check(k6, output):
    output.mkdir(parents=True, exist_ok=True)
    cases = [
        ("procurement-success", "procurement-platform", None, 0, False),
        ("procurement-authenticated", "procurement-platform", None, 0, True),
        ("graphql-200-errors", "procurement-platform", "graphql_error", 2, True),
        ("procurement-malformed-health", "procurement-platform", "bad_health_json", 1, False),
        ("integrations-success", "integrations-hub", None, 0, False),
        ("integrations-malformed-health", "integrations-hub", "bad_health_json", 1, False),
        ("integrations-bad-receipt", "integrations-hub", "bad_receipt", 1, False),
    ]
    results = [run_case(k6, output, *case) for case in cases]
    report = {"mode": "synthetic-fixture-contract-check", "k6_version": subprocess.check_output([k6, "version"], text=True).strip(), "cases": results}
    (output / "proof.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k6", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/k6-proof")
    args = parser.parse_args()
    check(args.k6, args.output)
