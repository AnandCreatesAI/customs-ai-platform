#!/usr/bin/env node
/**
 * Restore legacy Next.js BFF route handlers for two-server rollback (Next :3000 + Django :8000).
 * Copies frontend/legacy/next-bff-app-api → frontend/app/api
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');
const legacy = path.join(frontendRoot, 'legacy', 'next-bff-app-api');
const target = path.join(frontendRoot, 'app', 'api');

if (!fs.existsSync(legacy)) {
  console.error('Legacy BFF backup missing at', legacy);
  process.exit(1);
}

fs.rmSync(target, { recursive: true, force: true });
fs.cpSync(legacy, target, { recursive: true });
console.log('Restored Next.js BFF routes to app/api (two-server dev mode).');
