import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
const require=createRequire(import.meta.url),ts=require('typescript'),exports={};
runInNewContext(ts.transpileModule(readFileSync(new URL('../src/api-url.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports,Error});
assert.equal(exports.resolveApiUrl('/api/products'),'/api/products');
assert.equal(exports.resolveApiUrl('/api/v2/support/customer/messages','https://backend.example.invalid/'),'https://backend.example.invalid/api/v2/support/customer/messages');
assert.throws(()=>exports.resolveApiUrl('https://other.invalid/api/products'),/API paths/);
for(const file of ['api.ts','SupportChat.tsx','BrochureReview.tsx']){
  const source=readFileSync(new URL('../src/'+file,import.meta.url),'utf8');
  assert.doesNotMatch(source,/fetch\(['"]\/api\//,'Every API fetch uses the configured origin');
}
const config=JSON.parse(readFileSync(new URL('../vercel.json',import.meta.url),'utf8'));
assert.deepEqual(config.rewrites,[{source:'/(.*)',destination:'/index.html'}]);
const {loadConfigFromFile}=await import('vite');
const original={VERCEL:process.env.VERCEL,VITE_API_BASE_URL:process.env.VITE_API_BASE_URL};
try{
  process.env.VERCEL='1';
  for(const invalid of ['', 'http://backend.example.invalid','https://backend.example.invalid/api','https://user:secret@backend.example.invalid']){
    process.env.VITE_API_BASE_URL=invalid;
    await assert.rejects(()=>loadConfigFromFile({command:'build',mode:'production'}),/VITE_API_BASE_URL/);
  }
  process.env.VITE_API_BASE_URL='https://backend.example.invalid';
  assert.ok(await loadConfigFromFile({command:'build',mode:'production'}));
}finally{for(const [key,value] of Object.entries(original))value===undefined?delete process.env[key]:process.env[key]=value;}
console.log('Deployment: local/cloud API URLs, all fetch paths, SPA fallback and Vercel HTTPS configuration guards passed.');
