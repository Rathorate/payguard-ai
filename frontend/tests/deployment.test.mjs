import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { createFrontendServer } from '../dev-server.mjs';
import { backendOrigin, createDeploymentConfig } from '../deployment.mjs';

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return `http://127.0.0.1:${server.address().port}`;
}
async function close(server) {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}

test('deployment requires a real HTTPS origin and rewrites only API traffic', () => {
  for (const value of [undefined, 'http://remote.test', 'https://user:secret@api.test', 'https://api.test/path', 'https://api.test?key=x', 'https://api.test/#fragment', 'https://example.com']) {
    assert.throws(() => createDeploymentConfig(value));
  }
  const config = createDeploymentConfig('https://payguard-api.onrender.com/');
  assert.deepEqual(config.rewrites, [{source:'/api/v1/:path*',destination:'https://payguard-api.onrender.com/api/v1/:path*'}]);
  assert.equal(config.outputDirectory, 'public');
  assert.equal(backendOrigin('http://127.0.0.1:8000', true), 'http://127.0.0.1:8000');
});

test('frontend serves all UI assets, blocks private paths and retains CSP', async () => {
  const server = createFrontendServer('http://127.0.0.1:1');
  const base = await listen(server);
  try {
    const response = await fetch(base);
    assert.equal(response.status, 200);
    assert.match(await response.text(), /Open interactive demo/);
    assert.match(response.headers.get('content-security-policy'), /script-src 'self'/);
    for (const asset of ['app.js', 'style.css', 'base.css']) assert.equal((await fetch(base + '/static/' + asset)).status, 200);
    for (const path of ['/.env', '/app/config.py', '/%2e%2e%2f.env', '/static/%5c..%5c.env']) assert.equal((await fetch(base + path)).status, 404);
    assert.equal((await fetch(base, {method:'POST'})).status, 405);
    assert.equal((await fetch(base, {method:'HEAD'})).status, 200);
  } finally { await close(server); }
});

test('proxy preserves query, cookie, CSRF, Origin, multipart bytes and Set-Cookie', async () => {
  let received;
  const upstream = http.createServer(async (request, response) => {
    const chunks = []; for await (const chunk of request) chunks.push(chunk);
    received = {url:request.url,headers:request.headers,body:Buffer.concat(chunks)};
    response.writeHead(201, {'Content-Type':'application/json','Set-Cookie':['pg_session=test; HttpOnly; Path=/; SameSite=Strict'],'Cache-Control':'public, max-age=999'}).end('{"ok":true}');
  });
  const backend = await listen(upstream);
  const server = createFrontendServer(backend);
  const base = await listen(server);
  try {
    const payload = Buffer.from('--boundary\r\nContent-Disposition: form-data; name="file"; filename="invoice.pdf"\r\n\r\n%PDF-test\r\n--boundary--\r\n');
    const result = await fetch(base + '/api/v1/disputes/id/upload?source=pdf', {method:'POST', headers:{'Content-Type':'multipart/form-data; boundary=boundary',Cookie:'pg_session=test','X-CSRF-Token':'csrf-value',Origin:base},body:payload});
    assert.equal(result.status, 201);
    assert.deepEqual(await result.json(), {ok:true});
    assert.match(result.headers.get('set-cookie'), /HttpOnly/);
    assert.equal(result.headers.get('cache-control'), 'no-store');
    assert.equal(received.url, '/api/v1/disputes/id/upload?source=pdf');
    assert.equal(received.headers.cookie, 'pg_session=test');
    assert.equal(received.headers['x-csrf-token'], 'csrf-value');
    assert.equal(received.headers.origin, base);
    assert.deepEqual(received.body, payload);
  } finally { await close(server); await close(upstream); }
});

test('unavailable backend returns a useful uncached JSON error', async () => {
  const server = createFrontendServer('http://127.0.0.1:1');
  const base = await listen(server);
  try {
    const result = await fetch(base + '/api/v1/config');
    assert.equal(result.status, 502);
    assert.match((await result.json()).detail, /Backend unavailable/);
    assert.equal(result.headers.get('cache-control'), 'no-store');
  } finally { await close(server); }
});
