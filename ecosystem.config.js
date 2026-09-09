const path = require('path');

const ROOT_DIR = __dirname;
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');

// LEGACY ONLY: canonical deployment is docker-compose.yml.
// Loading this file must never silently restart a second scheduler beside Compose.
if (process.env.RAPOT_ALLOW_LEGACY_PM2 !== '1') {
  throw new Error('Legacy PM2 deployment is disabled. Follow scripts/DEPLOY.md for Docker Compose.');
}

module.exports = {
  apps: [
    {
      name: 'api',
      script: path.join(ROOT_DIR, 'start-api.sh'),
      cwd: ROOT_DIR,
      env: {
        RUN_EMBEDDED_BOT: 'false',
      },
    },
    {
      name: 'frontend',
      script: 'npm',
      args: 'run start -- -H 127.0.0.1 -p 3000',
      cwd: FRONTEND_DIR,
      instances: 1,
      exec_mode: 'fork',
      env: {
        HOSTNAME: '127.0.0.1',
        PORT: '3000',
        NODE_ENV: 'production',
      },
    },
  ],
};
