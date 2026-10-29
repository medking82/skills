// Development-only Babel provenance + read-only JSX/TSX source validation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {createRequire} = require('node:module');
const MARKER = 'data-design-live-source';
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const fail = reason => { throw new Error(reason); };
function sourceFile(root, file) {
  root = fs.realpathSync(root);
  const full = fs.realpathSync(path.resolve(root, file));
  const relative = path.relative(root, full);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)
      || relative.split(path.sep).some(p => ['dist','build','out','.next','node_modules','.git','.impeccable'].includes(p))
      || !/\.(jsx|tsx)$/.test(full)) fail('not_true_jsx_source');
  return {root, full, relative:relative.split(path.sep).join('/')};
}
function nodeId(file, start, end, hash) { return digest(`${file}:${start}:${end}:${hash}`).slice(0,24); }
function plugin({types:t}, options={}) {
  if (options.development !== true || process.env.NODE_ENV === 'production') return {};
  return {
    pre(file) {
      this.location = sourceFile(options.root, file.opts.filename);
      this.sourceHash = digest(file.code);
      if (digest(fs.readFileSync(this.location.full)) !== this.sourceHash) fail('compiler_input_not_original_source');
      this.records = [];
    },
    visitor: {
      JSXElement(p, state) {
        const n=p.node, name=n.openingElement.name;
        if (!t.isJSXIdentifier(name) || !/^[a-z]/.test(name.name)) return;
        if (n.openingElement.attributes.some(a => t.isJSXAttribute(a) && a.name.name === MARKER)) fail('reserved_source_marker');
        const r={file:state.location.relative,start:n.start,end:n.end,tag:name.name,hash:state.sourceHash};
        r.id=nodeId(r.file,r.start,r.end,r.hash);
        state.records.push(r);
        n.openingElement.attributes.push(t.jsxAttribute(t.jsxIdentifier(MARKER),t.stringLiteral(r.id)));
      }
    },
    post() {
      const target=path.join(this.location.root,'.impeccable/live/jsx-source-maps',digest(this.location.relative).slice(0,24)+'.json');
      const map={version:1,root:this.location.root,nodes:{}};
      for(const r of this.records) map.nodes[r.id]=r;
      fs.mkdirSync(path.dirname(target),{recursive:true});
      const temporary=target+'.'+process.pid+'.tmp';
      fs.writeFileSync(temporary,JSON.stringify(map));fs.renameSync(temporary,target);
    }
  };
}
function parser(root,file) {
  const babel=createRequire(path.join(root,'package.json'))('@babel/core');
  return code=>babel.parseSync(code,{filename:file,configFile:false,babelrc:false,
    parserOpts:{plugins:['jsx',...(file.endsWith('.tsx')?['typescript']:[])]}});
}
function findElement(tree,start,end) {
  if(!tree || typeof tree!=='object') return null;
  if(tree.type==='JSXElement' && tree.start===start && tree.end===end) return tree;
  for(const [key,value] of Object.entries(tree)) {
    if(['loc','extra','comments','tokens'].includes(key)) continue;
    for(const n of Array.isArray(value)?value:[value]) {
      const result=findElement(n,start,end);if(result)return result;
    }
  }
  return null;
}
function mappedNode(root,map,event) {
  root=fs.realpathSync(root);
  const captured=event.sourceLocator?.templateSource;
  if(!captured || !/^[a-f0-9]{24}$/.test(captured.id)) fail('missing_compiler_provenance');
  if(captured.occurrences!==1) fail('shared_template_source');
  const r=map.nodes?.[captured.id];
  if(map.version!==1 || map.root!==root || !r || nodeId(r.file,r.start,r.end,r.hash)!==captured.id) fail('invalid_compiler_map');
  const location=sourceFile(root,r.file), code=fs.readFileSync(location.full,'utf8');
  if(digest(code)!==r.hash) fail('source_changed_since_render');
  const node=findElement(parser(root,location.full)(code),r.start,r.end);
  if(!node || node.openingElement.name.type!=='JSXIdentifier' || node.openingElement.name.name!==r.tag
     || event.element.tagName!==r.tag || !event.element.outerHTML.includes(`${MARKER}="${captured.id}"`)) fail('render_source_mismatch');
  return {r,location,code,node};
}
function readMap(target,event) {
  const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
  if(!fs.statSync(target).isDirectory())return read(target);
  const id=event.sourceLocator?.templateSource?.id;
  const matches=fs.readdirSync(target).filter(n=>n.endsWith('.json')).map(n=>read(path.join(target,n))).filter(m=>m.nodes?.[id]);
  if(matches.length!==1)fail('compiler_map_not_unique');
  return matches[0];
}
function locate(root,map,event) {
  if(!/^[a-f0-9]{8}$/.test(event.id) || !Number.isInteger(event.count) || event.count<1 || event.count>8) fail('invalid_session');
  const {r,location,code}=mappedNode(root,map,event), original=code.slice(r.start,r.end);
  const id=event.id, rendered=event.element.outerHTML;
  const wrapper=`<!-- impeccable-variants-start ${id} --><span data-impeccable-variants="${id}" data-impeccable-variant-count="${event.count}" style="display:contents"><style data-impeccable-css="${id}">span[data-impeccable-variants="${id}"]>span[data-impeccable-variant]{display:contents!important}</style><span data-impeccable-variant="original" style="display:contents">${rendered}</span><!-- Variants: insert below this line --></span><!-- impeccable-variants-end ${id} -->`;
  return {ok:true,sourceWritten:false,publishToSource:false,sourceKind:'jsx',sessionId:id,file:location.full,
    sourceSha256:r.hash,replaceStartOffset:[...code.slice(0,r.start)].length,replaceEndOffset:[...code.slice(0,r.end)].length,
    startUTF16:r.start,endUTF16:r.end,original,wrapperBlock:wrapper,renderedOriginal:rendered,
    offsetUnit:'Python Unicode characters'};
}
function staticExpression(n) {
  if(!n)return false;
  if(['StringLiteral','NumericLiteral','BooleanLiteral','NullLiteral'].includes(n.type))return true;
  if(n.type==='ObjectExpression')return n.properties.every(p=>p.type==='ObjectProperty'&&!p.computed&&staticExpression(p.value));
  if(n.type==='ArrayExpression')return n.elements.every(staticExpression);
  return false;
}
function contract(n,code) {
  if(n.type==='JSXText') return {kind:'text'};
  if(n.type==='JSXExpressionContainer' || n.type==='JSXSpreadChild') return {kind:n.type,raw:code.slice(n.start,n.end)};
  if(n.type==='JSXFragment') return {kind:n.type,children:n.children.map(c=>contract(c,code))};
  if(n.type!=='JSXElement') fail('unsupported_jsx_structure');
  const opening=n.openingElement;
  const names=opening.attributes.filter(a=>a.type==='JSXAttribute').map(a=>a.name.name);
  if(new Set(names).size!==names.length)fail('duplicate_jsx_attribute');
  const safe=name=>/^(className|style|title|id|role|type|disabled|tabIndex|href|src|alt|aria-.+|data-.+)$/.test(name);
  const dynamic=opening.attributes.filter(a=>a.type==='JSXSpreadAttribute' || !safe(a.name?.name||'')
    || (a.value?.type==='JSXExpressionContainer'&&!staticExpression(a.value.expression)))
    .map(a=>code.slice(a.start,a.end));
  return {kind:n.type,name:code.slice(opening.name.start,opening.name.end),dynamic,children:n.children.map(c=>contract(c,code))};
}
function validate(root,receipt,replacement) {
  const location=sourceFile(root,receipt.file),code=fs.readFileSync(location.full,'utf8');
  if(receipt.sourceKind!=='jsx' || receipt.publishToSource!==false || digest(code)!==receipt.sourceSha256) fail('source_changed');
  const parse=parser(location.root,location.full), node=findElement(parse(code),receipt.startUTF16,receipt.endUTF16);
  if(!node || code.slice(node.start,node.end)!==receipt.original
    || [...code.slice(0,node.start)].length!==receipt.replaceStartOffset
    || [...code.slice(0,node.end)].length!==receipt.replaceEndOffset) fail('source_range_mismatch');
  const ast=parse(replacement),next=ast.program.body[0]?.expression;
  if(ast.program.body.length!==1 || next?.type!=='JSXElement' || next.start!==0 || next.end!==replacement.length) fail('replacement_must_be_one_jsx_element');
  if(replacement.includes(MARKER) || /data-impeccable-|data-p-/.test(replacement)) fail('replacement_has_live_markers');
  if(JSON.stringify(contract(node,code))!==JSON.stringify(contract(next,replacement))) fail('template_bindings_or_structure_changed');
  parse(code.slice(0,node.start)+replacement+code.slice(node.end));
  return {ok:true,validator:'babel-jsx-static-edits-v1',receipt,replacementSha256:digest(replacement)};
}
module.exports=plugin;
Object.assign(module.exports,{locate,validate,sourceFile,readMap});
if(require.main===module) {
  try {
    const [command,...rest]=process.argv.slice(2),args={};
    for(let i=0;i<rest.length;i+=2)args[rest[i].replace(/^--/,'')]=rest[i+1];
    const root=args.root||process.cwd();
    const json=file=>JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
    const event=command==='locate'?json(args.event):null;
    const result=command==='locate'?locate(root,readMap(args.map,event),event)
      :command==='validate'?validate(root,json(args.receipt),fs.readFileSync(args.replacement,'utf8')):fail('unknown_command');
    process.stdout.write(JSON.stringify(result)+'\n');
  } catch(error) {console.log(JSON.stringify({ok:false,sourceWritten:false,error:error.message}));process.exitCode=1;}
}
