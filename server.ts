import express, { Request as ExpressRequest, Response as ExpressResponse, NextFunction } from 'express';
import path from 'path';
import { spawn } from 'child_process';
import { createServer as createViteServer } from 'vite';
import { fallbackRouter } from './server/fallbackApi';

const PORT = 3000;
const FASTAPI_PORT = process.env.API_PORT || '8001';
const FASTAPI_URL = (process.env.FASTAPI_URL || process.env.VITE_SKYOPS_API_URL || `http://127.0.0.1:${FASTAPI_PORT}`).replace(/\/$/, '');

let pythonProc: any = null;
let isShuttingDown = false;

function launchFastApi() {
  if (isShuttingDown) return;
  const env = {
    ...process.env,
    API_PORT: FASTAPI_PORT,
    DATABASE_URL: process.env.DATABASE_URL || 'sqlite:///./data/cloud_db.sqlite',
    PYTHONPATH: `${process.cwd()}:${process.env.PYTHONPATH || ''}`,
  };

  console.log(`[SkyOps UI] Launching FastAPI backend on port ${FASTAPI_PORT}...`);
  pythonProc = spawn('python3', ['-m', 'uvicorn', 'cloud.app.main:app', '--host', '127.0.0.1', '--port', FASTAPI_PORT], {
    env,
    stdio: 'inherit',
  });

  pythonProc.on('error', (err: any) => {
    console.error('[SkyOps UI] Failed to spawn FastAPI process:', err);
  });

  pythonProc.on('exit', (code: number, signal: string) => {
    console.warn(`[SkyOps UI] FastAPI process exited with code ${code}, signal ${signal}`);
    pythonProc = null;
    if (!isShuttingDown) {
      setTimeout(() => {
        console.log('[SkyOps UI] Respawning FastAPI backend...');
        launchFastApi();
      }, 1000);
    }
  });
}

function ensureFastApiBackend() {
  if (FASTAPI_URL.includes('127.0.0.1') || FASTAPI_URL.includes('localhost')) {
    if (!pythonProc) {
      launchFastApi();
    }

    process.on('exit', () => {
      isShuttingDown = true;
      if (pythonProc) pythonProc.kill();
    });
  }
}

async function waitForFastApi(maxMs = 5000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/health`);
      if (res.ok) {
        console.log('[SkyOps UI] FastAPI backend is ready and healthy.');
        return true;
      }
    } catch {
      // Waiting for FastAPI to accept connections
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  console.warn('[SkyOps UI] FastAPI backend ping timed out during server boot.');
  return false;
}

async function startServer() {
  ensureFastApiBackend();
  await waitForFastApi(5000);

  const app = express();
  app.use(express.json());

  // CORS middleware supporting credentials
  app.use((req, res, next) => {
    const origin = req.headers.origin;
    if (origin) {
      res.header('Access-Control-Allow-Origin', origin);
      res.header('Access-Control-Allow-Credentials', 'true');
    } else {
      res.header('Access-Control-Allow-Origin', '*');
    }
    res.header('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, Cookie');
    if (req.method === 'OPTIONS') {
      return res.sendStatus(200);
    }
    next();
  });

  // Proxy API & Health endpoints to canonical FastAPI + PostgreSQL backend
  const proxyPaths = ['/api', '/health', '/ready', '/docs', '/redoc', '/openapi.json'];

  app.use(proxyPaths, async (req: ExpressRequest, res: ExpressResponse, next: NextFunction) => {
    try {
      const targetUrl = `${FASTAPI_URL}${req.originalUrl}`;
      const headers: Record<string, string> = {};

      for (const [key, val] of Object.entries(req.headers)) {
        if (val && key.toLowerCase() !== 'host') {
          headers[key] = Array.isArray(val) ? val.join(', ') : val;
        }
      }

      const init: RequestInit = {
        method: req.method,
        headers,
      };

      if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(req.method) && req.body && Object.keys(req.body).length > 0) {
        init.body = JSON.stringify(req.body);
        headers['content-type'] = 'application/json';
      }

      let response: globalThis.Response | null = null;

      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          response = await fetch(targetUrl, init);
          if (response.ok || response.status < 500) break;
        } catch {
          await new Promise((r) => setTimeout(r, 150));
        }
      }

      if (!response || response.status >= 500) {
        return next();
      }

      res.status(response.status);

      response.headers.forEach((value, key) => {
        if (key.toLowerCase() !== 'transfer-encoding') {
          res.setHeader(key, value);
        }
      });

      const bodyText = await response.text();
      res.send(bodyText);
    } catch {
      return next();
    }
  });

  // Fallback API Router if proxy is unreachable or 5xx
  app.use('/api/v1', fallbackRouter);
  app.use('/api', fallbackRouter);

  // Unhandled API requests catch-all (prevents returning HTML index.html for API calls)
  app.use(['/api', '/api/*'], (req: ExpressRequest, res: ExpressResponse) => {
    res.status(404).json({ detail: `API endpoint '${req.originalUrl}' not found` });
  });

  // --- Vite & Production Static File Handler ---
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req: ExpressRequest, res: ExpressResponse) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[SkyOps UI] Web Console running on http://0.0.0.0:${PORT} (Proxying API to ${FASTAPI_URL})`);
  });
}

startServer().catch((err) => {
  console.error('[SkyOps UI] Failed to start server:', err);
  process.exit(1);
});
