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
    "/api/verified": ["../data/verified/manifest.json", "../data/verified/utilities.json", "../data/verified/coverage.json", "../data/national/geography.json"],
    "/api/verified/*": ["../data/verified/manifest.json", "../data/verified/utilities.json", "../data/verified/coverage.json", "../data/national/geography.json"],
    "/api/weather-history": ["../data/weather_history/index.json", "../data/weather_history/stations/*.json"],
    // Readiness checks the verified artifacts and the national snapshot without serving them.
    "/api/health": ["../data/national/*.json", "../data/verified/manifest.json", "../data/verified/utilities.json", "../data/verified/coverage.json"],
    "/api/operations/*": ["../data/environment/aef-samples.json", "../data/environment/aef-samples.evidence.json", "../data/environment/washington-boundary.json", "../data/environment/washington-boundary.evidence.json"],
  },
};

export default nextConfig;
