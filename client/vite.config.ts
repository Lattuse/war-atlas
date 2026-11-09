/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // FastAPI dev server (cd server && fastapi dev app/main.py)
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'node',
  },
})
