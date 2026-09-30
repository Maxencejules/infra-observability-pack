"""Small bounded HTTP helpers shared by native and kind wiring proofs."""
import base64
import json
import math
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def get_json(url, auth=None):
    headers = {}
    if auth:
        headers["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return json.load(response)

def wait_for(description, predicate, timeout=90):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            result = predicate()
            if result:
                return result
        except (OSError, ValueError, AssertionError) as exc:
            last = str(exc)
        time.sleep(1)
    raise AssertionError(f"Timed out waiting for {description}; last error: {last}")

def query(base, expression):
    response = get_json(base + "/api/v1/query?" + urlencode({"query": expression}))
    assert response["status"] == "success"
    assert response["data"]["resultType"] == "vector"
    return response["data"]["result"]

def up_is(base, job, value):
    samples = query(base, f'up{{job="{job}"}}')
    return samples if len(samples) == 1 and float(samples[0]["value"][1]) == value else None

def measured(base):
    samples = {}
    for metric, count in (("portfolio:http_requests:rate1m",2), ("portfolio:http_5xx:rate1m",2),
                          ("portfolio:http_latency:p95_5m",2), ("portfolio:events_published:rate1m",1)):
        rows = query(base, metric)
        if len(rows) != count or any(not math.isfinite(float(r["value"][1])) for r in rows):
            return None
        if metric in {"portfolio:http_requests:rate1m", "portfolio:events_published:rate1m"} and any(float(r["value"][1]) <= 0 for r in rows):
            return None
        samples[metric] = rows
    # Fixture has no worker: never manufacture webhook delivery success.
    assert not query(base, "portfolio:webhook_attempts:rate1m")
    assert not query(base, "portfolio:webhook_latency:p95_5m")
    return samples
