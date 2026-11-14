import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In production (Vercel), proxy /api/* to the backend Vercel project via NEXT_PUBLIC_API_URL.
  // In local development, proxy to FastAPI on localhost:8000.
  async rewrites() {
    const apiUrl = process.env.API_BASE_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
