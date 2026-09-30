"""Semantic loopback smoke: API responses, scrapes, provisioned Grafana datasource."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ci.monitoring import get_json, wait_for, up_is

def loopback(url):
    parts = urlsplit(url)
    if parts.scheme not in {"http","https"} or parts.hostname not in {"localhost","127.0.0.1","::1"} or parts.username or parts.password or parts.path not in {"","/"} or parts.query or parts.fragment:
        raise ValueError("Only loopback base URLs without credentials are allowed")
    return url.rstrip("/")

def check(procurement, integrations, prometheus, grafana):
    for base in (procurement,integrations):
        wait_for(base+" health", lambda b=base: get_json(b+"/health").get("status") == "ok")
    for job in ("procurement-platform","integrations-hub","prometheus"):
        wait_for(job+" scrape up",lambda j=job: up_is(prometheus,j,1))
    wait_for("Grafana health",lambda: get_json(grafana+"/api/health").get("database") == "ok")
    ds = wait_for("provisioned datasource",lambda: get_json(grafana+"/api/datasources/uid/portfolio-prometheus",auth="admin:admin"))
    assert ds["uid"] == "portfolio-prometheus" and ds["url"] == "http://prometheus:9090"
    # Grafana 13's resource API returns the provisioned dashboard under spec.
    dashboard = wait_for("provisioned dashboard",lambda: get_json(grafana+"/apis/dashboard.grafana.app/v1/namespaces/default/dashboards/portfolio-overview",auth="admin:admin"))
    spec = dashboard["spec"]
    assert spec["title"] == "Portfolio Overview" and len(spec["panels"]) == 7
    assert all(panel["datasource"]["uid"] == ds["uid"] for panel in spec["panels"])
    proxy = get_json(grafana+"/api/datasources/proxy/uid/portfolio-prometheus/api/v1/query?query=up",auth="admin:admin")
    assert proxy["status"] == "success"
    assert {r["metric"]["job"] for r in proxy["data"]["result"] if float(r["value"][1]) == 1} == {"procurement-platform","integrations-hub","prometheus"}
    return {"scrapes":3,"provisioned_panels":7,"datasource_proxy":"success"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name,port in (("procurement",8001),("integrations",8002),("prometheus",9090),("grafana",3000)):
        parser.add_argument("--"+name,type=loopback,default=f"http://127.0.0.1:{port}")
    args = parser.parse_args()
    print(json.dumps(check(**vars(args)),indent=2))
