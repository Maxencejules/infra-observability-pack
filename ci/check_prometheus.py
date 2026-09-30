"""Real Prometheus + k6 on loopback; synthetic wiring, not app capacity."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.service import State, make_server
from ci.monitoring import get_json, wait_for, up_is, measured

def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]

def start_fixture(name, port=0):
    server = make_server(State(name), port=port)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    return server, worker

def stop_fixture(item):
    server, worker = item
    server.shutdown()
    server.server_close()
    worker.join(5)

def run(prometheus, k6, output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    prometheus_version = subprocess.check_output([prometheus,"--version"], stderr=subprocess.STDOUT,text=True).strip()
    k6_version = subprocess.check_output([k6,"version"], text=True).strip()
    storage = tempfile.TemporaryDirectory(prefix="tsdb-", dir=output)
    fixtures = {job:start_fixture(job) for job in ("procurement-platform", "integrations-hub")}
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    config = yaml.safe_load((ROOT / "observability/prometheus/prometheus.yml").read_text())
    config["global"].update(scrape_interval="2s", evaluation_interval="2s")
    config["rule_files"] = [str(ROOT / "observability/prometheus/rules.yml").replace("\\","/")]
    for job in config["scrape_configs"]:
        target_port = port if job["job_name"] == "prometheus" else fixtures[job["job_name"]][0].server_port
        job["static_configs"][0]["targets"] = [f"127.0.0.1:{target_port}"]
    config_file = output / "prometheus.yml"
    config_file.write_text(yaml.safe_dump(config), encoding="utf-8", newline="\n")
    empty_config = output / "k6-empty.json"
    empty_config.write_text("{}\n", encoding="utf-8")
    process = None
    proof = {"mode":"synthetic-native-wiring", "started_at":datetime.now(timezone.utc).isoformat(),
             "platform":platform.platform(), "python_version":platform.python_version(),
             "configuration_note":"Loopback targets and two-second scrape interval; canonical rule group uses ten seconds",
             "source_files_sha256":{str(path.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(path.read_bytes()).hexdigest()
                                    for path in [ROOT/"demo/service.py", ROOT/"observability/prometheus/rules.yml",
                                                 ROOT/"load-testing/contracts.mjs", ROOT/"load-testing/k6-procurement.js", ROOT/"load-testing/k6-integrations.js"]},
             "prometheus_version":prometheus_version,
             "k6_version":k6_version, "checks":[]}
    try:
        for server, _ in fixtures.values():
            get_json(f"http://127.0.0.1:{server.server_port}/health")
        with (output/"prometheus.log").open("w",encoding="utf-8") as log:
            process = subprocess.Popen([prometheus, f"--config.file={config_file}", f"--storage.tsdb.path={storage.name}",
                                        f"--web.listen-address=127.0.0.1:{port}", "--storage.tsdb.retention.time=1h"], stdout=log, stderr=log)
        for job in fixtures:
            wait_for(job+" scrape up", lambda j=job: up_is(base,j,1))
        time.sleep(3)  # Two scrape samples before traffic: zero counter baseline.
        for job, (server, _) in fixtures.items():
            script = "k6-procurement.js" if job == "procurement-platform" else "k6-integrations.js"
            command = [k6,"--config",str(empty_config),"run","--quiet","--no-usage-report","--include-system-env-vars=false",
                       "--summary-mode","disabled","--out",f"json={output / (job+'.jsonl')}",
                       "-e",f"BASE_URL=http://127.0.0.1:{server.server_port}","-e","PROFILE=smoke","-e","ITERATIONS=10",str(ROOT/"load-testing"/script)]
            result = subprocess.run(command, capture_output=True,text=True,timeout=90,
                                    env={k:v for k,v in os.environ.items() if not k.upper().startswith("K6_")})
            (output/(job+".log")).write_text(result.stdout+result.stderr,encoding="utf-8",newline="\n")
            assert result.returncode == 0, result.stderr
            from ci.check_k6 import read_points
            points = read_points(output / (job+'.jsonl'))
            expected = 30 if job == "procurement-platform" else 40
            assert len(points["request_errors"]) == expected and sum(points["request_errors"]) == 0
            proof.setdefault("k6_requests", {})[job] = expected
        proof["measurements"] = wait_for("positive rates and finite histograms", lambda: measured(base))
        proof["checks"].append("real k6 traffic scraped and recorded; absent worker metrics remain absent")
        job = "procurement-platform"
        restart_port = fixtures[job][0].server_port
        stop_fixture(fixtures.pop(job))
        wait_for("stopped target up=0", lambda: up_is(base,job,0))
        assert up_is(base,"integrations-hub",1), "Unrelated target went down"
        proof["checks"].append("one stopped target up=0 while the other stayed up=1")
        fixtures[job] = start_fixture(job, restart_port)
        wait_for("restarted target up=1", lambda: up_is(base,job,1))
        proof["checks"].append("restarted target up=1")
        proof["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output/"proof.json").write_text(json.dumps(proof,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
        print(json.dumps(proof,indent=2))
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(10)
        for fixture in fixtures.values():
            stop_fixture(fixture)
        storage.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus",required=True)
    parser.add_argument("--k6",required=True)
    parser.add_argument("--output",type=Path,default=ROOT/".local/prometheus-proof")
    args = parser.parse_args()
    run(args.prometheus,args.k6,args.output)
