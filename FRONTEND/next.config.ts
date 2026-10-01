import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The browser test builds into its own folder so it never clobbers a dev build.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
