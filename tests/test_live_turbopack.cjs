// Opt-in checks against the project's real Next schema and Babel compiler.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {createRequire}=require('node:module');
const root=process.env.DESIGN_TURBOPACK_TEST_ROOT;
assert(root,'Test root required');fs.mkdirSync(path.join(root,'app'),{recursive:true});
fs.writeFileSync(path.join(root,'package.json'),'{"private":true}');
const req=createRequire(path.join(root,'package.json'));
const {configSchema}=req('next/dist/server/config-schema');
const sourcePath=/(?:^|\/)app\/.*\.(jsx|tsx)$/;
const rule={condition:{all:['development',{not:'foreign'},{path:sourcePath}]},
  loaders:[{loader:path.resolve(__dirname,'../skills/impeccable/scripts/live-jsx-loader.cjs'),options:{root}}]};
assert.equal(configSchema.safeParse({turbopack:{rules:{'*':rule}}}).success,true);
assert.equal(configSchema.safeParse({turbopack:{rules:{'*':{...rule,enforce:'pre'}}}}).success,false);
for(const name of ['app/page.jsx','app/Client.tsx','workspace/app/Client.tsx'])assert(sourcePath.test(name));
for(const name of ['app/page.js','app/x.tsx.css','other/Client.tsx'])assert(!sourcePath.test(name));
const filename=path.join(root,'app/Client.tsx'),code="const label: string='Same'; export const Client=()=> <span>{label}</span>;";
fs.writeFileSync(filename,code);
const loader=require('../skills/impeccable/scripts/live-jsx-loader.cjs');
process.env.NODE_ENV='development';let transformed,map;
const context={mode:'development',sourceMap:true,resourcePath:filename,getOptions:()=>({root}),
  callback:(err,result,resultMap)=>{assert.ifError(err);transformed=result;map=resultMap;}};
for(const api of ['emitFile','loadModule','utils'])Object.defineProperty(context,api,{get(){throw Error('Unsupported Turbopack API: '+api);}});
loader.call(context,code);
assert(transformed.includes('data-design-live-source'));assert(transformed.includes('label: string'));
assert.equal(map.version,3);assert(map.sources.some(s=>s.endsWith('Client.tsx')));assert(map.sourcesContent.includes(code));
const bridge=require('../skills/impeccable/scripts/live-jsx-source.cjs');
const dir=path.join(root,'.impeccable/live/jsx-source-maps'),file=path.join(dir,fs.readdirSync(dir)[0]);
const manifest=JSON.parse(fs.readFileSync(file,'utf8')),record=Object.values(manifest.nodes).find(n=>n.tag==='span');
const event={id:'abcd1234',count:3,element:{tagName:'span',outerHTML:`<span data-design-live-source="${record.id}">Same</span>`},
  sourceLocator:{templateSource:{id:record.id,occurrences:1}}};
const receipt=bridge.locate(root,manifest,event);
const snippet=path.join(root,'.impeccable/live/chosen-template.txt');
fs.writeFileSync(snippet,'<span className="chosen">{label}</span>');
assert(bridge.validate(root,receipt,fs.readFileSync(snippet,'utf8')).ok);
const before=fs.readFileSync(file,'utf8');process.env.NODE_ENV='production';let production;
loader.call({mode:'production',callback:(err,result)=>production=result},code);
assert.equal(production,code);assert.equal(fs.readFileSync(file,'utf8'),before);
console.log('Turbopack Schema, Loader Subset, Maps And Text Snippet Passed');
