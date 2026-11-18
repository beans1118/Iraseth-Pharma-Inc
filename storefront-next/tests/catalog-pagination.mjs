import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
const require=createRequire(import.meta.url), ts=require('typescript'), exports={};
const compiled=ts.transpileModule(readFileSync(new URL('../lib/catalog.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const calls=[];let broken=false;
runInNewContext(compiled,{exports,require,process:{env:{CATALOG_API_BASE_URL:'http://catalog.invalid'}},console:{error:()=>{}},fetch:async url=>{
  calls.push(url);const page=Number(new URL(url).searchParams.get('page'));
  return {ok:true,json:async()=>({products:broken?[]:Array.from({length:page===1?100:7},(_,i)=>({id:`P${(page-1)*100+i}`,slug:`P${(page-1)*100+i}`,name:'Medical item',category:page===1?'Supplies':'Diagnostics',inStock:false,publicPrice:null})),hasMore:broken||page===1})};
}});
const result=await exports.getPublicProducts();
assert.equal(result.connected,true);assert.equal(result.products.length,107);assert.equal(calls.length,2);
assert.equal(result.products.at(-1).category,'Diagnostics');assert.match(calls[1],/page=2/);
broken=true;assert.equal((await exports.getPublicProducts()).connected,false);
console.log('Catalog pagination: 107 live records, categories after page 1, bounded failure when upstream makes no progress.');
