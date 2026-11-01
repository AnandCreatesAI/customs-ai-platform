import type { NextConfig } from "next";

const djangoDevOrigin =
  process.env.DJANGO_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: false,
  images: {
    unoptimized: true,
  },
  experimental: {
    agentFeedback: true,
  },
  // Static export (output: "export") is incompatible with PPR / cacheComponents.
  cacheComponents: false,
  partialPrefetching: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  /** Two-server rollback: `npm run dev` proxies /api to Django without Next BFF routes. */
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: `${djangoDevOrigin}/api/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
