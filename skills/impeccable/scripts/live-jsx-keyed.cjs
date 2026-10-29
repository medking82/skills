// Construct the original element first, then override only the selected React key.
const fail=message=>{throw Error(message);};
function recipe(plan) {
  const {tree,code}=plan,tsx=plan.file.endsWith('.tsx');
  const typeNames=new Set();
  function scan(n) {if(!n||typeof n!=='object')return;if(['TSTypeAliasDeclaration','TSInterfaceDeclaration','TSEnumDeclaration','TSModuleDeclaration','TSImportEqualsDeclaration'].includes(n.type))typeNames.add(n.id?.name);
    if(n.type==='TSTypeParameter')typeNames.add(n.name);for(const [k,v] of Object.entries(n))if(!['loc','extra','comments'].includes(k))for(const child of Array.isArray(v)?v:[v])scan(child);}
  scan(tree);
  const typeImports=tree.program.body.filter(n=>n.type==='ImportDeclaration'&&n.source.value==='react').flatMap(n=>n.specifiers)
    .filter(s=>s.type==='ImportSpecifier'&&!typeNames.has(s.local.name));
  const existing=name=>['ReactElement','ComponentProps'].includes(name)?typeImports.find(s=>s.imported.name===name)?.local.name
    :plan.reactImports.find(s=>s.imported===name&&s.kind==='value')?.local;
  const unique=base=>{let name=base,n=0;while(new RegExp('\\b'+name+'\\b').test(code))name=base+(++n);return name;};
  const cloneName=existing('cloneElement')||unique('__designLiveCloneElement'),elementType=tsx?(existing('ReactElement')||unique('__designLiveElement')):null;
  const propsType=tsx?(existing('ComponentProps')||unique('__designLiveComponentProps')):null;
  const additions=[];if(!existing('cloneElement'))additions.push('cloneElement as '+cloneName);
  if(tsx&&!existing('ReactElement'))additions.push('type ReactElement as '+elementType);
  if(tsx&&!existing('ComponentProps'))additions.push('type ComponentProps as '+propsType);
  const position=tree.program.directives.at(-1)?.end||tree.program.interpreter?.end||(code.startsWith('\uFEFF')?1:0);
  const offset=[...code.slice(0,position)].length;
  return {cloneName,elementType,propsType,additionalEdits:additions.length?[{start:offset,end:offset,startUTF16:position,endUTF16:position,original:'',replacement:'\nimport { '+additions.join(', ')+' } from "react";\n'}]:[]};
}
function generate(plan,receipt,props) {
  if(!plan.loop||!receipt.loopKey)fail('keyed_receipt_required');
  if(!props||typeof props!=='object'||Array.isArray(props)||!Object.keys(props).length)fail('presentation_props_required');
  for(const [name,value] of Object.entries(props)) {
    if(!plan.forwardedProps.includes(name))fail('unverified_presentation_prop');
    if(name==='style') {
      if(!value||typeof value!=='object'||Array.isArray(value)||Object.entries(value).some(([k,v])=>!/^[-a-zA-Z0-9_]+$/.test(k)||!['string','number'].includes(typeof v)||(typeof v==='number'&&!Number.isFinite(v))))fail('static_style_object_required');
    } else if(typeof value!=='string')fail('static_string_prop_required');
  }
  let name='__designLiveElementValue',n=0;while(new RegExp('\\b'+name+'\\b').test(plan.code))name='__designLiveElementValue'+(++n);
  const r=recipe(plan),original=plan.code.slice(plan.replaceStart,plan.replaceEnd),key=JSON.stringify(String(receipt.loopKey.value));
  const ordered=Object.fromEntries(Object.keys(props).sort().map(k=>[k,props[k]]));
  const type=plan.file.endsWith('.tsx')?': '+r.elementType+'<'+r.propsType+'<'+(plan.intrinsic?JSON.stringify(plan.tag):'typeof '+plan.tag)+'>>':'';
  return '(('+name+type+') => '+name+'.key === '+key+' ? '+r.cloneName+'('+name+', '+JSON.stringify(ordered)+') : '+name+')('+original+')';
}
function apply(source,receipt,replacement) {
  const edits=[{start:receipt.startUTF16,end:receipt.endUTF16,original:receipt.original,replacement},...(receipt.additionalEdits||[]).map(e=>({...e,start:e.startUTF16,end:e.endUTF16}))];
  let result=source;for(const e of edits.sort((a,b)=>b.start-a.start)){if(source.slice(e.start,e.end)!==e.original)fail('source_range_mismatch');result=result.slice(0,e.start)+e.replacement+result.slice(e.end);}return result;
}
module.exports={generate,recipe,apply};
