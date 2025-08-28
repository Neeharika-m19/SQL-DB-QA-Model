import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // server proxy if you prefer `/api/...` → `http://localhost:8000`
  // server: {
  //   proxy: { '/api': 'http://localhost:8000' }
  // }
});
