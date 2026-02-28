import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // This magically forwards your frontend requests to the Express backend!
      '/data': 'http://localhost:8080',
      '/live': 'http://localhost:8080',
      '/health': 'http://localhost:8080'
    }
  }
})