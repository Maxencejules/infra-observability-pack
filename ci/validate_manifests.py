"""Offline structural wiring checks, not Kubernetes API-schema validation."""
import argparse
import json
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

class StrictLoader(yaml.SafeLoader):
    pass

def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping

StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def load_yaml(text):
    return list(yaml.load_all(text, Loader=StrictLoader))

def validate(documents):
    objects = {}
    for obj in documents:
        if not isinstance(obj, dict) or not obj.get("apiVersion") or not obj.get("kind"):
            raise ValueError("Every rendered document must be a Kubernetes object")
        meta = obj["metadata"]
        key = (obj["kind"], meta.get("namespace", ""), meta["name"])
        if key in objects:
            raise ValueError(f"Duplicate object: {key}")
        objects[key] = obj
    assert ("Namespace", "", "portfolio") in objects, "Missing portfolio namespace"
    for (kind, namespace, name), obj in objects.items():
        assert kind == "Namespace" or namespace == "portfolio", f"Unexpected namespace for {name}"
    pods = [o for k,o in objects.items() if k[0] in {"Deployment", "StatefulSet"}]
    for obj in pods:
        template = obj["spec"]["template"]
        labels = template["metadata"]["labels"]
        selector = obj["spec"]["selector"]["matchLabels"]
        assert all(labels.get(k) == v for k,v in selector.items()), "Controller selector mismatch"
        spec = template["spec"]
        volumes = {v["name"]: v for v in spec.get("volumes", [])}
        for volume in volumes.values():
            for kind, field in (("ConfigMap", "configMap"), ("Secret", "secret")):
                if field in volume:
                    ref = volume[field]
                    target = objects[(kind, "portfolio", ref.get("name", ref.get("secretName")))]
                    for item in ref.get("items", []):
                        assert item["key"] in target.get("data", target.get("stringData", {})), "Missing volume key"
        for container in spec["containers"] + spec.get("initContainers", []):
            for env_from in container.get("envFrom", []):
                for kind, field in (("ConfigMap", "configMapRef"), ("Secret", "secretRef")):
                    if field in env_from:
                        assert (kind, "portfolio", env_from[field]["name"]) in objects, "Missing envFrom object"
            for mount in container.get("volumeMounts", []):
                # StatefulSet claim templates are also valid volume sources.
                claims = {c["metadata"]["name"] for c in obj["spec"].get("volumeClaimTemplates", [])}
                assert mount["name"] in volumes or mount["name"] in claims, "Missing mounted volume"
            for env in container.get("env", []):
                for kind, field in (("ConfigMap", "configMapKeyRef"), ("Secret", "secretKeyRef")):
                    ref = env.get("valueFrom", {}).get(field)
                    if ref:
                        target = objects[(kind, "portfolio", ref["name"])]
                        assert ref["key"] in target.get("data", target.get("stringData", {})), "Missing environment key"
    for (kind, namespace, name), obj in objects.items():
        if kind != "Service":
            continue
        selector = obj["spec"].get("selector", {})
        selected = [p for p in pods if selector and all(p["spec"]["template"]["metadata"]["labels"].get(k) == v for k,v in selector.items())]
        assert selected, f"Service {name} selects no workload"
        ports = [port for pod in selected for c in pod["spec"]["template"]["spec"]["containers"] for port in c.get("ports", [])]
        for port in obj["spec"]["ports"]:
            target = port.get("targetPort", port["port"])
            assert any(target in {p["containerPort"], p.get("name")} for p in ports), f"Service {name} targetPort mismatch"
    def generated_config(name):
        matches = [o for (kind, ns, obj_name), o in objects.items()
                   if kind == "ConfigMap" and ns == "portfolio" and obj_name.startswith(name + "-")]
        assert len(matches) == 1, f"Expected one generated {name}"
        return matches[0]["data"]
    prom_data = generated_config("prometheus-config")
    for file in ("prometheus.yml", "rules.yml"):
        assert prom_data[file].rstrip() == (ROOT / "observability/prometheus" / file).read_text(encoding="utf-8").rstrip(), f"Stale generated {file}"
    rules = load_yaml(prom_data["rules.yml"])[0]
    records = {r["record"] for g in rules["groups"] for r in g["rules"]}
    dashboard_text = generated_config("grafana-dashboards")["portfolio-overview.json"]
    assert json.loads(dashboard_text) == json.loads((ROOT / "observability/grafana/dashboard.json").read_text()), "Stale dashboard"
    dashboard = json.loads(dashboard_text)
    ds = objects[("ConfigMap", "portfolio", "grafana-datasources")]["data"]["datasources.yaml"]
    datasource = load_yaml(ds)[0]["datasources"][0]
    assert datasource["uid"] == "portfolio-prometheus" and datasource["url"] == "http://prometheus:9090", "Datasource wiring mismatch"
    used = set()
    for panel in dashboard["panels"]:
        assert panel["datasource"]["uid"] == datasource["uid"], "Dashboard datasource mismatch"
        assert "queue" not in panel["title"].lower(), "No measured queue gauge exists"
        for target in panel["targets"]:
            expr = target["expr"]
            if expr.startswith("up{"):
                continue
            record = re.match(r"([a-zA-Z_:][a-zA-Z0-9_:]*)", expr).group(1)
            assert record in records, f"Untested dashboard recording rule: {record}"
            used.add(record)
    assert used == records, "Unused or missing dashboard recording rules"
    config = load_yaml(prom_data["prometheus.yml"])[0]
    for job in config["scrape_configs"]:
        for group in job["static_configs"]:
            for target in group["targets"]:
                if target == "localhost:9090":
                    continue
                name, port = target.split(":")
                service = objects[("Service", "portfolio", name)]
                assert int(port) in {p["port"] for p in service["spec"]["ports"]}, "Scrape target port mismatch"
    return {"objects": len(objects), "recording_rules": len(records), "dashboard_panels": len(dashboard["panels"])}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rendered", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(load_yaml(args.rendered.read_text(encoding="utf-8-sig"))), indent=2))
