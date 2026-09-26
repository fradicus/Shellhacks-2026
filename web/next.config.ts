import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname, ".."),
  outputFileTracingIncludes: {
    "/explore": ["../data/national/*.json"],
    "/api/national": ["../data/national/*.json"],
    "/api/national/*": ["../data/national/*.json"],
    // Only used on the separate optional F32 branch; no assistant route is activated here.
    "/assistant": ["../data/national/*.json"],
  },
};

export default nextConfig;
