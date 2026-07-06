import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5175,
    // Zugriff über die ngrok-Domain erlauben
    allowedHosts: ['.ngrok.io', '.ngrok.app', '.ngrok-free.app'],
    proxy: {
      '/api': 'http://localhost:8020',
    },
  },
})
