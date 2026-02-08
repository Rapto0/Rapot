import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['http://138.68.71.27:3000'],
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`, // Proxy to FastAPI
      },
      {
        source: '/health-api/:path*',
        destination: 'http://localhost:5000/:path*', // Proxy to Health API
      },
    ]
  },
};

export default nextConfig;
