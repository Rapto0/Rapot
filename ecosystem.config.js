module.exports = {
  apps: [
    {
      name: 'api',
      script: '/home/user/Rapot/start-api.sh',
      cwd: '/home/user/Rapot',
    },
    {
      name: 'frontend',
      script: 'npm',
      args: 'run dev -- -H 0.0.0.0',
      cwd: '/home/user/Rapot/frontend',
      env: {
        HOSTNAME: '0.0.0.0',
        NODE_ENV: 'production',
        __NEXT_PRIVATE_ORIGIN: 'http://138.68.71.27:3000',
      },
    },
  ],
};
