import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createDeploymentConfig } from './deployment.mjs';

const root = dirname(fileURLToPath(import.meta.url));
createDeploymentConfig(process.env.BACKEND_ORIGIN);
for (const file of ['index.html', 'static/app.js', 'static/review-ui.js', 'static/questions-ui.js', 'static/workflow-ui.js', 'static/style.css', 'static/base.css', 'static/favicon.svg']) {
  if (!(await readFile(join(root, 'public', file))).length) throw new Error(`Missing frontend asset: ${file}`);
}
console.log('Frontend assets and deployment configuration are ready.');
