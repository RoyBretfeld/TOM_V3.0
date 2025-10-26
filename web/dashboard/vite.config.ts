import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3003,
    strictPort: true, // Verhindert Port-Wechsel
    host: true
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
