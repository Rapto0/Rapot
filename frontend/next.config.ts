import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ['http://138.68.71.27:3000'],
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    const apiBasePath = process.env.NEXT_PUBLIC_API_URL || '/api'
    const normalizedApiBasePath =
      apiBasePath.startsWith('/') ? apiBasePath.replace(/\/$/, '') : '/api'
    const apiProxyTarget = (process.env.API_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/, '')
    const healthProxyTarget = (process.env.HEALTH_PROXY_TARGET || 'http://localhost:5000').replace(/\/$/, '')

    return [
      {
        source: `${normalizedApiBasePath}/:path*`,
        destination: `${apiProxyTarget}/:path*`, // Proxy to FastAPI
      },
      {
        source: '/health-api/:path*',
        destination: `${healthProxyTarget}/:path*`,
      },
    ]
  },
};

export default nextConfig;
