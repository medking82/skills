const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),bridge=require('../skills/impeccable/scripts/live-jsx-source.cjs');
const root=process.env.DESIGN_JSX_TEST_ROOT,req=createRequire(path.join(root,'package.json')),babel=req('@babel/core'),React=req('react');
fs.mkdirSync(path.join(root,'app'),{recursive:true});fs.writeFileSync(path.join(root,'package.json'),'{"private":true}');
const file=path.join(root,'app/page.jsx'),maps=path.join(root,'.impeccable/live/jsx-source-maps');
process.env.NODE_ENV='development';
function render(code,target=file) {
  fs.writeFileSync(target,code);
  const output=babel.transformSync(code,{filename:target,configFile:false,babelrc:false,plugins:[[bridge,{development:true,root}],req('@babel/plugin-transform-react-jsx')]});
  const scope={exports:{}};vm.runInNewContext(output.code,{require:req,module:scope});
  const html=req('react-dom/server').renderToStaticMarkup(React.createElement(scope.exports));
  const relative=path.relative(root,target).split(path.sep).join('/');
  const map=fs.readdirSync(maps).map(n=>JSON.parse(fs.readFileSync(path.join(maps,n),'utf8'))).find(m=>Object.values(m.nodes).some(r=>r.file===relative));
  return {html,map,output:output.code};
}
function eventFor(html,number=1,instanceCount=1) {
  const articles=[...html.matchAll(/<article\b[^>]*>[\s\S]*?<\/article>/g)].map(m=>m[0]),outerHTML=articles[number];
  const id=outerHTML.match(/data-design-live-source="([a-f0-9]+)"/)[1],instance=outerHTML.match(/data-design-live-instance="([a-f0-9]+)"/)[1];
  return {id:'abc12345',count:3,element:{tagName:'article',outerHTML},sourceLocator:{templateSource:{id,occurrences:articles.length},instanceSource:{id:instance,rootSelected:true,occurrences:instanceCount}}};
}
const base="const React=require('react'); const handler=()=>1; const Card=({className,style,title,label,onClick})=><article className={className} style={style} title={title}><button onClick={onClick}>{label}</button></article>;";
const code=base+'const View=()=> <main><Card label="Same" onClick={handler}/><Card label="Same" onClick={handler}/></main>; module.exports=View;';
let {html,map}=render(code),event=eventFor(html),receipt=bridge.locate(root,map,event);
assert.equal(Object.keys(map.instances).length,2);assert.equal(receipt.sourceKind,'jsx-instance');assert.equal(receipt.editScope,'instance');
assert.equal(receipt.original,'<Card label="Same" onClick={handler}/>');assert.equal(receipt.startUTF16,code.lastIndexOf(receipt.original));
const chosen='<Card label="Same" onClick={handler} className="chosen" style={{fontWeight:600}}/>';
assert.equal(bridge.validate(root,receipt,chosen).validator,'babel-jsx-instance-props-v1');
for(const bad of [chosen.replace('Card','Other'),chosen.replace('label="Same"','label="Changed"'),chosen.replace('onClick={handler}','onClick={()=>2}'),
  chosen.replace('/>','>Extra</Card>'),chosen.replace('className="chosen"','className={theme}'),chosen.replace(' style=', ' data-extra="x" style=')]) {
  assert.throws(()=>bridge.validate(root,receipt,bad),/instance_bindings_changed|dynamic_instance_presentation_prop/);
}
assert.throws(()=>bridge.validate(root,receipt,chosen,'structural'),/instance_contract_mismatch/);
assert.throws(()=>bridge.validate(root,receipt,chosen,'static','template'),/edit_scope_mismatch/);
assert.throws(()=>bridge.locate(root,map,event,'all'),/unknown_edit_scope/);
assert.throws(()=>bridge.locate(root,map,{...event,sourceLocator:{...event.sourceLocator,instanceSource:{...event.sourceLocator.instanceSource,occurrences:2}}}),/shared_callsite_source/);
assert.throws(()=>bridge.locate(root,map,{...event,sourceLocator:{...event.sourceLocator,instanceSource:{...event.sourceLocator.instanceSource,rootSelected:false}}}),/select_component_root_for_instance/);
const otherInstance=Object.keys(map.instances).find(id=>id!==event.sourceLocator.instanceSource.id);
assert.throws(()=>bridge.locate(root,map,{...event,sourceLocator:{...event.sourceLocator,instanceSource:{...event.sourceLocator.instanceSource,id:otherInstance}}}),/instance_source_mismatch/);
assert.throws(()=>bridge.locate(root,map,{...event,element:{...event.element,outerHTML:'<article>'+event.element.outerHTML+'</article>'}}),/render_source_mismatch/);
const noInstance={...event,sourceLocator:{templateSource:event.sourceLocator.templateSource}};
assert.throws(()=>bridge.locate(root,map,noInstance),/shared_template_source/);
assert.throws(()=>bridge.locate(root,map,{...noInstance,sourceLocator:{templateSource:{...event.sourceLocator.templateSource,occurrences:1}}}),/missing_instance_provenance/);
const template=bridge.locate(root,map,event,'template'),templateChosen=template.original.replace('<article ','<article data-template="all" ');
assert.equal(template.sourceKind,'jsx');assert.equal(template.editScope,'template');assert.equal(template.observedInstances,2);
assert.throws(()=>bridge.validate(root,template,templateChosen),/edit_scope_mismatch/);
assert.equal(bridge.validate(root,template,templateChosen,'static','template').validator,'babel-jsx-template-static-edits-v1');
const instanceCode=code.slice(0,receipt.startUTF16)+chosen+code.slice(receipt.endUTF16);
const after=render(instanceCode).html;
const articles=[...after.matchAll(/<article\b[^>]*>/g)].map(m=>m[0]);
assert(!articles[0].includes('class="chosen"'));assert(articles[1].includes('class="chosen"'));assert(articles[1].includes('font-weight:600'));
assert(instanceCode.includes(base));assert.equal(fs.readFileSync(file,'utf8'),instanceCode);
assert.throws(()=>bridge.validate(root,receipt,chosen),/source_changed/);
const allCode=code.slice(0,template.startUTF16)+templateChosen+code.slice(template.endUTF16);
assert.equal((render(allCode).html.match(/data-template="all"/g)||[]).length,2);
// A static use inside a repeated parent is still a shared callsite.
let sample=render(base+'const Holder=()=> <div><Card label="Same" onClick={handler}/></div>; const View=()=> <main><Holder/><Holder/></main>;module.exports=View;');
assert.throws(()=>bridge.locate(root,sample.map,eventFor(sample.html,1,2)),/shared_callsite_source/);
assert.throws(()=>bridge.locate(root,sample.map,eventFor(sample.html,1,1)),/nested_component_instance_not_supported/);
// One current loop item is not a unique source use.
sample=render(base+'const View=()=> <main>{[1].map(n=><Card key={n} label="Same" onClick={handler}/>)}</main>;module.exports=View;');
const loopEvent=eventFor(sample.html,0,1);
assert.throws(()=>bridge.locate(root,sample.map,loopEvent),/callback_template_source/);
assert(bridge.locate(root,sample.map,loopEvent,'template').ok);
// Lexical shadowing must not inherit the real local Card's provenance.
sample=render(base+'function Shadow(Card){return <Card label="Other"/>} const View=()=> <Card label="Same" onClick={handler}/>;module.exports=View;');
assert.equal(Object.keys(sample.map.instances).length,1);
sample=render(base+'const View=()=> <Card {...{label:"Same"}} onClick={handler}/>;module.exports=View;');
assert.throws(()=>bridge.locate(root,sample.map,eventFor(sample.html,0)),/instance_spread_not_supported/);
sample=render(base+'const theme="x";const View=()=> <Card label="Same" className={theme} onClick={handler}/>;module.exports=View;');
assert.throws(()=>bridge.locate(root,sample.map,eventFor(sample.html,0)),/dynamic_instance_presentation_prop/);
for(const altered of [base.replace('className={className}','className={className || "fallback"}').replace('style={style} title={title}',''),
  base.replace('<article className={className} style={style} title={title}>','<article {...{className,style,title}}>')]) {
  sample=render(altered+'const View=()=> <main><Card label="Same"/><Card label="Same"/></main>;module.exports=View;');
  assert.equal(Object.keys(sample.map.instances).length,0);
}
for(const variant of [base.replace('const Card=', 'let Card=')+'Card=Card;const View=()=> <Card label="Same"/>;module.exports=View;',
  base+'const Alias=Card;const View=()=> <Alias label="Same"/>;module.exports=View;',
  base+'const Wrapped=((C)=>C)(Card);const View=()=> <Wrapped label="Same"/>;module.exports=View;']) {
  sample=render(variant);assert.equal(Object.keys(sample.map.instances).length,0);
  const outerHTML=sample.html.match(/<article\b[^>]*>[\s\S]*?<\/article>/)[0],id=outerHTML.match(/data-design-live-source="([a-f0-9]+)"/)[1];
  const unresolved={id:'abcd1234',count:3,element:{tagName:'article',outerHTML},sourceLocator:{templateSource:{id,occurrences:1}}};
  assert.throws(()=>bridge.locate(root,sample.map,unresolved),/missing_instance_provenance/);
  assert(bridge.locate(root,sample.map,unresolved,'template').ok);
}
console.log('Instance Callsite Isolation, Explicit Template Scope And Adversarial Checks Passed');
fs.mkdirSync(path.join(root,'src'),{recursive:true});
sample=render(base+'module.exports=Card;',path.join(root,'src/Library.jsx'));
const libraryHTML=sample.html.match(/<article\b[^>]*>[\s\S]*?<\/article>/)[0],libraryId=libraryHTML.match(/data-design-live-source="([a-f0-9]+)"/)[1];
const libraryEvent={id:'abcd4321',count:3,element:{tagName:'article',outerHTML:libraryHTML},sourceLocator:{templateSource:{id:libraryId,occurrences:1}}};
assert.throws(()=>bridge.locate(root,sample.map,libraryEvent),/missing_instance_provenance/);
assert(bridge.locate(root,sample.map,libraryEvent,'template').ok);
const {components}=require('../skills/impeccable/scripts/live-jsx-instances.cjs');
for(const suffix of ['export {Card};','const holder={};holder.Card=Card;']) {
  const ast=babel.parseSync(base+suffix,{sourceType:'module',configFile:false,babelrc:false,parserOpts:{plugins:['jsx']}});
  assert.equal(components(ast,babel.traverse,'src/Library.jsx').find(c=>c.name==='Card').reusable,true);
}
