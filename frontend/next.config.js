/** @type {import('next').NextConfig} */
const nextConfig = {
  // Cloud Run用の設定
  output: 'standalone',
  
  // 環境変数の設定
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_GEMINI_API_KEY: process.env.NEXT_PUBLIC_GEMINI_API_KEY,
  },
  
  // 画像最適化の設定
  images: {
    unoptimized: true,
  },
  
  // 実験的機能
  experimental: {
    serverComponentsExternalPackages: [],
  },
  
  // リダイレクト設定（必要に応じて）
  async redirects() {
    return []
  },
  
  // リライト設定（必要に応じて）
  async rewrites() {
    return []
  }
}

module.exports = nextConfig
