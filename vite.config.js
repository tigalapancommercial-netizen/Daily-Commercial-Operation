import { defineConfig } from 'vite';

// Base path harus sama dengan sub-path GitHub Pages (diisi workflow: /Daily-Commercial-Operation/).
// Saat lokal tetap '/'.
export default defineConfig({
  base: process.env.GITHUB_PAGES_BASE || '/',
  build: { target: 'es2019', sourcemap: false, chunkSizeWarningLimit: 900 },
});
