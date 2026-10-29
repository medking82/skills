// Development-only Babel provenance + read-only JSX/TSX source validation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {createRequire} = require('node:module');
const instances = require('./live-jsx-instances.cjs');
const modules = require('./live-jsx-modules.cjs');
const keyed = require('./live-jsx-keyed.cjs');
const MARKER = 'data-design-live-source';
const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const fail = reason => { throw new Error(reason); };
const ownsMarker=(html,name,value)=>html.match(/^<[a-z][a-z0-9:-]*\b(?:[^>"']|"[^"]*"|'[^']*')*>/i)?.[0].includes(` ${name}="${value}"`);
function sourceFile(root, file, readModule=false) {
  root = fs.realpathSync(root);
  const full = fs.realpathSync(path.resolve(root, file));
  const relative = path.relative(root, full);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)
      || relative.split(path.sep).some(p => ['dist','build','out','.next','node_modules','.git','.impeccable'].includes(p))
      || !(readModule?/\.(jsx|tsx|js|ts)$/:/\.(jsx|tsx)$/).test(full)) fail('not_true_jsx_source');
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
      this.recordedNodes = new WeakSet();
    },
    visitor: {
      Program: {enter(p,state) {
        const babel=createRequire(path.join(state.location.root,'package.json'))('@babel/core');
        state.components=instances.components(p.parent,babel.traverse,state.location.relative);
        const graph=modules.graph(state.location.root,state.location.full,babel,sourceFile);state.callPlans=new Map();state.processedCalls=new WeakSet();
        for(const node of graph.main.elements.values()) {
          try{const plan=graph.describe(node);state.callPlans.set(`${node.start}:${node.end}`,plan);}catch{} // Unsupported provenance stays unavailable.
        }
        if([...state.callPlans.values()].some(p=>p.loop)) {
          state.cloneIdentifier=p.scope.generateUidIdentifier('designLiveCloneElement');
          while(new RegExp(`\\b${state.cloneIdentifier.name}\\b`).test(state.file.code))state.cloneIdentifier=p.scope.generateUidIdentifier('designLiveCloneElement');
          const module=p.node.body.some(n=>n.type.startsWith('Import')||n.type.startsWith('Export'));
          if(module)p.unshiftContainer('body',t.importDeclaration([t.importSpecifier(state.cloneIdentifier,t.identifier('cloneElement'))],t.stringLiteral('react')));
          else p.unshiftContainer('body',t.variableDeclaration('const',[t.variableDeclarator(state.cloneIdentifier,t.memberExpression(t.callExpression(t.identifier('require'),[t.stringLiteral('react')]),t.identifier('cloneElement')))]));
        }
        for(const component of state.components.filter(c=>c.forwarded.length)) {
          if(component.root.openingElement.attributes.some(a=>a.type==='JSXAttribute'&&a.name.name===instances.MARKER))fail('reserved_instance_marker');
          component.alias=p.scope.generateUidIdentifier('designLiveInstance');
          component.parameter.properties.push(t.objectProperty(t.identifier(instances.PROP),component.alias));
          component.root.openingElement.attributes.push(t.jsxAttribute(t.jsxIdentifier(instances.MARKER),t.jsxExpressionContainer(component.alias)));
        }
      }},
      JSXElement(p, state) {
        const n=p.node, name=n.openingElement.name;
        const plan=state.callPlans.get(`${n.start}:${n.end}`);
        if(plan&&!state.processedCalls.has(n)) {
          state.processedCalls.add(n);
          if(n.openingElement.attributes.some(a=>a.type==='JSXAttribute'&&a.name.name===instances.PROP))fail('reserved_instance_prop');
          const {node,tree,code,...r}=plan;state.instanceRecords.push(r);
          if(plan.loop) {
            const element=p.scope.generateUidIdentifier('designLiveElement'),key=t.memberExpression(element,t.identifier('key'));
            const encoded=t.callExpression(t.identifier('encodeURIComponent'),[t.callExpression(t.memberExpression(t.identifier('JSON'),t.identifier('stringify')),[t.arrayExpression([t.stringLiteral('string'),key])])]);
            const marker=t.conditionalExpression(t.binaryExpression('===',t.unaryExpression('typeof',key),t.stringLiteral('string')),t.binaryExpression('+',t.stringLiteral(r.id+':'),encoded),t.unaryExpression('void',t.numericLiteral(0)));
            const clone=t.callExpression(state.cloneIdentifier,[element,t.objectExpression([t.objectProperty(plan.intrinsic?t.stringLiteral(instances.MARKER):t.identifier(instances.PROP),marker)])]);
            p.replaceWith(t.callExpression(t.arrowFunctionExpression([element],clone),[n]));
          } else n.openingElement.attributes.push(t.jsxAttribute(t.jsxIdentifier(instances.PROP),t.stringLiteral(r.id)));
        }
        if (!t.isJSXIdentifier(name) || !/^[a-z]/.test(name.name)) return;
        if(state.recordedNodes.has(n))return;
        if (n.openingElement.attributes.some(a => t.isJSXAttribute(a) && a.name.name === MARKER)) fail('reserved_source_marker');
        state.recordedNodes.add(n);
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
    parserOpts:{plugins:['jsx',...(/\.tsx?$/.test(file)?['typescript']:[])]}});
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
  const result={...matches[0],instances:{}};
  for(const m of fs.readdirSync(target).filter(n=>n.endsWith('.json')).map(n=>read(path.join(target,n)))) {
    if(m.root!==result.root||m.version!==1)fail('invalid_compiler_map');
    for(const [id,record] of Object.entries(m.instances||{})){if(result.instances[id])fail('compiler_instance_map_not_unique');result.instances[id]=record;}
  }
  return result;
}
function locate(root,map,event,scope='instance') {
  if(!['instance','template'].includes(scope))fail('unknown_edit_scope');
  if(!/^[a-f0-9]{8}$/.test(event.id) || !Number.isInteger(event.count) || event.count<1 || event.count>8) fail('invalid_session');
  let {r,location,code,tree}=mappedNode(root,map,event,scope),sourceKind='jsx',metadata={};
  if(scope==='instance'&&event.sourceLocator?.instanceSource) {
    const captured=event.sourceLocator.instanceSource;
    if(captured.rootSelected!==true)fail('select_component_root_for_instance');
    if(captured.occurrences!==1)fail('shared_callsite_source');
    const identity=modules.decodeIdentity(captured.id),call=map.instances?.[identity.id];
    if(!call||nodeId(call.file,call.start,call.end,call.hash)!==identity.id||call.templateId!==r.id
      ||!ownsMarker(event.element.outerHTML,instances.MARKER,captured.id))fail('instance_source_mismatch');
    const templateLocation=location;location=sourceFile(root,call.file);code=fs.readFileSync(location.full,'utf8');
    if(digest(code)!==call.hash)fail('source_changed_since_render');
    const babel=createRequire(path.join(location.root,'package.json'))('@babel/core'),graph=modules.graph(root,location.full,babel,sourceFile);
    const plan=graph.describe({start:call.start,end:call.end});
    const {node,tree:callTree,code:callCode,...record}=plan;
    if(JSON.stringify(record)!==JSON.stringify(call)||plan.templateFile!==templateLocation.full||Boolean(plan.loop)!==Boolean(identity.key))fail('instance_source_mismatch');
    if(plan.sharedOwner)fail('nested_component_instance_not_supported');
    tree=callTree;
    if(!plan.loop){assertSourceContext(tree,node);instances.instanceContract(node,code,plan.forwardedProps,staticExpression);}
    metadata={templateSourceId:r.id,instanceSourceId:call.id,runtimeInstanceId:captured.id,forwardedProps:plan.forwardedProps,
      projectRoot:plan.projectRoot,dependencies:plan.dependencies,graphVersion:1,...(identity.key?{loopKey:identity.key,keyExpression:plan.loop.keyExpression,
        callsiteStartUTF16:call.start,callsiteEndUTF16:call.end,...keyed.recipe(plan)}:{} )};
    r={...call,start:plan.replaceStart,end:plan.replaceEnd};sourceKind=plan.loop?'jsx-loop-instance':'jsx-instance';
  }
  const original=code.slice(r.start,r.end);
  const id=event.id, rendered=event.element.outerHTML;
  const wrapper=`<!-- impeccable-variants-start ${id} --><span data-impeccable-variants="${id}" data-impeccable-variant-count="${event.count}" style="display:contents"><style data-impeccable-css="${id}">span[data-impeccable-variants="${id}"]>span[data-impeccable-variant]{display:contents!important}</style><span data-impeccable-variant="original" style="display:contents">${rendered}</span><!-- Variants: insert below this line --></span><!-- impeccable-variants-end ${id} -->`;
  return {ok:true,sourceWritten:false,publishToSource:false,sourceKind,editScope:scope,
    scopeNotice:scope==='template'?'All uses of this source template, including unmounted instances; preview shows one example.'
      :sourceKind==='jsx-loop-instance'?'Only the selected stable item key at this callsite; other keys and shared template remain unchanged.'
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
function validatedPlan(root,receipt,node) {
  const babel=createRequire(path.join(root,'package.json'))('@babel/core'),graph=modules.graph(root,receipt.file,babel,sourceFile),plan=graph.describe(node);
  if(plan.sharedOwner||receipt.graphVersion!==1||receipt.instanceSourceId!==plan.id||receipt.templateSourceId!==plan.templateId
    ||receipt.projectRoot!==plan.projectRoot||JSON.stringify(receipt.dependencies)!==JSON.stringify(plan.dependencies)
    ||JSON.stringify(receipt.forwardedProps)!==JSON.stringify(plan.forwardedProps))fail('instance_contract_mismatch');
  const identity=modules.decodeIdentity(receipt.runtimeInstanceId);
  if(identity.id!==plan.id||JSON.stringify(identity.key)!==JSON.stringify(receipt.loopKey)||Boolean(plan.loop)!==Boolean(identity.key)
    ||(plan.loop&&receipt.keyExpression!==plan.loop.keyExpression))fail('instance_contract_mismatch');
  if(plan.replaceStart!==receipt.startUTF16||plan.replaceEnd!==receipt.endUTF16)fail('instance_contract_mismatch');
  if(plan.loop) {
    const recipe=keyed.recipe(plan);
    if(receipt.cloneName!==recipe.cloneName||receipt.elementType!==recipe.elementType||receipt.propsType!==recipe.propsType||JSON.stringify(receipt.additionalEdits)!==JSON.stringify(recipe.additionalEdits))fail('instance_contract_mismatch');
  }
  return plan;
}
function validate(root,receipt,replacement,mode='static',scope='instance',props) {
  if(!['static','structural'].includes(mode))fail('unknown_validation_mode');
  if(!['instance','template'].includes(scope)||(receipt.editScope||'instance')!==scope)fail('edit_scope_mismatch');
  const location=sourceFile(root,receipt.file),code=fs.readFileSync(location.full,'utf8');
  if(!['jsx','jsx-instance','jsx-loop-instance'].includes(receipt.sourceKind) || receipt.publishToSource!==false || digest(code)!==receipt.sourceSha256) fail('source_changed');
  const parse=parser(location.root,location.full),tree=parse(code),node=findElement(tree,receipt.callsiteStartUTF16??receipt.startUTF16,receipt.callsiteEndUTF16??receipt.endUTF16);
  if(!node || code.slice(receipt.startUTF16,receipt.endUTF16)!==receipt.original
    || [...code.slice(0,receipt.startUTF16)].length!==receipt.replaceStartOffset
    || [...code.slice(0,receipt.endUTF16)].length!==receipt.replaceEndOffset) fail('source_range_mismatch');
  if(receipt.sourceKind!=='jsx-loop-instance'&&(node.start!==receipt.startUTF16||node.end!==receipt.endUTF16))fail('source_range_mismatch');
  if(scope!=='template'&&receipt.sourceKind!=='jsx-loop-instance')assertSourceContext(tree,node);
  const ast=parse(replacement),next=ast.program.body[0]?.expression;
  if(receipt.sourceKind==='jsx-loop-instance') {
    if(scope!=='instance'||mode!=='static')fail('instance_contract_mismatch');
    const plan=validatedPlan(root,receipt,node),expected=keyed.generate(plan,receipt,props,staticExpression);
    if(replacement!==expected||ast.program.body.length!==1||next?.type!=='CallExpression')fail('keyed_specialization_mismatch');
    parse(keyed.apply(code,receipt,replacement));
    return {ok:true,validator:'babel-jsx-keyed-props-v1',receipt,replacementSha256:digest(replacement)};
  }
  if(ast.program.body.length!==1 || next?.type!=='JSXElement' || next.start!==0 || next.end!==replacement.length) fail('replacement_must_be_one_jsx_element');
  if(replacement.includes(MARKER) || replacement.includes(instances.MARKER)||replacement.includes(instances.PROP)|| /data-impeccable-|data-p-/.test(replacement)) fail('replacement_has_live_markers');
  const babel=createRequire(path.join(location.root,'package.json'))('@babel/core'),definitions=instances.components(tree,babel.traverse,location.relative);
  if(receipt.sourceKind==='jsx-instance') {
    if(scope!=='instance'||mode!=='static')fail('instance_contract_mismatch');
    const plan=validatedPlan(root,receipt,node);
    const compare=n=>instances.instanceContract(n,n===node?code:replacement,plan.forwardedProps,staticExpression);
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
module.exports.specialize=(root,receipt,props)=> {
  const replacement=keyed.generate(validatedPlan(root,receipt,{start:receipt.callsiteStartUTF16??receipt.startUTF16,end:receipt.callsiteEndUTF16??receipt.endUTF16}),receipt,props,staticExpression);
  validate(root,receipt,replacement,'static','instance',props);return {ok:true,sourceWritten:false,replacement};
};
if(require.main===module) {
  try {
    const [command,...rest]=process.argv.slice(2),args={};
    for(let i=0;i<rest.length;i+=2)args[rest[i].replace(/^--/,'')]=rest[i+1];
    const root=args.root||process.cwd();
    const json=file=>JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
    const event=command==='locate'?json(args.event):null;
    const result=command==='locate'?locate(root,readMap(args.map,event),event,args.scope||'instance')
      :command==='validate'?validate(root,json(args.receipt),fs.readFileSync(args.replacement,'utf8'),args.mode||'static',args.scope||'instance',args.props?json(args.props):undefined)
      :command==='specialize'?module.exports.specialize(root,json(args.receipt),json(args.props)):fail('unknown_command');
    process.stdout.write(JSON.stringify(result)+'\n');
  } catch(error) {console.log(JSON.stringify({ok:false,sourceWritten:false,error:error.message}));process.exitCode=1;}
}
