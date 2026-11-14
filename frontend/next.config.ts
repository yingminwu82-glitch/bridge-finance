import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In production (Vercel), /api/* is handled by Vercel Python Serverless Functions.
  // In local development, proxy /api/* to FastAPI on localhost:8000.
  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
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
