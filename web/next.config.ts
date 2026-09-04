import type { NextConfig } from "next";
import BundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = BundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const nextConfig: NextConfig = {
  agentRules: false,
  turbopack: {
    root: __dirname,
  },
};

export default withBundleAnalyzer(nextConfig);
