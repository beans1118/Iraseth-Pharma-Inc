import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const original={VERCEL:process.env.VERCEL,CATALOG_API_BASE_URL:process.env.CATALOG_API_BASE_URL,NEXT_PUBLIC_STAFF_LOGIN_URL:process.env.NEXT_PUBLIC_STAFF_LOGIN_URL};
let iteration=0;
const load=()=>import('../next.config.mjs?deployment-test='+iteration++);
try{
  process.env.VERCEL='1';
  process.env.NEXT_PUBLIC_STAFF_LOGIN_URL='https://staff.example.invalid';
  for(const invalid of ['', 'http://backend.example.invalid','https://backend.example.invalid/api','https://user:secret@backend.example.invalid']){
    process.env.CATALOG_API_BASE_URL=invalid;
    await assert.rejects(load,/CATALOG_API_BASE_URL/);
  }
  process.env.CATALOG_API_BASE_URL='https://backend.example.invalid';
  delete process.env.NEXT_PUBLIC_STAFF_LOGIN_URL;
  await assert.rejects(load,/NEXT_PUBLIC_STAFF_LOGIN_URL/);
  process.env.NEXT_PUBLIC_STAFF_LOGIN_URL='https://staff.example.invalid';
  const config=(await load()).default;assert.equal(config.output,undefined,'Keep SSR and route handlers; never static-export the storefront');
  const vercel=JSON.parse(readFileSync(new URL('../vercel.json',import.meta.url),'utf8'));
  assert.equal(vercel.framework,'nextjs');assert.equal(vercel.outputDirectory,undefined);
}finally{for(const [key,value] of Object.entries(original))value===undefined?delete process.env[key]:process.env[key]=value;}
console.log('Staging storefront: required HTTPS API/staff origins, no credentials/path leakage, and server-rendered Vercel configuration passed.');
