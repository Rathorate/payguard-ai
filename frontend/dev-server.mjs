// Local development proxy. Production uses Vercel's native external rewrite.
import http from 'node:http';
import https from 'node:https';
import { createReadStream } from 'node:fs';
import { realpath, stat } from 'node:fs/promises';
import { dirname, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pathToFileURL } from 'node:url';
import { backendOrigin, securityHeaders } from './deployment.mjs';

const publicDirectory = resolve(dirname(fileURLToPath(import.meta.url)), 'public');
const hopByHop = ['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade'];
function forwardedHeaders(headers) {
  const result = {...headers};
  const extra = String(headers.connection || '').split(',').map(x => x.trim().toLowerCase());
  for (const key of [...hopByHop, ...extra]) delete result[key];
  return result;
}

export function createFrontendServer(origin) {
  const backend = new URL(backendOrigin(origin, true));
  return http.createServer(async (request, response) => {
    response.setHeader('Cache-Control', 'no-store');
    let url;
    try { url = new URL(request.url, 'http://localhost'); }
    catch { response.writeHead(400).end('Invalid request'); return; }
    if (url.pathname === '/api/v1' || url.pathname.startsWith('/api/v1/')) {
      const headers = forwardedHeaders(request.headers);
      headers.host = backend.host;
      const upstream = (backend.protocol === 'https:' ? https : http).request({
        protocol: backend.protocol, hostname: backend.hostname, port: backend.port,
        path: url.pathname + url.search, method: request.method, headers,
      }, upstreamResponse => {
        const resultHeaders = forwardedHeaders(upstreamResponse.headers);
        resultHeaders['cache-control'] = 'no-store';
        response.writeHead(upstreamResponse.statusCode, resultHeaders);
        upstreamResponse.pipe(response);
        upstreamResponse.on('error', () => response.destroy());
      });
      upstream.setTimeout(120000, () => upstream.destroy(new Error('Backend timed out')));
      upstream.on('error', () => {
        if (response.headersSent) { response.destroy(); return; }
        response.writeHead(502, {'Content-Type': 'application/json'}).end(JSON.stringify({detail:'Backend unavailable. Start the API server and verify BACKEND_ORIGIN.'}));
      });
      request.on('aborted', () => upstream.destroy());
      response.on('close', () => { if (!response.writableFinished) upstream.destroy(); });
      request.pipe(upstream);
      return;
    }
    for (const [name, value] of Object.entries(securityHeaders)) response.setHeader(name, value);
    if (!['GET', 'HEAD'].includes(request.method)) {
      response.writeHead(405, {Allow:'GET, HEAD'}).end('Method not allowed'); return;
    }
    try {
      const path = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
      if (path.includes('\0') || path.includes('\\') || path.split('/').some(x => x.startsWith('.'))) throw new Error('Invalid path');
      const file = await realpath(resolve(publicDirectory, '.' + path));
      const root = await realpath(publicDirectory);
      if (!file.startsWith(root + sep) || !(await stat(file)).isFile()) throw new Error('Not a public asset');
      const types = {'.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.png':'image/png', '.svg':'image/svg+xml'};
      response.writeHead(200, {'Content-Type':types[extname(file)] || 'application/octet-stream'});
      if (request.method === 'HEAD') response.end();
      else createReadStream(file).on('error', () => response.destroy()).pipe(response);
    } catch { response.writeHead(404).end('Not found'); }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const port = Number(process.env.FRONTEND_PORT || 3000);
  const host = process.env.FRONTEND_HOST || '127.0.0.1';
  const server = createFrontendServer(process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000');
  server.on('error', error => { console.error(error.message); process.exitCode = 1; });
  server.listen(port, host, () => console.log(`PayGuard frontend: http://${host}:${port}`));
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close());
}
