// Development-only Babel provenance + read-only JSX/TSX source validation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {createRequire} = require('node:module');
const instances = require('./live-jsx-instances.cjs');
const MARKER = 'data-design-live-source';
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const fail = reason => { throw new Error(reason); };
const ownsMarker=(html,name,value)=>html.match(/^<[a-z][a-z0-9:-]*\b(?:[^>"']|"[^"]*"|'[^']*')*>/i)?.[0].includes(` ${name}="${value}"`);
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
      this.instanceRecords = [];
    },
    visitor: {
      Program: {enter(p,state) {
        state.components=instances.components(p.parent,createRequire(path.join(state.location.root,'package.json'))('@babel/core').traverse,state.location.relative);
        for(const component of state.components.filter(c=>c.calls.length&&c.forwarded.length)) {
          if(component.root.openingElement.attributes.some(a=>a.type==='JSXAttribute'&&a.name.name===instances.MARKER))fail('reserved_instance_marker');
          component.alias=p.scope.generateUidIdentifier('designLiveInstance');
          component.parameter.properties.push(t.objectProperty(t.identifier(instances.PROP),component.alias));
          component.root.openingElement.attributes.push(t.jsxAttribute(t.jsxIdentifier(instances.MARKER),t.jsxExpressionContainer(component.alias)));
        }
      }},
      JSXElement(p, state) {
        const n=p.node, name=n.openingElement.name;
        const component=state.components.find(c=>c.alias&&c.calls.includes(n));
        if(component) {
          if(n.openingElement.attributes.some(a=>a.type==='JSXAttribute'&&a.name.name===instances.PROP))fail('reserved_instance_prop');
          const r={file:state.location.relative,start:n.start,end:n.end,tag:name.name,hash:state.sourceHash,
            templateId:nodeId(state.location.relative,component.root.start,component.root.end,state.sourceHash)};
          r.id=nodeId(r.file,r.start,r.end,r.hash);state.instanceRecords.push(r);
          n.openingElement.attributes.push(t.jsxAttribute(t.jsxIdentifier(instances.PROP),t.stringLiteral(r.id)));
        }
        if (!t.isJSXIdentifier(name) || !/^[a-z]/.test(name.name)) return;
        if (n.openingElement.attributes.some(a => t.isJSXAttribute(a) && a.name.name === MARKER)) fail('reserved_source_marker');
        const r={file:state.location.relative,start:n.start,end:n.end,tag:name.name,hash:state.sourceHash};
        if(state.components.some(c=>c.reusable&&p.findParent(a=>a.node===c.fn)))r.componentTemplate=true;
        r.id=nodeId(r.file,r.start,r.end,r.hash);
        state.records.push(r);
        n.openingElement.attributes.push(t.jsxAttribute(t.jsxIdentifier(MARKER),t.stringLiteral(r.id)));
      }
    },
    post() {
      const target=path.join(this.location.root,'.impeccable/live/jsx-source-maps',digest(this.location.relative).slice(0,24)+'.json');
      const map={version:1,root:this.location.root,nodes:{},instances:{}};
      for(const r of this.records) map.nodes[r.id]=r;
      for(const r of this.instanceRecords)map.instances[r.id]=r;
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
function assertSourceContext(tree,target) {
  function visit(node,ancestors) {
    if(!node || typeof node!=='object')return false;
    if(node===target) {
      const functions=ancestors.filter(n=>/^(ArrowFunctionExpression|FunctionExpression|FunctionDeclaration|ObjectMethod|ClassMethod)$/.test(n.type));
      if(functions.length>1 || functions.some(n=>ancestors.some(p=>
        /^(CallExpression|OptionalCallExpression|NewExpression)$/.test(p.type)&&p.arguments.includes(n))))fail('callback_template_source');
      return true;
    }
    for(const [key,value] of Object.entries(node)) {
      if(['loc','extra','comments','tokens'].includes(key))continue;
      for(const child of Array.isArray(value)?value:[value])if(visit(child,[...ancestors,node]))return true;
    }
    return false;
  }
  visit(tree,[]);
}
function mappedNode(root,map,event,scope) {
  root=fs.realpathSync(root);
  const captured=event.sourceLocator?.templateSource;
  if(!captured || !/^[a-f0-9]{24}$/.test(captured.id)) fail('missing_compiler_provenance');
  if(!Number.isInteger(captured.occurrences)||captured.occurrences<1)fail('invalid_template_occurrences');
  const r=map.nodes?.[captured.id];
  if(map.version!==1 || map.root!==root || !r || nodeId(r.file,r.start,r.end,r.hash)!==captured.id) fail('invalid_compiler_map');
  const location=sourceFile(root,r.file), code=fs.readFileSync(location.full,'utf8');
  if(digest(code)!==r.hash) fail('source_changed_since_render');
  const tree=parser(root,location.full)(code),node=findElement(tree,r.start,r.end);
  if(!node || node.openingElement.name.type!=='JSXIdentifier' || node.openingElement.name.name!==r.tag
     || event.element.tagName!==r.tag || !ownsMarker(event.element.outerHTML,MARKER,captured.id)) fail('render_source_mismatch');
  if(scope!=='template'&&!event.sourceLocator?.instanceSource) {
    if(captured.occurrences!==1)fail('shared_template_source');
    assertSourceContext(tree,node);
    if(r.componentTemplate)fail('missing_instance_provenance');
  }
  return {r,location,code,node,tree};
}
function readMap(target,event) {
  const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
  if(!fs.statSync(target).isDirectory())return read(target);
  const id=event.sourceLocator?.templateSource?.id;
  const matches=fs.readdirSync(target).filter(n=>n.endsWith('.json')).map(n=>read(path.join(target,n))).filter(m=>m.nodes?.[id]);
  if(matches.length!==1)fail('compiler_map_not_unique');
  return matches[0];
}
function locate(root,map,event,scope='instance') {
  if(!['instance','template'].includes(scope))fail('unknown_edit_scope');
  if(!/^[a-f0-9]{8}$/.test(event.id) || !Number.isInteger(event.count) || event.count<1 || event.count>8) fail('invalid_session');
  let {r,location,code,tree}=mappedNode(root,map,event,scope),sourceKind='jsx',metadata={};
  if(scope==='instance'&&event.sourceLocator?.instanceSource) {
    const captured=event.sourceLocator.instanceSource;
    if(captured.rootSelected!==true)fail('select_component_root_for_instance');
    if(captured.occurrences!==1)fail('shared_callsite_source');
    const call=map.instances?.[captured.id];
    if(!call||nodeId(call.file,call.start,call.end,call.hash)!==captured.id||call.hash!==r.hash||call.file!==r.file||call.templateId!==r.id
      ||!ownsMarker(event.element.outerHTML,instances.MARKER,captured.id))fail('instance_source_mismatch');
    const babel=createRequire(path.join(location.root,'package.json'))('@babel/core');
    const callNode=findElement(tree,call.start,call.end),definitions=instances.components(tree,babel.traverse,location.relative);
    const definition=definitions.find(c=>c.calls.includes(callNode)&&c.forwarded.length);
    if(!definition||definition.root.start!==r.start||definition.root.end!==r.end)fail('instance_source_mismatch');
    assertSourceContext(tree,callNode);
    if(instances.owner(tree,callNode,definitions,babel.traverse))fail('nested_component_instance_not_supported');
    instances.instanceContract(callNode,code,definition.forwarded,staticExpression);
    metadata={templateSourceId:r.id,instanceSourceId:call.id,forwardedProps:definition.forwarded};r=call;sourceKind='jsx-instance';
  }
  const original=code.slice(r.start,r.end);
  const id=event.id, rendered=event.element.outerHTML;
  const wrapper=`<!-- impeccable-variants-start ${id} --><span data-impeccable-variants="${id}" data-impeccable-variant-count="${event.count}" style="display:contents"><style data-impeccable-css="${id}">span[data-impeccable-variants="${id}"]>span[data-impeccable-variant]{display:contents!important}</style><span data-impeccable-variant="original" style="display:contents">${rendered}</span><!-- Variants: insert below this line --></span><!-- impeccable-variants-end ${id} -->`;
  return {ok:true,sourceWritten:false,publishToSource:false,sourceKind,editScope:scope,
    scopeNotice:scope==='template'?'All uses of this source template, including unmounted instances; preview shows one example.'
      :sourceKind==='jsx-instance'?'Only this unique static component callsite; shared template remains unchanged.':'Only the selected source range.',
    observedInstances:event.sourceLocator.templateSource.occurrences,...metadata,sessionId:id,file:location.full,
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
  // A static override after a spread can change protected runtime props.
  if(opening.attributes.some(a=>a.type==='JSXSpreadAttribute'))return {kind:n.type,name:code.slice(opening.name.start,opening.name.end),dynamic:opening.attributes.map(a=>code.slice(a.start,a.end)),children:n.children.map(c=>contract(c,code))};
  return {kind:n.type,name:code.slice(opening.name.start,opening.name.end),dynamic,children:n.children.map(c=>contract(c,code))};
}
const LAYOUT_TAGS=new Set('div span section article aside header footer main nav h1 h2 h3 h4 h5 h6 p strong em small b i u s br hr img picture source figure figcaption'.split(' '));
function structuralContract(node,code) {
  const tokens=[];
  function expression(n) {
    const islands=[];
    function collect(value) {
      if(!value || typeof value!=='object')return;
      if(value.type==='JSXElement' || value.type==='JSXFragment'){islands.push(value);return;}
      for(const [key,child] of Object.entries(value)) {
        if(['loc','extra','comments','tokens'].includes(key))continue;
        for(const x of Array.isArray(child)?child:[child])collect(x);
      }
    }
    collect(n.expression||n.argument);
    islands.sort((a,b)=>a.start-b.start);
    let cursor=n.start;const parts=[];
    for(const island of islands){parts.push(code.slice(cursor,island.start));parts.push(structuralContract(island,code));cursor=island.end;}
    parts.push(code.slice(cursor,n.end));
    return {kind:n.type,parts};
  }
  function visit(n) {
    if(n.type==='JSXText')return;
    if(n.type==='JSXExpressionContainer'||n.type==='JSXSpreadChild'){tokens.push(expression(n));return;}
    if(n.type==='JSXFragment'){n.children.forEach(visit);return;}
    if(n.type!=='JSXElement')fail('unsupported_jsx_structure');
    const c=contract(n,code),protectedNode=c.dynamic.length>0||!LAYOUT_TAGS.has(c.name);
    if(!/^[a-z][a-z0-9]*$/.test(c.name)) {tokens.push({kind:'component',raw:code.slice(n.start,n.end)});return;}
    if(protectedNode)tokens.push({kind:'open',name:c.name,dynamic:c.dynamic});
    n.children.forEach(visit);
    if(protectedNode)tokens.push({kind:'close',name:c.name});
  }
  // A keyed/ref root must stay at the expression/selection boundary, not below a new wrapper.
  const boundary=node.openingElement?.attributes.filter(a=>a.type==='JSXAttribute'&&['key','ref'].includes(a.name.name)).map(a=>code.slice(a.start,a.end))||[];
  visit(node);return {boundary,tokens};
}
function validate(root,receipt,replacement,mode='static',scope='instance') {
  if(!['static','structural'].includes(mode))fail('unknown_validation_mode');
  if(!['instance','template'].includes(scope)||(receipt.editScope||'instance')!==scope)fail('edit_scope_mismatch');
  const location=sourceFile(root,receipt.file),code=fs.readFileSync(location.full,'utf8');
  if(!['jsx','jsx-instance'].includes(receipt.sourceKind) || receipt.publishToSource!==false || digest(code)!==receipt.sourceSha256) fail('source_changed');
  const parse=parser(location.root,location.full),tree=parse(code),node=findElement(tree,receipt.startUTF16,receipt.endUTF16);
  if(!node || code.slice(node.start,node.end)!==receipt.original
    || [...code.slice(0,node.start)].length!==receipt.replaceStartOffset
    || [...code.slice(0,node.end)].length!==receipt.replaceEndOffset) fail('source_range_mismatch');
  if(scope!=='template')assertSourceContext(tree,node);
  const ast=parse(replacement),next=ast.program.body[0]?.expression;
  if(ast.program.body.length!==1 || next?.type!=='JSXElement' || next.start!==0 || next.end!==replacement.length) fail('replacement_must_be_one_jsx_element');
  if(replacement.includes(MARKER) || replacement.includes(instances.MARKER)||replacement.includes(instances.PROP)|| /data-impeccable-|data-p-/.test(replacement)) fail('replacement_has_live_markers');
  const babel=createRequire(path.join(location.root,'package.json'))('@babel/core'),definitions=instances.components(tree,babel.traverse,location.relative);
  if(receipt.sourceKind==='jsx-instance') {
    const definition=definitions.find(c=>c.calls.includes(node)&&c.forwarded.length);
    if(scope!=='instance'||mode!=='static'||!definition||receipt.instanceSourceId!==nodeId(location.relative,node.start,node.end,receipt.sourceSha256)
      ||receipt.templateSourceId!==nodeId(location.relative,definition.root.start,definition.root.end,receipt.sourceSha256)
      ||JSON.stringify(receipt.forwardedProps)!==JSON.stringify(definition.forwarded))fail('instance_contract_mismatch');
    if(instances.owner(tree,node,definitions,babel.traverse))fail('nested_component_instance_not_supported');
    const compare=n=>instances.instanceContract(n,n===node?code:replacement,definition.forwarded,staticExpression);
    if(JSON.stringify(compare(node))!==JSON.stringify(compare(next)))fail('instance_bindings_changed');
    parse(code.slice(0,node.start)+replacement+code.slice(node.end));
    return {ok:true,validator:'babel-jsx-instance-props-v1',receipt,replacementSha256:digest(replacement)};
  }
  if(scope!=='template'&&instances.owner(tree,node,definitions,babel.traverse))fail('missing_instance_provenance');
  const compare=mode==='structural'?structuralContract:contract;
  if(JSON.stringify(compare(node,code))!==JSON.stringify(compare(next,replacement))) fail('template_bindings_or_structure_changed');
  parse(code.slice(0,node.start)+replacement+code.slice(node.end));
  const validator=scope==='template'?`babel-jsx-template-${mode}-edits-v1`:mode==='structural'?'babel-jsx-structural-edits-v1':'babel-jsx-static-edits-v1';
  return {ok:true,validator,receipt,replacementSha256:digest(replacement)};
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
    const result=command==='locate'?locate(root,readMap(args.map,event),event,args.scope||'instance')
      :command==='validate'?validate(root,json(args.receipt),fs.readFileSync(args.replacement,'utf8'),args.mode||'static',args.scope||'instance'):fail('unknown_command');
    process.stdout.write(JSON.stringify(result)+'\n');
  } catch(error) {console.log(JSON.stringify({ok:false,sourceWritten:false,error:error.message}));process.exitCode=1;}
}
