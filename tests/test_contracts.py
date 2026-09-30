import copy
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ci.validate_manifests import load_yaml, validate
from ci.lint_yaml import problems
from demo.service import State, make_server

class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = load_yaml((ROOT / ".local/rendered.yaml").read_text(encoding="utf-8-sig"))

    def edited(self, kind, name):
        docs = copy.deepcopy(self.documents)
        target = next(o for o in docs if o["kind"] == kind and
                      (o["metadata"]["name"] == name or o["metadata"]["name"].startswith(name + "-")))
        return docs, target

    def test_rendered_wiring(self):
        result = validate(self.documents)
        self.assertEqual(result["recording_rules"], 8)
        self.assertEqual(result["dashboard_panels"], 7)

    def test_duplicate_yaml_key_rejected(self):
        with self.assertRaises(ValueError):
            load_yaml("x: 1\nx: 2\n")

    def test_duplicate_object_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.documents + [self.documents[0]])

    def test_wrong_namespace_rejected(self):
        docs, obj = self.edited("Service", "grafana")
        obj["metadata"]["namespace"] = "default"
        with self.assertRaisesRegex(AssertionError, "namespace"):
            validate(docs)

    def test_service_selector_mismatch_rejected(self):
        docs, obj = self.edited("Service", "grafana")
        obj["spec"]["selector"]["app"] = "nothing"
        with self.assertRaisesRegex(AssertionError, "selects no workload"):
            validate(docs)

    def test_target_port_mismatch_rejected(self):
        docs, obj = self.edited("Service", "grafana")
        obj["spec"]["ports"][0]["targetPort"] = 9999
        with self.assertRaisesRegex(AssertionError, "targetPort"):
            validate(docs)

    def test_missing_secret_key_rejected(self):
        docs, obj = self.edited("Secret", "postgres-credentials")
        obj["stringData"].pop("PROCUREMENT_DATABASE_URL")
        with self.assertRaisesRegex(AssertionError, "environment key"):
            validate(docs)

    def test_missing_volume_rejected(self):
        docs, obj = self.edited("Deployment", "grafana")
        obj["spec"]["template"]["spec"]["containers"][0]["volumeMounts"][0]["name"] = "missing"
        with self.assertRaisesRegex(AssertionError, "volume"):
            validate(docs)

    def test_missing_envfrom_rejected(self):
        docs, obj = self.edited("Deployment", "procurement-platform")
        obj["spec"]["template"]["spec"]["containers"][0]["envFrom"][0]["configMapRef"]["name"] = "absent"
        with self.assertRaisesRegex(AssertionError, "envFrom"):
            validate(docs)

    def test_stale_dashboard_rejected(self):
        docs, obj = self.edited("ConfigMap", "grafana-dashboards")
        d = json.loads(obj["data"]["portfolio-overview.json"])
        d["panels"][0]["datasource"]["uid"] = "wrong"
        obj["data"]["portfolio-overview.json"] = json.dumps(d)
        with self.assertRaisesRegex(AssertionError, "Stale dashboard"):
            validate(docs)

    def test_datasource_uid_rejected(self):
        docs, obj = self.edited("ConfigMap", "grafana-datasources")
        obj["data"]["datasources.yaml"] = obj["data"]["datasources.yaml"].replace("portfolio-prometheus", "other")
        with self.assertRaisesRegex(AssertionError, "Datasource"):
            validate(docs)

    def test_yaml_lint_detects_duplicate_error(self):
        path = ROOT / ".local/negative-lint.yaml"
        path.write_text("x: 1\nx: 2\n", encoding="utf-8")
        self.assertTrue(any(p.level == "error" for p in problems(path)))

class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.state = State("integrations-hub")
        self.server = make_server(self.state)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def request(self, path, data=None):
        request = Request(self.base + path, data=data, headers={"Content-Type":"application/json"})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as response:
            return response.code, response.read().decode()
        with response:
            return response.status, response.read().decode()

    def test_unknown_routes_have_bounded_label(self):
        for path in ("/private/customer1", "/private/customer2"):
            self.assertEqual(self.request(path)[0], 404)
        text = self.request("/metrics")[1]
        self.assertIn('path="unmatched"', text)
        self.assertNotIn("customer1", text)

    def test_scrapes_do_not_inflate_http_counters(self):
        self.request("/health")
        first = self.request("/metrics")[1]
        second = self.request("/metrics")[1]
        self.assertEqual(first, second)

    def test_invalid_json_returns_400_without_accepted_event(self):
        self.assertEqual(self.request("/api/v1/events", b"{")[0], 400)
        self.assertEqual(self.state.events, 0)

    def test_valid_event_receipt_and_cumulative_histogram(self):
        status, body = self.request("/api/v1/events", b'{"event_type":"request_submitted","payload":{"id":1}}')
        self.assertEqual(status, 201)
        receipt = json.loads(body)
        self.assertEqual(json.loads(receipt["payload"]), {"id":1})
        text = self.request("/metrics")[1]
        self.assertIn('events_published_total{event_type="request_submitted"} 1', text)
        buckets = [float(line.rsplit(" ",1)[1]) for line in text.splitlines() if line.startswith("http_request_duration_seconds_bucket")]
        self.assertEqual(buckets, sorted(buckets))
        self.assertEqual(buckets[-1], 1)

    def test_untrusted_url_never_becomes_label(self):
        self.request("/api/v1/subscriptions?email=secret")
        self.assertNotIn("secret", self.request("/metrics")[1])

    def test_parallel_observations_preserve_all_counts(self):
        def worker():
            for _ in range(100):
                self.state.observe("GET", "/health", 200, 0.02)
        workers = [threading.Thread(target=worker) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
        self.assertEqual(self.state.requests[("GET", "/health", 200)], 800)
        self.assertEqual(self.state.buckets["+Inf"], 800)

    def test_graphql_nonstring_query_is_rejected(self):
        self.state.service = "procurement-platform"
        self.assertEqual(self.request("/graphql", b'{"query":123}')[0], 400)

if __name__ == "__main__":
    unittest.main()
