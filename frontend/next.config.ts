import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  // 禁用 Next.js 热重载，由 nodemon 处理重编译
  reactStrictMode: false,
  webpack: (config, { dev }) => {
    if (dev) {
      // 禁用 webpack 的热模块替换
      config.watchOptions = {
        ignored: ['**/*'], // 忽略所有文件变化
      };
    }
    return config;
  },
  eslint: {
    // 构建时忽略ESLint错误
    ignoreDuringBuilds: true,
  },
  // Proxy API requests to backend
  async rewrites() {
    return [
      // Exclude local API routes from proxying
      {
        source: '/api/auth/:path*',
        destination: '/api/auth/:path*', // Keep NextAuth routes local
      },
      {
        source: '/api/chat-sessions/:path*',
        destination: '/api/chat-sessions/:path*', // Keep chat sessions local
      },
      {
        source: '/api/sessions/:path*',
        destination: '/api/sessions/:path*', // Keep session messages local
      },
      {
        source: '/api/test/:path*',
        destination: '/api/test/:path*', // Keep test routes local
      },
      {
        source: '/api/health',
        destination: '/api/health', // Keep health check local
      },
      {
        source: '/api/settings/:path*',
        destination: '/api/settings/:path*', // Keep settings local
      },
      {
        source: '/api/chat',
        destination: '/api/chat', // Keep chat route local for processing
      },
      // Proxy other API requests to backend
      {
        source: '/api/:path*',
        destination: 'http://localhost:8001/api/:path*',
      },
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8001/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;
