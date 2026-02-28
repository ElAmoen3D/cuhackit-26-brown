import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/data':   'http://localhost:5001',
      '/health': 'http://localhost:5001',
      // /live in the frontend maps to /video_feed on the Python server
      '/live': {
        target: 'http://localhost:5001',
        rewrite: () => '/video_feed'
      }
    }
  }
})