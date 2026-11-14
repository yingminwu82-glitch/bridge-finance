import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API proxying:
  // - Production: handled by vercel.json rewrites → Python Serverless Function
  // - Development: proxy /api/* to FastAPI on localhost:8000
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
