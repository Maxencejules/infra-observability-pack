import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const healthLatency = new Trend("health_latency", true);
const graphqlLatency = new Trend("graphql_latency", true);

// Configuration: override with -e BASE_URL=http://...
const BASE_URL = __ENV.BASE_URL || "http://localhost:8001";

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

  group("GraphQL - Introspection", () => {
    const payload = JSON.stringify({
      query: `{ __schema { queryType { name } } }`,
    });
    const params = {
      headers: { "Content-Type": "application/json" },
    };
    const res = http.post(`${BASE_URL}/graphql`, payload, params);
    graphqlLatency.add(res.timings.duration);
    check(res, {
      "graphql status 200": (r) => r.status === 200,
      "graphql has data": (r) => r.json().data !== undefined,
    }) || errorRate.add(1);
  });

  group("GraphQL - List Purchase Requests", () => {
    const payload = JSON.stringify({
      query: `
        query {
          purchaseRequests(limit: 10, offset: 0) {
            id
            title
            status
            amount
          }
        }
      `,
    });
    const params = {
      headers: { "Content-Type": "application/json" },
    };
    const res = http.post(`${BASE_URL}/graphql`, payload, params);
    graphqlLatency.add(res.timings.duration);
    check(res, {
      "list PRs status 200": (r) => r.status === 200,
    }) || errorRate.add(1);
  });

  group("Metrics Endpoint", () => {
    const res = http.get(`${BASE_URL}/metrics`);
    check(res, {
      "metrics status 200": (r) => r.status === 200,
      "metrics has content": (r) => r.body.length > 0,
    }) || errorRate.add(1);
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: "  ", enableColors: true }),
    "results/procurement-platform-results.json": JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  // k6 built-in text summary
  return "";
}
