export function baseUrl(value) {
  if (!/^https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?\/?$/.test(value)) {
    throw new Error('BASE_URL must be a loopback HTTP(S) origin without credentials, query or path');
  }
  const port = value.match(/:([0-9]+)\/?$/)?.[1];
  if (port !== undefined && (Number(port) < 1 || Number(port) > 65535)) throw new Error('Invalid TCP port');
  return value.replace(/\/$/, '');
}

export function jsonBody(response) {
  try { return JSON.parse(response.body); } catch { return null; }
}

export function graphqlData(body, field) {
  if (!body || typeof body !== 'object' || Array.isArray(body) ||
      (body.errors !== undefined && (!Array.isArray(body.errors) || body.errors.length !== 0)) ||
      !body.data || typeof body.data !== 'object' || Array.isArray(body.data)) return null;
  return body.data[field] ?? null;
}

export function hasMetrics(body, name) {
  if (typeof body !== 'string') return false;
  return body.split('\n').some(line => {
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^\n]*\})?\s+([^\s]+)(?:\s+[0-9]+)?\s*$/);
    return match?.[1] === name && Number.isFinite(Number(match[2])) && Number(match[2]) >= 0;
  });
}

export function profileOptions(env) {
  const profile = env.PROFILE || 'smoke';
  if (!['smoke', 'load'].includes(profile)) throw new Error('PROFILE must be smoke or load');
  const iterations = Number(env.ITERATIONS || 1);
  if (!Number.isInteger(iterations) || iterations < 1 || iterations > 100000) throw new Error('ITERATIONS must be an integer from 1 to 100000');
  return {
    maxRedirects: 0,
    ...(profile === 'load' ? { stages: [
      { duration: '30s', target: 5 }, { duration: '1m', target: 10 },
      { duration: '30s', target: 20 }, { duration: '30s', target: 0 },
    ] } : { vus: 1, iterations }),
    thresholds: {
      evaluated_requests: ['count>0'],
      request_errors: [profile === 'smoke' ? 'rate==0' : 'rate<0.05'],
      http_req_failed: [profile === 'smoke' ? 'rate==0' : 'rate<0.05'],
      ...(profile === 'load' ? { http_req_duration: ['p(95)<500', 'p(99)<1000'] } : {}),
    },
  };
}
