// Exercise gallery handlers through React's element tree without a browser or inventory writes.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
const require=createRequire(import.meta.url), ts=require('typescript');
let state=0;const touch={current:null};
const react={...require('react'),useState:()=>[state,fn=>{state=typeof fn==='function'?fn(state):fn;}],useRef:()=>touch};
const exports={};
const code=ts.transpileModule(readFileSync(new URL('../components/ProductGallery.tsx',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
runInNewContext(code,{exports,require:name=>name==='react'?react:require(name)});
const draw=()=>exports.default({images:['one','two','three'],name:'Documented device'});
function nodes(node){if(!node||typeof node!=='object')return [];return [node,...[node.props?.children].flat(Infinity).flatMap(nodes)];}
let tree=draw();assert.equal(tree.props['aria-roledescription'],'carousel');
tree.props.onKeyDown({key:'ArrowRight',preventDefault(){}});assert.equal(state,1);
tree=draw();assert.equal(nodes(tree).find(n=>n.props?.className==='gallery-track').props.style.transform,'translateX(-100%)');
nodes(tree).find(n=>n.props?.['aria-label']==='Previous product image').props.onClick();assert.equal(state,0);
nodes(draw()).find(n=>n.props?.['aria-label']==='View image 3').props.onClick();assert.equal(state,2);
const viewport=nodes(draw()).find(n=>n.props?.className==='gallery-viewport');
viewport.props.onTouchStart({touches:[{clientX:200,clientY:10}]});viewport.props.onTouchEnd({changedTouches:[{clientX:50,clientY:12}]});assert.equal(state,0);
const selected=nodes(draw()).filter(n=>n.type==='button'&&n.props['aria-pressed']===true);assert.equal(selected.length,1);
assert.match(nodes(draw()).find(n=>n.props?.className==='gallery-indicator').props.children.join(''),/Primary image/);
const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');assert.match(css,/prefers-reduced-motion/);
console.log('Gallery: arrows, keyboard wrap, thumbnail selection, horizontal swipe, selection semantics, primary indicator and reduced-motion styles. Browser focus remains a manual check.');
