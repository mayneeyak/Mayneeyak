// Pact Escrow server. No dependencies: run with `node server.js`.

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Store } from './lib/store.js';
import { SandboxProvider } from './lib/payments.js';
import { EscrowService, HttpError } from './lib/escrow.js';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC = path.join(ROOT, 'public');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml' };
const HEADERS = {
  'Content-Security-Policy': "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'Cache-Control': 'no-store',
};

export function createApp({ dataFile, provider = new SandboxProvider(), feeBps = 0, retentionDays = 30, now } = {}) {
  const service = new EscrowService({ store: new Store(dataFile), provider, feeBps, retentionDays, now });

  const routes = [
    ['POST', /^\/api\/escrows$/, (_m, b) => service.create(b)],
    ['POST', /^\/api\/escrows\/([\w-]+)\/preview$/, (m, b, ctx) => service.preview(m[1], b.inviteCode, ctx.ip)],
    ['POST', /^\/api\/escrows\/([\w-]+)\/join$/, (m, b, ctx) => service.join(m[1], b, ctx.ip)],
    ['POST', /^\/api\/escrows\/([\w-]+)\/unlock$/, (m, b, ctx) => service.unlock(m[1], b.passphrase, ctx.ip)],
    ['GET', /^\/api\/escrow$/, (_m, _b, ctx) => service.view(ctx.token)],
    ['POST', /^\/api\/escrow\/deposit$/, (_m, _b, ctx) => service.deposit(ctx.token)],
    ['POST', /^\/api\/escrow\/report$/, (_m, b, ctx) => service.report(ctx.token, b.outcomeId)],
    ['POST', /^\/api\/escrow\/cancel$/, (_m, _b, ctx) => service.cancel(ctx.token)],
    ['POST', /^\/api\/escrow\/lock$/, (_m, _b, ctx) => (service.lock(ctx.token), { ok: true })],
  ];

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://x');
    try {
      if (url.pathname.startsWith('/api/')) {
        const route = routes.find(([m, re]) => m === req.method && re.test(url.pathname));
        if (!route) throw new HttpError(404, 'Not found');
        if (req.method === 'POST' && !String(req.headers['content-type']).startsWith('application/json')) throw new HttpError(415, 'Send JSON');
        const body = req.method === 'POST' ? await readJson(req) : {};
        const auth = String(req.headers.authorization ?? '');
        const ctx = { ip: req.socket.remoteAddress ?? '', token: auth.startsWith('Bearer ') ? auth.slice(7) : null };
        const result = await route[2](url.pathname.match(route[1]), body, ctx);
        return send(res, 200, result);
      }
      return serveStatic(url.pathname, res);
    } catch (err) {
      const status = err.status ?? 500;
      if (status === 500) console.error(err);
      return send(res, status, { error: status === 500 ? 'Something went wrong' : err.message });
    }
  });

  const sweeper = setInterval(() => service.purge(), 60 * 60 * 1000);
  sweeper.unref();
  server.on('close', () => clearInterval(sweeper));
  return { server, service };
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > 64 * 1024) { reject(new HttpError(413, 'Request too large')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      try {
        const v = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
        resolve(v && typeof v === 'object' ? v : {});
      } catch { reject(new HttpError(400, 'Invalid JSON')); }
    });
    req.on('error', reject);
  });
}

function send(res, status, data) {
  res.writeHead(status, { ...HEADERS, 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function serveStatic(pathname, res) {
  const rel = pathname === '/' ? 'index.html' : decodeURIComponent(pathname).replace(/^\/+/, '');
  const file = path.join(PUBLIC, rel);
  if (!file.startsWith(PUBLIC + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404, HEADERS);
    return res.end('Not found');
  }
  res.writeHead(200, { ...HEADERS, 'Content-Type': TYPES[path.extname(file)] ?? 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT ?? 3000);
  const { server } = createApp({
    dataFile: process.env.DATA_FILE ?? path.join(ROOT, 'data', 'escrows.json'),
    feeBps: Number(process.env.PLATFORM_FEE_BPS ?? 0),
    retentionDays: Number(process.env.RETENTION_DAYS ?? 30),
  });
  server.listen(port, () => console.log(`Pact Escrow running at http://localhost:${port} (sandbox payments)`));
}
