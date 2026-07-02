import type { NextConfig } from "next";

const API_URL = process.env.DASHBOARD_API_URL ?? "http://127.0.0.1:8100";

const nextConfig: NextConfig = {
  images: {
    localPatterns: [
      {
        pathname: "/advisors/**",
      },
      {
        pathname: "**",
        search: "",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
