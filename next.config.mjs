/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Allow dev access from local network host for HMR/dev resources
  allowedDevOrigins: ['192.168.1.11'],
}

export default nextConfig
