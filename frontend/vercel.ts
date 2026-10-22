import { createDeploymentConfig } from './deployment.mjs';

// Vercel evaluates this before the build. Set BACKEND_ORIGIN in project settings.
export const config = createDeploymentConfig(process.env.BACKEND_ORIGIN);
