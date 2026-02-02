import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use backend hostname for Docker, localhost for local development
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://backend:8000'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
