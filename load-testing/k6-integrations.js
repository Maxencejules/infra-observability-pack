import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const healthLatency = new Trend("health_latency", true);
const apiLatency = new Trend("api_latency", true);

// Configuration: override with -e BASE_URL=http://...
const BASE_URL = __ENV.BASE_URL || "http://localhost:8002";

export const options = {
  stages: [
    { duration: "30s", target: 5 },   // ramp up
    { duration: "1m", target: 10 },   // steady state
    { duration: "30s", target: 20 },  // peak
    { duration: "30s", target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    errors: ["rate<0.05"],
  },
};

export default function () {
  group("Health Check", () => {
    const res = http.get(`${BASE_URL}/health`);
    healthLatency.add(res.timings.duration);
    check(res, {
      "health status 200": (r) => r.status === 200,
      "health body ok": (r) => r.json().status === "ok",
    }) || errorRate.add(1);
  });

  group("List Subscriptions", () => {
    const res = http.get(`${BASE_URL}/api/v1/subscriptions`);
    apiLatency.add(res.timings.duration);
    check(res, {
      "subscriptions status 200": (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  group("Publish Event", () => {
    const payload = JSON.stringify({
      event_type: "load_test.ping",
      payload: {
        message: "k6 load test",
        timestamp: new Date().toISOString(),
      },
    });
    const params = {
      headers: { "Content-Type": "application/json" },
    };
    const res = http.post(`${BASE_URL}/api/v1/events`, payload, params);
    apiLatency.add(res.timings.duration);
    check(res, {
      "publish event status 2xx": (r) => r.status >= 200 && r.status < 300,
    }) || errorRate.add(1);
  });

  group("Metrics Endpoint", () => {
    const res = http.get(`${BASE_URL}/metrics`);
    check(res, {
      "metrics status 200": (r) => r.status === 200,
      "metrics has prometheus data": (r) =>
        r.body.includes("http_requests_total"),
    }) || errorRate.add(1);
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: "  ", enableColors: true }),
    "results/integrations-hub-results.json": JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  return "";
}
