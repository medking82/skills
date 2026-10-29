const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const bridge=require('../skills/impeccable/scripts/live-jsx-source.cjs');
const root=process.env.DESIGN_JSX_TEST_ROOT;
assert(root,'Test root required');fs.mkdirSync(path.join(root,'src'),{recursive:true});
fs.writeFileSync(path.join(root,'package.json'),'{"private":true}');
const file=path.join(root,'src/Panel.tsx');
const code="const emoji = '😀'; const label: string='Same'; const handler=()=>1; const View=()=> <p>Before<span onClick={handler}>{label}</span><span onClick={handler}>{label}</span>After</p>;";
fs.writeFileSync(file,code);
process.env.NODE_ENV='production';
assert.deepEqual(bridge({}, {development:true,root}),{});
fs.mkdirSync(path.join(root,'dist'),{recursive:true});fs.writeFileSync(path.join(root,'dist/Bad.tsx'),'<span/>');
assert.throws(()=>bridge.sourceFile(root,'dist/Bad.tsx'),/not_true_jsx_source/);
if(!process.env.DESIGN_JSX_WITH_COMPILER){console.log('JSX Boundary Checks Passed');process.exit(0);}
process.env.NODE_ENV='development';
const {createRequire}=require('node:module'),req=createRequire(path.join(root,'package.json')),babel=req('@babel/core');
const output=babel.transformSync(code,{filename:file,configFile:false,babelrc:false,parserOpts:{plugins:['jsx','typescript']},plugins:[[bridge,{development:true,root}]]});
assert(output.code.includes('data-design-live-source'));
const maps=path.join(root,'.impeccable/live/jsx-source-maps');
const map=JSON.parse(fs.readFileSync(path.join(maps,fs.readdirSync(maps)[0]),'utf8'));
const spans=Object.values(map.nodes).filter(r=>r.tag==='span').sort((a,b)=>a.start-b.start);
assert.equal(spans.length,2);assert.notEqual(spans[0].id,spans[1].id);
const r=spans[1];
const event={id:'1234abcd',count:3,element:{tagName:'span',outerHTML:`<span data-design-live-source="${r.id}">Same</span>`},sourceLocator:{templateSource:{id:r.id,occurrences:1}}};
const receipt=bridge.locate(root,bridge.readMap(maps,event),event);
assert.equal(receipt.original,'<span onClick={handler}>{label}</span>');
assert.equal(receipt.replaceStartOffset,[...code.slice(0,r.start)].length);
assert(receipt.replaceStartOffset<receipt.startUTF16);
const chosen='<span className="chosen" style={{fontWeight:600}} onClick={handler}>{label}</span>';
assert.equal(bridge.validate(root,receipt,chosen).ok,true);
for(const bad of ['<span>Same</span>','<span onClick={()=>2}>{label}</span>','<a onClick={handler}>{label}</a>',
  '<span onClick={handler}>{label}<b>Extra</b></span>'])assert.throws(()=>bridge.validate(root,receipt,bad),/template_bindings_or_structure_changed/);
assert.throws(()=>bridge.locate(root,map,{...event,sourceLocator:{templateSource:{id:r.id,occurrences:2}}}),/shared_template_source/);
assert.throws(()=>bridge.locate(root,map,{...event,sourceLocator:{}}),/missing_compiler_provenance/);
const loader=require('../skills/impeccable/scripts/live-jsx-loader.cjs');let transformed;
loader.call({mode:'development',resourcePath:file,getOptions:()=>({root}),callback:(err,result,map)=>{assert.ifError(err);transformed=result;assert.equal(map.version,3);}},code);
assert(transformed.includes('<span'));assert(transformed.includes('data-design-live-source'));
let unchanged;loader.call({mode:'production',callback:(err,result)=>unchanged=result},code);assert.equal(unchanged,code);
// Another source module cannot erase the first module's manifest shard.
const other=path.join(root,'src/Other.jsx');fs.writeFileSync(other,'const Other=()=> <h2>Other</h2>;');
babel.transformSync(fs.readFileSync(other,'utf8'),{filename:other,configFile:false,babelrc:false,parserOpts:{plugins:['jsx']},plugins:[[bridge,{development:true,root}]]});
assert.equal(bridge.readMap(maps,event).nodes[r.id].file,'src/Panel.tsx');
const repeated=path.join(root,'src/Repeated.jsx');
const repeatedCode="const React=require('react'); module.exports=()=> ['A','B'].map(item=><span>{item}</span>);";
fs.writeFileSync(repeated,repeatedCode);
const compiled=babel.transformSync(repeatedCode,{filename:repeated,configFile:false,babelrc:false,
  plugins:[[bridge,{development:true,root}],req('@babel/plugin-transform-react-jsx')]});
const moduleScope={exports:{}};
vm.runInNewContext(compiled.code,{require:req,module:moduleScope});
const React=req('react'),html=req('react-dom/server').renderToStaticMarkup(React.createElement(moduleScope.exports));
const markers=[...html.matchAll(/data-design-live-source="([a-f0-9]+)"/g)].map(m=>m[1]);
assert.equal(markers.length,2);assert.equal(markers[0],markers[1]);
const loopEvent={id:'1234abce',count:3,element:{tagName:'span',outerHTML:`<span data-design-live-source="${markers[0]}">A</span>`},sourceLocator:{templateSource:{id:markers[0],occurrences:2}}};
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,loopEvent),loopEvent),/shared_template_source/);
assert.throws(()=>bridge.locate(root,bridge.readMap(maps,loopEvent),{...loopEvent,sourceLocator:{templateSource:{id:markers[0],occurrences:1}}}),/callback_template_source/);
const loopRecord=bridge.readMap(maps,loopEvent).nodes[markers[0]];
const loopReceipt={sourceKind:'jsx',publishToSource:false,file:repeated,sourceSha256:loopRecord.hash,
  startUTF16:loopRecord.start,endUTF16:loopRecord.end,replaceStartOffset:loopRecord.start,replaceEndOffset:loopRecord.end,
  original:repeatedCode.slice(loopRecord.start,loopRecord.end)};
assert.throws(()=>bridge.validate(root,loopReceipt,loopReceipt.original,'structural'),/callback_template_source/);
// Reproduce the structural restriction; only an explicit structural lane may relax it.
const structuralFile=path.join(root,'src/Structural.tsx');
function structuralReceipt(original) {
  const code=`const View=()=> ${original};`;
  fs.writeFileSync(structuralFile,code);
  babel.transformSync(code,{filename:structuralFile,configFile:false,babelrc:false,parserOpts:{plugins:['jsx','typescript']},plugins:[[bridge,{development:true,root}]]});
  const manifest=fs.readdirSync(maps).map(n=>JSON.parse(fs.readFileSync(path.join(maps,n),'utf8'))).find(m=>Object.values(m.nodes).some(r=>r.file==='src/Structural.tsx'));
  const record=Object.values(manifest.nodes).sort((a,b)=>a.start-b.start)[0];
  return bridge.locate(root,manifest,{id:'abcd9876',count:3,element:{tagName:record.tag,outerHTML:`<${record.tag} data-design-live-source="${record.id}"></${record.tag}>`},sourceLocator:{templateSource:{id:record.id,occurrences:1}}});
}
let structural=structuralReceipt('<div><span>{label}</span><button onClick={save}>Save</button></div>');
const reorganized='<section><header><strong>{label}</strong></header><aside><button className="primary" onClick={save}>Save Now</button></aside></section>';
assert.throws(()=>bridge.validate(root,structural,reorganized),/template_bindings_or_structure_changed/);
assert.equal(bridge.validate(root,structural,reorganized,'structural').validator,'babel-jsx-structural-edits-v1');
for(const bad of [
  '<section><button onClick={save}>Save</button></section>',
  '<section>{label}{label}<button onClick={save}>Save</button></section>',
  '<section>{label.trim()}<button onClick={save}>Save</button></section>',
  '<section onClick={save}>{label}<button>Save</button></section>',
  '<section>{label}<a onClick={save}>Save</a></section>',
  '<section><button onClick={save}>{label}</button></section>',
  '<section><button onClick={save}>Save</button>{label}</section>',
  '<form>{label}<button onClick={save}>Save</button></form>'
])assert.throws(()=>bridge.validate(root,structural,bad,'structural'),/template_bindings_or_structure_changed/);
const conditional='<div>{ready ? <span>{label}</span> : <i>{fallback}</i>}{items.map(item => <button key={item.id} onClick={() => choose(item)}>{item.name}</button>)}</div>';
structural=structuralReceipt(conditional);
const dynamicChosen='<section>{ready ? <header><strong>{label}</strong></header> : <aside><em>{fallback}</em></aside>}{items.map(item => <button key={item.id} onClick={() => choose(item)}><span>{item.name}</span></button>)}</section>';
assert(bridge.validate(root,structural,dynamicChosen,'structural').ok);
for(const bad of [dynamicChosen.replace('ready ?', '!ready ?'),dynamicChosen.replace('item =>','other =>'),
  dynamicChosen.replace('items.map','others.map'),dynamicChosen.replace('key={item.id} ',''),
  dynamicChosen.replace('<button key=', '<article><button key=').replace('</button>)','</button></article>)'),
  dynamicChosen.replace('choose(item)','choose(other)'),dynamicChosen.replace('{item.name}','{item.name.toUpperCase()}'),
  dynamicChosen.replace('<strong>{label}</strong>','<strong/>').replace('</section>','{label}</section>')]) {
  assert.throws(()=>bridge.validate(root,structural,bad,'structural'),/template_bindings_or_structure_changed/);
}
// Spread order and added static overrides are locked in both lanes.
structural=structuralReceipt('<button {...props} disabled={locked}>{label}</button>');
for(const mode of ['static','structural'])for(const bad of [
  '<button disabled={locked} {...props}>{label}</button>',
  '<button {...props} disabled={locked} className="override">{label}</button>'
])assert.throws(()=>bridge.validate(root,structural,bad,mode),/template_bindings_or_structure_changed/);
structural=structuralReceipt('<div><Provider value={context}><span>{label}</span></Provider>{first()}{second()}</div>');
assert(bridge.validate(root,structural,'<section><Provider value={context}><span>{label}</span></Provider>{first()}{second()}</section>','structural').ok);
for(const bad of [
  '<div><Provider value={context}><strong>{label}</strong></Provider>{first()}{second()}</div>',
  '<div><Provider value={context}><span>{label}</span></Provider>{second()}{first()}</div>'
])assert.throws(()=>bridge.validate(root,structural,bad,'structural'),/template_bindings_or_structure_changed/);
assert.throws(()=>bridge.validate(root,structural,structural.original,'unknown'),/unknown_validation_mode/);
assert.equal(fs.readFileSync(structuralFile,'utf8'),`const View=()=> ${structural.original};`);
fs.writeFileSync(file,code+'\n// concurrent edit');
assert.throws(()=>bridge.locate(root,map,event),/source_changed_since_render/);
assert.throws(()=>bridge.validate(root,receipt,chosen),/source_changed/);
console.log('Compiler Mapping, Binding Preservation, Loader And Drift Checks Passed');
