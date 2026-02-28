import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../video_processing/camera_backend/dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      // ── Python face-recognition server (direct) ───────────────────────────
      '/data':      'http://localhost:5001',
      '/health':    'http://localhost:5001',
      '/face_crop': 'http://localhost:5001',
      // /live in the frontend maps to /video_feed on the Python server
      '/live': {
        target:  'http://localhost:5001',
        rewrite: () => '/video_feed'
      },

      // ── Node Express server (port 8080) ───────────────────────────────────
      // Face database CRUD + Copilot AI analysis + single-frame snapshot
      '/face_db':        'http://localhost:8080',
      '/snapshot':       'http://localhost:8080',
      '/copilot':        'http://localhost:8080',
    }
  }
})
