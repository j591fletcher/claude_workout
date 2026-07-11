import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['apple-touch-icon.png'],
      // Precaches the app shell only (JS/CSS/HTML). No runtimeCaching rules
      // are added on purpose — /hevy, /ask, /chat, /health must always hit
      // the network live, never served stale from a cache (CLAUDE.md data
      // freshness expectations for a personal training log).
      manifest: {
        name: 'Workout Coach',
        short_name: 'Workout',
        description: 'Your Hevy training history, progression, and Nippard-grounded coaching',
        start_url: '/',
        display: 'standalone',
        background_color: '#121212',
        theme_color: '#121212',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/ask': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/hevy': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
