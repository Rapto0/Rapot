import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['http://138.68.71.27:3000'],
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    const apiBasePath = process.env.NEXT_PUBLIC_API_URL || '/api'
    const normalizedApiBasePath =
      apiBasePath.startsWith('/') ? apiBasePath.replace(/\/$/, '') : '/api'
    const apiProxyTarget = (process.env.API_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/, '')

    return [
      {
        source: `${normalizedApiBasePath}/:path*`,
        destination: `${apiProxyTarget}/:path*`, // Proxy to FastAPI
      },
      {
        source: '/health-api/:path*',
        destination: 'http://localhost:5000/:path*', // Proxy to Health API
      },
    ]
  },
};

export default nextConfig;
