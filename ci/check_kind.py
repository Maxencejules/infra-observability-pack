"""Run only after dedicated kind fixture deployment and loopback forwarding."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ci.smoke_test import check
from ci.monitoring import wait_for, up_is, measured
from ci.check_k6 import read_points

def run():
    output = ROOT / ".local/kind-proof"
    output.mkdir(parents=True,exist_ok=True)
    cluster = os.environ.get("CLUSTER_NAME","portfolio-observability")
    kubeconfig = os.environ.get("KUBECONFIG_PATH",str(ROOT/".local/kubeconfig"))
    kube = ["kubectl","--kubeconfig",kubeconfig,"--context","kind-"+cluster,"-n","portfolio"]
    # Refuse to run on a context that isn't a running named local kind cluster.
    assert cluster in subprocess.check_output(["kind","get","clusters"],text=True).splitlines()
    proof = {"mode":"synthetic-kind-wiring","started_at":datetime.now(timezone.utc).isoformat(),
             "source_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
             "kubectl_version":json.loads(subprocess.check_output(["kubectl","version","--client","-o","json"],text=True)),
             "kind_version":subprocess.check_output(["kind","version"],text=True).strip(),
             "k6_version":subprocess.check_output(["k6","version"],text=True).strip()}
    proof["smoke"] = check("http://127.0.0.1:8001","http://127.0.0.1:8002","http://127.0.0.1:9090","http://127.0.0.1:3000")
    # Have baseline zero event counter samples before generating acceptance traffic.
    wait_for("initial metrics evaluation",lambda: up_is("http://127.0.0.1:9090","integrations-hub",1))
    subprocess.run(["bash",str(ROOT/"load-testing/run-load-test.sh")],cwd=ROOT,check=True,timeout=180,
                   env={**os.environ,"PROFILE":"smoke","ITERATIONS":"10","PROCUREMENT_TOKEN":"synthetic-fixture-token","OUTPUT_DIR":str(output/"k6")})
    proof["k6"] = []
    for service in ("procurement","integrations"):
        points = read_points(output/"k6"/(service+".jsonl"))
        failures = points["request_errors"]
        assert len(failures) == 40 and all(value == 0 for value in failures), "Expected ten four-request iterations without semantic errors"
        proof["k6"].append({"service":service,"requests":len(failures),"failures":sum(failures)})
    proof["measurements"] = wait_for("recording rule output",lambda: measured("http://127.0.0.1:9090"),timeout=120)
    subprocess.run(kube+["scale","deployment/procurement-platform","--replicas=0"],check=True)
    try:
        wait_for("scaled-down scrape up=0",lambda: up_is("http://127.0.0.1:9090","procurement-platform",0))
        assert up_is("http://127.0.0.1:9090","integrations-hub",1), "Unrelated target failed"
        proof["stopped_target_up"] = 0
    finally:
        subprocess.run(kube+["scale","deployment/procurement-platform","--replicas=1"],check=True)
    subprocess.run(kube+["rollout","status","deployment/procurement-platform","--timeout=180s"],check=True)
    wait_for("restored scrape up=1",lambda: up_is("http://127.0.0.1:9090","procurement-platform",1))
    proof["recovered_target_up"] = 1
    proof["pods"] = json.loads(subprocess.check_output(kube+["get","pods","-o","json"],text=True))
    proof["nodes"] = json.loads(subprocess.check_output(kube[:-2]+["get","nodes","-o","json"],text=True))
    proof["finished_at"] = datetime.now(timezone.utc).isoformat()
    (output/"proof.json").write_text(json.dumps(proof,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({key:value for key,value in proof.items() if key not in {"pods","nodes","measurements"}},indent=2))

if __name__ == "__main__":
    run()
