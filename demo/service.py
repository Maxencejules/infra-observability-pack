"""A synthetic API fixture, not a portfolio application or a benchmark.

Counters describe requests this process actually serves. Route labels are bounded;
no database, authentication system, queue or webhook worker is implemented.
"""

import argparse
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socketserver
import threading
import time
from urllib.parse import urlsplit
import uuid

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)


class State:
    def __init__(self, service="procurement-platform", fault=None):
        self.service = service
        self.fault = fault
        self.lock = threading.Lock()
        self.requests = Counter()
        self.buckets = Counter()
        self.duration_sum = 0.0
        self.events = 0

    def observe(self, method, route, status, duration):
        with self.lock:
            self.requests[(method, route, status)] += 1
            self.duration_sum += duration
            for bucket in BUCKETS:
                self.buckets[bucket] += duration <= bucket
            self.buckets["+Inf"] += 1

    def metrics(self):
        with self.lock:
            lines = ["# HELP http_requests_total Fixture responses, excluding metrics scrapes.",
                     "# TYPE http_requests_total counter"]
            for (method, path, status), value in sorted(self.requests.items()):
                lines.append(f'http_requests_total{{method="{method}",path="{path}",status_code="{status}"}} {value}')
            lines.extend(["# HELP http_request_duration_seconds Fixture response duration in seconds.",
                          "# TYPE http_request_duration_seconds histogram"])
            for bucket in (*BUCKETS, "+Inf"):
                lines.append(f'http_request_duration_seconds_bucket{{le="{bucket}"}} {self.buckets[bucket]}')
            lines.extend([f"http_request_duration_seconds_count {self.buckets['+Inf']}",
                          f"http_request_duration_seconds_sum {self.duration_sum}",
                          "# HELP events_published_total Events accepted by this in-memory fixture.",
                          "# TYPE events_published_total counter",
                          f'events_published_total{{event_type="request_submitted"}} {self.events}'])
            return "\n".join(lines) + "\n"


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):
        # Avoid HTTPServer's reverse-DNS lookup even for numeric loopback.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def make_server(state, host="127.0.0.1", port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            start = time.perf_counter()
            path = urlsplit(self.path).path
            route = path if path in {"/health", "/graphql", "/metrics", "/api/v1/subscriptions", "/api/v1/events"} else "unmatched"
            status, payload = 200, None
            if self.command == "GET" and path == "/metrics":
                body = state.metrics().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.command == "GET" and path == "/health":
                payload = {"status": "ok", "mode": "synthetic-fixture"}
            elif self.command == "GET" and path == "/api/v1/subscriptions" and state.service == "integrations-hub":
                payload = []
            elif self.command == "POST":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 8192:
                        raise ValueError("invalid length")
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError("object required")
                except (ValueError, json.JSONDecodeError):
                    status, payload = 400, {"error": "invalid request"}
                else:
                    if path == "/graphql" and state.service == "procurement-platform":
                        query = data.get("query", "")
                        if not isinstance(query, str):
                            status, payload = 400, {"error": "query must be a string"}
                        elif state.fault == "graphql_error":
                            payload = {"data": None, "errors": [{"message": "synthetic failure"}]}
                        elif "__schema" in query:
                            payload = {"data": {"__schema": {"queryType": {"name": "Query"}}}}
                        elif "purchaseRequests" in query and self.headers.get("Authorization") == "Bearer synthetic-fixture-token":
                            payload = {"data": {"purchaseRequests": {"items": [], "total": 0}}}
                        else:
                            payload = {"data": None, "errors": [{"message": "unsupported or unauthenticated fixture query"}]}
                    elif path == "/api/v1/events" and state.service == "integrations-hub" and data.get("event_type") == "request_submitted" and isinstance(data.get("payload"), dict):
                        with state.lock:
                            state.events += 1
                        status = 201
                        payload = {"id": str(uuid.uuid4()), "event_type": "request_submitted", "payload": json.dumps(data["payload"]), "created_at": "2000-01-01T00:00:00Z"}
                    else:
                        status, payload = 404, {"error": "unsupported fixture route"}
            else:
                status, payload = 404, {"error": "unsupported fixture route"}
            body = json.dumps(payload).encode()
            if path == "/health" and state.fault == "bad_health_json":
                body = b"not JSON"
            if path == "/api/v1/events" and state.fault == "bad_receipt":
                body = b"{}"
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            state.observe(self.command, route, status, time.perf_counter() - start)
            self.wfile.write(body)

    return Server((host, port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--service", choices=("procurement-platform", "integrations-hub"), default=os.getenv("PORTFOLIO_SERVICE", "procurement-platform"))
    args = parser.parse_args()
    print(f"Synthetic fixture: {args.service} on {args.host}:{args.port}", flush=True)
    make_server(State(args.service), args.host, args.port).serve_forever()
