import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({mode})=>{
  const env=loadEnv(mode,process.cwd(),'VITE_');
  const base=process.env.VITE_API_BASE_URL||env.VITE_API_BASE_URL||'';
  if(process.env.VERCEL==='1'&&!base)throw new Error('VITE_API_BASE_URL is required on Vercel. Set the HTTPS Flask origin, without /api.');
  if(base){
    const url=new URL(base);
    if(!['http:','https:'].includes(url.protocol)||url.pathname!=='/'||url.search||url.hash||url.username||url.password||
      (process.env.VERCEL==='1'&&url.protocol!=='https:'))throw new Error('VITE_API_BASE_URL must be a Flask origin without a path, credentials or query; Vercel requires HTTPS.');
  }
  return {
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {'/api': {target: process.env.VITE_DEV_API_TARGET || env.VITE_DEV_API_TARGET || 'http://127.0.0.1:5000', changeOrigin: true}}
  }
  };
});
