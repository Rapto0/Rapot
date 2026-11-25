import path from "path";
import type { NextConfig } from "next";

const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  ...(allowedDevOrigins.length ? { allowedDevOrigins } : {}),
  turbopack: {
    root: path.resolve(__dirname),
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
  async rewrites() {
    const apiBasePath = process.env.NEXT_PUBLIC_API_URL || "/api";
    const normalizedApiBasePath =
      apiBasePath.startsWith("/") ? apiBasePath.replace(/\/$/, "") : "/api";
    const apiProxyTarget = (process.env.API_PROXY_TARGET || "http://localhost:8000").replace(/\/$/, "");

    return [
      {
        source: `${normalizedApiBasePath}/:path*`,
        destination: `${apiProxyTarget}/:path*`, // Proxy to FastAPI
      },
    ];
  },
};

export default nextConfig;
