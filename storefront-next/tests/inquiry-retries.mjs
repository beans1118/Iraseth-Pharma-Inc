import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {webcrypto,createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
const require=createRequire(import.meta.url);
const ts=require('typescript');
const source=readFileSync(new URL('../lib/inquiry-submission.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const store=new Map();
const storage={getItem:key=>store.get(key)??null,setItem:(key,value)=>store.set(key,value)};
function reload(sessionStorage=storage, crypto=webcrypto){
 const exports={};
 runInNewContext(compiled,{exports,crypto,TextEncoder,Uint8Array,sessionStorage});
 return exports.submissionKey;
}
const payload=JSON.stringify({fullName:'Customer',email:'customer@example.org',items:[{id:'P1',quantity:2}]});
const key=await reload()(payload);
assert.equal(await reload()(payload),key,'Retry after reload must reuse its key');
const edited=JSON.stringify({fullName:'Customer',email:'customer@example.org',items:[{id:'P1',quantity:3}]});
assert.notEqual(await reload()(edited),key,'Changed quantities, including drawer changes, need a new key');
assert.equal(await reload()(payload),key,'Returning to earlier intent must recover the original key');
assert.ok(![...store.values()].some(value=>value.includes('customer@example.org')),'Retry storage must not contain customer details');
await assert.rejects(reload({getItem(){return null},setItem(){throw Error('Storage blocked')}})(payload),/Storage blocked/);
console.log('Inquiry retry tests passed: durable keys, changed intent, reload recovery, private storage and storage failure.');

const httpCrypto={getRandomValues:array=>webcrypto.getRandomValues(array)};
assert.equal(await reload(storage,httpCrypto)(payload),key,'HTTP fallback must recover existing secure-context keys');
for(const value of ['', 'abc', 'a'.repeat(55), 'a'.repeat(56), 'a'.repeat(64), 'a'.repeat(1000), '\u4e2d\u6587\ud83d\ude00']){
 const memory=new Map();
 const local={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v)};
 const generated=await reload(local,httpCrypto)(value);
 assert.match(generated,/^[a-f0-9]{32}$/);
 const expected=createHash('sha256').update(value).digest('hex');
 assert.equal(JSON.parse([...memory.values()][0])[expected],generated,'Fallback SHA-256 must match Node SHA-256');
 assert.equal(await reload(local)(value),generated,'HTTPS must recover HTTP keys');
}
await assert.rejects(reload({getItem:()=>null,setItem:()=>{}},{})(payload),/Secure random generation is unavailable/);
console.log('HTTP-context tests passed: no subtle/randomUUID, SHA-256 vectors and cross-context retry recovery.');
