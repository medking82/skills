// Actual project Babel/React/Next transforms and SSR; project modules are fixture-owned.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const {createRequire}=require('node:module'),bridge=require('../skills/impeccable/scripts/live-jsx-source.cjs');
const {decodeIdentity,graph}=require('../skills/impeccable/scripts/live-jsx-modules.cjs');
const root=process.env.DESIGN_JSX_TEST_ROOT,req=createRequire(path.join(root,'package.json')),babel=req('@babel/core'),React=req('react');
const files={card:'lib/Card.jsx',barrel:'lib/index.ts',hoc:'lib/withCard.jsx',page:'app/page.jsx'};
const write=(name,text)=>{const file=path.join(root,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,text);return file;};
write('package.json','{"private":true}');process.env.NODE_ENV='development';
const card=write(files.card,"import {memo as m,forwardRef as f} from 'react'; export const Card=m(f(({label,onClick,className,style,title},ref)=><article ref={ref} className={className} style={style} title={title}><button onClick={onClick}>{label}</button></article>));");
const barrel=write(files.barrel,"export {Card as Imported} from './Card';");
const hoc=write(files.hoc,'export function withCard(Component){return props=><Component {...props}/>;}');
const page=path.join(root,files.page),maps=path.join(root,'.impeccable/live/jsx-source-maps');
function render(code,development=true,runtime='automatic') {
  write(files.page,code);const cache=new Map();
  function load(file) {
    if(cache.has(file))return cache.get(file).exports;
    const module={exports:{}};cache.set(file,module);
    const plugins=[...(/\.[jt]sx$/.test(file)&&development?[[bridge,{development:true,root}]]:[]),
      ...(/\.tsx?$/.test(file)?[[req('@babel/plugin-transform-typescript'),{isTSX:file.endsWith('.tsx')}]]:[]),
      [req('@babel/plugin-transform-react-jsx'),{runtime}],req('next/dist/compiled/babel/plugin-transform-modules-commonjs')];
    const compiled=babel.transformSync(fs.readFileSync(file,'utf8'),{filename:file,configFile:false,babelrc:false,parserOpts:{plugins:['jsx',...(/\.tsx?$/.test(file)?['typescript']:[])]},plugins});
    const localRequire=specifier=> {
      if(!specifier.startsWith('.'))return req(specifier);
      const base=path.resolve(path.dirname(file),specifier),resolved=[base,...['.jsx','.tsx','.ts','.js'].map(e=>base+e)].find(f=>fs.existsSync(f)&&fs.statSync(f).isFile());
      return load(resolved);
    };
    vm.runInNewContext(compiled.code,{require:localRequire,module,exports:module.exports,React,JSON,encodeURIComponent},{filename:file});
    return module.exports;
  }
  const entry=load(page),html=req('react-dom/server').renderToStaticMarkup(React.createElement(entry.default));
  return {html,entry};
}
const head="import React from 'react';import {Imported} from '../lib/index';import {withCard} from '../lib/withCard';const Enhanced=withCard(Imported);";
const initial=head+'const save=()=>1;export default function Page(){return <main><Imported label="Same" onClick={save}/><Enhanced label="Same" onClick={save}/></main>}';
function articles(html){return [...html.matchAll(/<article\b[^>]*>[\s\S]*?<\/article>/g)].map(m=>m[0]);}
function eventFor(html,index) {
  const list=articles(html),outerHTML=list[index],id=outerHTML.match(/data-design-live-source="([a-f0-9]+)"/)[1],instance=outerHTML.match(/data-design-live-instance="([^"]+)"/)?.[1];
  let count=0;
  if(instance) {
    const selected=decodeIdentity(instance);
    count=list.filter(h=>{const raw=h.match(/data-design-live-instance="([^"]+)"/)?.[1];if(!raw)return false;const other=decodeIdentity(raw);return other.id===selected.id&&String(other.key?.value)===String(selected.key?.value);}).length;
  }
  return {id:'1234abcd',count:3,element:{tagName:'article',outerHTML},sourceLocator:{templateSource:{id,occurrences:list.length},...(instance?{instanceSource:{id:instance,occurrences:count,rootSelected:true}}:{})}};
}
let result=render(initial),event=eventFor(result.html,1),receipt=bridge.locate(root,bridge.readMap(maps,event),event);
assert.equal(receipt.file,page);assert.equal(receipt.sourceKind,'jsx-instance');assert.equal(receipt.dependencies.length,4);
const chosen=receipt.original.replace('/>',' className="one" style={{fontWeight:600}}/>');
assert(bridge.validate(root,receipt,chosen).ok);
for(const file of [card,barrel,hoc]) {
  const before=fs.readFileSync(file);fs.appendFileSync(file,'\n// dependency drift');
  assert.throws(()=>bridge.validate(root,receipt,chosen),/instance_contract_mismatch/);fs.writeFileSync(file,before);
}
const dependencyBytes=[card,barrel,hoc].map(f=>fs.readFileSync(f));
let selectedCode=initial.slice(0,receipt.startUTF16)+chosen+initial.slice(receipt.endUTF16);
result=render(selectedCode);assert(!articles(result.html)[0].includes('class="one"'));assert(articles(result.html)[1].includes('class="one"'));
[card,barrel,hoc].forEach((f,i)=>assert.deepEqual(fs.readFileSync(f),dependencyBytes[i]));
// Observe the actual original evaluation order through getters, before and after instrumentation/writes.
const data="export const order=[];export const selections=[];const save=name=>selections.push(name);const items=[{get id(){order.push('key:a');return 'a'},get css(){order.push('css:a');return 'base-a'},name:'A'},{get id(){order.push('key:b');return 'b'},get css(){order.push('css:b');return 'base-b'},name:'B'}];";
const loop=head+data+'export default function Page(){return <main>{items.map(item=><Enhanced key={item.id} label={item.name} onClick={()=>save(item.name)} className={item.css}/>)}</main>}';
const originalOrder=Array.from(render(loop,false).entry.order);
assert.equal(originalOrder.length,4);assert.deepEqual([...originalOrder].sort(),['css:a','css:b','key:a','key:b']);
result=render(loop);assert.deepEqual(Array.from(result.entry.order),originalOrder);
event=eventFor(result.html,1);receipt=bridge.locate(root,bridge.readMap(maps,event),event);
assert.equal(receipt.sourceKind,'jsx-loop-instance');assert.equal(receipt.loopKey.value,'b');
const props={className:'target-b',style:{fontWeight:600}},specialized=bridge.specialize(root,receipt,props).replacement;
assert(specialized.includes('onClick={()=>save(item.name)}'));assert.equal((specialized.match(/item\.id/g)||[]).length,1);
assert.equal(bridge.validate(root,receipt,specialized,'static','instance',props).validator,'babel-jsx-keyed-props-v1');
assert.throws(()=>bridge.validate(root,receipt,specialized.replace('save(item.name)','save("Wrong")'),'static','instance',props),/keyed_specialization_mismatch/);
assert.throws(()=>bridge.specialize(root,receipt,{onClick:'wrong'}),/unverified_presentation_prop/);
selectedCode=require('../skills/impeccable/scripts/live-jsx-keyed.cjs').apply(loop,receipt,specialized);
result=render(selectedCode);assert.deepEqual(Array.from(result.entry.order),originalOrder);
assert(articles(result.html)[0].includes('class="base-a"'));assert(articles(result.html)[1].includes('class="target-b"'));
assert(!articles(result.html)[0].includes('font-weight:600'));assert(articles(result.html)[1].includes('font-weight:600'));
const classicOrder=Array.from(render(loop,false,'classic').entry.order);
assert.deepEqual(Array.from(render(selectedCode,true,'classic').entry.order),classicOrder);
// Repick another item after the first source specialization, preserving its existing conditional props.
event=eventFor(result.html,0);receipt=bridge.locate(root,bridge.readMap(maps,event),event);
const second=bridge.specialize(root,receipt,{className:'target-a'}).replacement;
selectedCode=require('../skills/impeccable/scripts/live-jsx-keyed.cjs').apply(selectedCode,receipt,second);
result=render(selectedCode);assert.deepEqual(Array.from(result.entry.order),originalOrder);
assert(articles(result.html)[0].includes('class="target-a"'));assert(articles(result.html)[1].includes('class="target-b"'));
result.entry.default().props.children.forEach(element=>element.props.onClick());assert.deepEqual(Array.from(result.entry.selections),['A','B']);
const reordered=selectedCode.replace('return <main>{items.map','items.reverse();return <main>{items.map');
result=render(reordered);assert(articles(result.html)[0].includes('class="target-b"'));assert(articles(result.html)[1].includes('class="target-a"'));
for(const keys of ['1,"1"','0,-0']) {
  result=render(head+`const save=()=>1;export default function Page(){return <main>{[${keys}].map(item=><Enhanced key={item} label="Same" onClick={save}/>)}</main>}`);
  event=eventFor(result.html,0);assert.equal(event.sourceLocator.instanceSource.occurrences,2);
  assert.throws(()=>bridge.locate(root,bridge.readMap(maps,event),event),/shared_callsite_source/);
}
const indexed=head+'export default function Page(){return <main>{["a"].map((item,index)=><Enhanced key={index} label={item}/>)}</main>}';
result=render(indexed);event=eventFor(result.html,0);assert(!event.sourceLocator.instanceSource);
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,event),event),/missing_instance_provenance|callback_template_source/);
const nested=head+"const items=[{id:'a',name:'A'}];function Holder(){return <section>{items.map(item=><Enhanced key={item.id} label={item.name}/>)}</section>}export default function Page(){return <main><Holder/><Holder/></main>}";
result=render(nested);event=eventFor(result.html,0);
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,event),event),/shared_callsite_source/);
event.sourceLocator.instanceSource.occurrences=1;
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,event),event),/nested_component_instance_not_supported/);
const native=head+data+'export default function Page(){return <main>{items.map(item=><article className={item.css} key={item.id}><button onClick={()=>save(item.name)}>{item.name}</button></article>)}</main>}';
result=render(native);event=eventFor(result.html,1);receipt=bridge.locate(root,bridge.readMap(maps,event),event);
assert.equal(receipt.sourceKind,'jsx-loop-instance');
const nativeChosen=bridge.specialize(root,receipt,{className:'native-b'}).replacement;
result=render(require('../skills/impeccable/scripts/live-jsx-keyed.cjs').apply(native,receipt,nativeChosen));
assert(articles(result.html)[0].includes('class="base-a"'));assert(articles(result.html)[1].includes('class="native-b"'));
const beforeHoc=fs.readFileSync(hoc);write(files.hoc,'export function withCard(Component){return props=><Component {...props} className="forced"/>;}');
result=render(initial);event=eventFor(result.html,1);assert(!event.sourceLocator.instanceSource);
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,event),event),/shared_template_source/);fs.writeFileSync(hoc,beforeHoc);
const shadow="import React from 'react';import {Imported} from '../lib/index';function memo(Component){return props=><Component {...props} className=\"forced\"/>}const Enhanced=memo(Imported);export default function Page(){return <Enhanced label=\"Same\"/>}";
result=render(shadow);event=eventFor(result.html,0);assert(!event.sourceLocator.instanceSource);
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,event),event),/missing_instance_provenance|callback_template_source/);
console.log('Cross-Module Barrels, React/HOC Forwarding, Keyed Reordering, Repeat Edits And Single Evaluation Passed');
const typed=write('app/typed/page.tsx',"import {cloneElement as ce,type ReactElement as E,type ComponentProps as P} from 'react';import {Imported} from '../../lib/index';export default function Page(){return <main>{['a'].map(item=><Imported key={item} label={item}/>)}</main>}");
const typedGraph=graph(root,typed,babel,bridge.sourceFile),typedPlan=typedGraph.describe([...typedGraph.main.elements.values()].find(n=>n.openingElement.name.name==='Imported'));
assert.equal(require('../skills/impeccable/scripts/live-jsx-keyed.cjs').recipe(typedPlan).additionalEdits.length,0);
write('app/typed/page.tsx',fs.readFileSync(typed,'utf8').replace('function Page()','function Page({ce}:{ce:unknown})'));
const shadowGraph=graph(root,typed,babel,bridge.sourceFile),shadowPlan=shadowGraph.describe([...shadowGraph.main.elements.values()].find(n=>n.openingElement.name.name==='Imported'));
assert.notEqual(require('../skills/impeccable/scripts/live-jsx-keyed.cjs').recipe(shadowPlan).cloneName,'ce');
