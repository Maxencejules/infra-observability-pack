import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';
import { baseUrl, jsonBody, graphqlData, hasMetrics, profileOptions } from './contracts.mjs';

const failures = new Rate('request_errors');
const evaluated = new Counter('evaluated_requests');
const BASE_URL = baseUrl(__ENV.BASE_URL || 'http://127.0.0.1:8001');
const TOKEN = __ENV.PROCUREMENT_TOKEN || '';
export const options = profileOptions(__ENV);

function observe(response, name, valid) {
  const passed = check(response, { [name]: () => Boolean(valid) });
  // One observation for EVERY evaluated request, including successes.
  failures.add(!passed);
  evaluated.add(1);
}

export default function () {
  let response = http.get(`${BASE_URL}/health`, { timeout: '5s', tags: { name: 'health' } });
  observe(response, 'health JSON/status', response.status === 200 && jsonBody(response)?.status === 'ok');
  const params = { timeout: '5s', headers: { 'Content-Type': 'application/json' }, tags: { name: 'graphql-introspection' } };
  response = http.post(`${BASE_URL}/graphql`, JSON.stringify({ query: '{ __schema { queryType { name } } }' }), params);
  const schema = graphqlData(jsonBody(response), '__schema');
  observe(response, 'GraphQL introspection without errors', response.status === 200 && typeof schema?.queryType?.name === 'string' && schema.queryType.name.length > 0);
  if (TOKEN) {
    response = http.post(`${BASE_URL}/graphql`, JSON.stringify({ query: '{ purchaseRequests(page: 1, pageSize: 10) { items { id title status amount } total } }' }),
      { ...params, headers: { ...params.headers, Authorization: `Bearer ${TOKEN}` }, tags: { name: 'graphql-purchase-requests' } });
    const page = graphqlData(jsonBody(response), 'purchaseRequests');
    observe(response, 'authenticated purchaseRequests page without errors', response.status === 200 && Array.isArray(page?.items) && Number.isInteger(page.total) && page.total >= 0);
  }
  response = http.get(`${BASE_URL}/metrics`, { timeout: '5s', tags: { name: 'metrics' } });
  observe(response, 'HTTP counter exposition', response.status === 200 && hasMetrics(response.body, 'http_requests_total'));
  if (__ENV.PROFILE === 'load') sleep(1);
}
