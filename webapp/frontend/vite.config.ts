import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' lets the static build run from any sub-path (GitHub Pages, file share).
// /api is proxied to the FastAPI service during development.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { port: 5173, proxy: { '/api/': 'http://127.0.0.1:8000' } },
  preview: { port: 4173, proxy: { '/api/': 'http://127.0.0.1:8000' } },
  build: {
    chunkSizeWarningLimit: 1600,
    rollupOptions: { output: { manualChunks: (id) => (id.includes('three') ? 'three' : undefined) } },
  },
})
