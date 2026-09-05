import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxy = process.env.API_PROXY || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: apiProxy,
        changeOrigin: true,
      },
      '/health': {
        target: apiProxy,
        changeOrigin: true,
      },
    },
  },
})
