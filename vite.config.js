import { defineConfig } from 'vite';

// Vite's base path must match the GitHub Pages repository subpath.
// On local development the application continues to use '/'.
export default defineConfig({
  base: process.env.GITHUB_PAGES_BASE || '/',
});
