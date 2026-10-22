export const securityHeaders = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'same-origin',
  'Cache-Control': 'no-store',
};

export function backendOrigin(value, allowHttp = false) {
  if (!value) throw new Error('Set BACKEND_ORIGIN to the deployed HTTPS backend URL.');
  const url = new URL(value);
  if (url.protocol !== 'https:' && !(allowHttp && url.protocol === 'http:')) {
    throw new Error('BACKEND_ORIGIN must use HTTPS (the local development proxy also permits HTTP).');
  }
  if (url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('BACKEND_ORIGIN must be an origin only, without credentials, path, query or fragment.');
  }
  if (url.hostname.endsWith('.example.com') || url.hostname === 'example.com') {
    throw new Error('Replace the example BACKEND_ORIGIN with your real backend URL.');
  }
  return url.origin;
}

export function createDeploymentConfig(value) {
  const origin = backendOrigin(value);
  return {
    framework: null,
    buildCommand: 'node check.mjs',
    installCommand: '',
    outputDirectory: 'public',
    rewrites: [{source: '/api/v1/:path*', destination: `${origin}/api/v1/:path*`}],
    headers: [{source: '/(.*)', headers: Object.entries(securityHeaders).map(([key, value]) => ({key, value}))}],
  };
}
