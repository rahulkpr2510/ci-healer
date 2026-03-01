// frontend/next.config.ts

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for Docker multi-stage standalone build (copies .next/standalone)
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
