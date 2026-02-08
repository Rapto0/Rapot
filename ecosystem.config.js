const path = require('path');

const ROOT_DIR = __dirname;
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');

module.exports = {
  apps: [
    {
      name: 'api',
      script: path.join(ROOT_DIR, 'start-api.sh'),
      cwd: ROOT_DIR,
    },
    {
      name: 'frontend',
      script: 'npm',
      args: 'run dev -- -H 0.0.0.0 -p 3000',
      cwd: FRONTEND_DIR,
      env: {
        HOSTNAME: '0.0.0.0',
        PORT: '3000',
        NODE_ENV: 'production',
        __NEXT_PRIVATE_ORIGIN: 'http://138.68.71.27:3000',
      },
    },
  ],
};
