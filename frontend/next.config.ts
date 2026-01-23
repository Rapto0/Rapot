import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*', // Proxy to FastAPI
      },
      {
        source: '/health-api/:path*',
        destination: 'http://localhost:5000/:path*', // Proxy to Health API
      },
    ]
  },
};

export default nextConfig;
