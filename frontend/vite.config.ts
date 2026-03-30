import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const basePath = process.env.VITE_BASE_PATH || '/'

export default defineConfig({
  base: basePath,
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  },
  server: {
    port: 5173,
    proxy: {
      '^/api/(strategies|analysis|contact)(/.*)?$': {
        target: 'http://localhost:5050',
        changeOrigin: true
      },
      '^/api/auth(/.*)?$': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: p => p.replace(/^\/api/, '')
      },
      '^/api/.*': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: p => p.replace(/^\/api/, '')
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      }
    }
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['recharts'],
          motion: ['framer-motion']
        }
      }
    }
  }
})
