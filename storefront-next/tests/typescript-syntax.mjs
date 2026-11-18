import {createRequire} from 'node:module';
import {readdirSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
const require=createRequire(import.meta.url);
const ts=require('typescript');
function* walk(dir){for(const e of readdirSync(dir,{withFileTypes:true})){const path=join(dir,e.name);if(e.isDirectory())yield* walk(path);else if(/\.(tsx?|jsx?)$/.test(e.name)&&!e.name.endsWith('.d.ts'))yield path}}
let count=0;let errors=0;
for(const dir of ['app','components','lib'])for(const f of walk(dir)){count++;const out=ts.transpileModule(readFileSync(f,'utf8'),{fileName:f,reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}});for(const d of out.diagnostics??[]){if(d.category===ts.DiagnosticCategory.Error){errors++;console.error(f,ts.flattenDiagnosticMessageText(d.messageText,'\n'));}}}
if(errors)process.exit(1);
console.log(`TypeScript/TSX syntax parsed: ${count} source files; 0 syntax errors.`);
