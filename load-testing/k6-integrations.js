import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';
import { baseUrl, jsonBody, hasMetrics, profileOptions } from './contracts.mjs';

const failures = new Rate('request_errors');
const evaluated = new Counter('evaluated_requests');
const BASE_URL = baseUrl(__ENV.BASE_URL || 'http://127.0.0.1:8002');
export const options = profileOptions(__ENV);

function observe(response, name, valid) {
  const passed = check(response, { [name]: () => Boolean(valid) });
  failures.add(!passed);
  evaluated.add(1);
}

export default function () {
  let response = http.get(`${BASE_URL}/health`, { timeout: '5s', tags: { name: 'health' } });
  observe(response, 'health JSON/status', response.status === 200 && jsonBody(response)?.status === 'ok');
  response = http.get(`${BASE_URL}/api/v1/subscriptions`, { timeout: '5s', tags: { name: 'subscriptions' } });
  observe(response, 'subscriptions array/status', response.status === 200 && Array.isArray(jsonBody(response)));
  response = http.post(`${BASE_URL}/api/v1/events`, JSON.stringify({ event_type: 'request_submitted', payload: { title: 'local k6 smoke fixture' } }),
    { timeout: '5s', headers: { 'Content-Type': 'application/json' }, tags: { name: 'publish-event' } });
  const event = jsonBody(response);
  observe(response, 'event accepted with valid receipt', response.status === 201 &&
    /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(event?.id || '') &&
    event.event_type === 'request_submitted' && typeof event.payload === 'string' && Number.isFinite(Date.parse(event.created_at)));
  response = http.get(`${BASE_URL}/metrics`, { timeout: '5s', tags: { name: 'metrics' } });
  // Integrations exports accepted-event counters; its historical HTTP counter
  // is not populated and it has no HTTP duration histogram.
  observe(response, 'event counter exposition', response.status === 200 && hasMetrics(response.body, 'events_published_total'));
  if (__ENV.PROFILE === 'load') sleep(1);
}
