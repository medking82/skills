// Read-only lexical module/HOC resolution. Never load or execute project modules.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const instances=require('./live-jsx-instances.cjs');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const id=(c,n)=>hash(`${c.relative}:${n.start}:${n.end}:${c.hash}`).slice(0,24);
const fail=s=>{throw Error(s);};
const directReturn=fn=>fn?.body?.type==='BlockStatement'?(fn.body.body.length===1&&fn.body.body[0].type==='ReturnStatement'?fn.body.body[0].argument:null):fn?.body;
function graph(root,file,babel,sourceFile) {
  const cache=new Map();let used=new Set(),active=new Set();
  function load(file) {
    const location=sourceFile(root,file,true);
    if(!cache.has(location.full)) {
      if(cache.size>=64)fail('module_graph_limit');
      const code=fs.readFileSync(location.full,'utf8'),tree=babel.parseSync(code,{filename:location.full,configFile:false,babelrc:false,
        parserOpts:{plugins:['jsx',...(/\.tsx?$/.test(location.full)?['typescript']:[])]}}),paths=new WeakMap(),elements=new Map();
      babel.traverse(tree,{enter(p){paths.set(p.node,p);if(p.isJSXElement())elements.set(`${p.node.start}:${p.node.end}`,p.node);}});
      cache.set(location.full,{...location,code,tree,paths,elements,hash:hash(code),definitions:instances.components(tree,babel.traverse,location.relative)});
    }
    const ctx=cache.get(location.full);used.add(ctx);return ctx;
  }
  function guard(key,fn) {if(active.has(key)||active.size>32)fail('cyclic_or_deep_module_graph');active.add(key);try{return fn();}finally{active.delete(key);}}
  function dependency(ctx,specifier) {
    if(!specifier.startsWith('.'))fail('unsupported_module_specifier');
    const base=path.resolve(path.dirname(ctx.full),specifier),candidates=path.extname(base)?[base]:
      ['.tsx','.jsx','.ts','.js','/index.tsx','/index.jsx','/index.ts','/index.js'].map(ext=>base+ext);
    const found=candidates.filter(f=>fs.existsSync(f)&&fs.statSync(f).isFile());
    if(found.length!==1)fail('module_resolution_not_unique');
    return load(found[0]);
  }
  function binding(ctx,name,node) {
    used.add(ctx);const b=ctx.paths.get(node)?.scope.getBinding(name);
    if(!b?.constant)fail('unstable_component_binding');
    return b;
  }
  function resolveBinding(ctx,b) {
    return guard(`${ctx.full}:binding:${b.identifier.start}`,()=>{
      const p=b.path,n=p.node;
      const definition=ctx.definitions.find(d=>d.binding===n&&d.forwarded.length);
      if(definition)return {ctx,definition};
      if(n.type==='VariableDeclarator')return expression(ctx,n.init);
      if(n.type==='FunctionDeclaration')return {ctx,factory:n};
      if(['ImportSpecifier','ImportDefaultSpecifier'].includes(n.type))return exported(dependency(ctx,p.parent.source.value),n.type==='ImportDefaultSpecifier'?'default':n.imported.name);
      fail('unresolved_component_binding');
    });
  }
  function exported(ctx,name) {
    used.add(ctx);return guard(`${ctx.full}:export:${name}`,()=>{
      for(const statement of ctx.tree.program.body) {
        if(statement.type==='ExportDefaultDeclaration'&&name==='default')return expression(ctx,statement.declaration);
        if(statement.type!=='ExportNamedDeclaration')continue;
        const d=statement.declaration;
        if(d?.id?.name===name)return expression(ctx,d);
        if(d?.type==='VariableDeclaration') {const v=d.declarations.find(v=>v.id.name===name);if(v)return resolveBinding(ctx,binding(ctx,name,v));}
        const s=statement.specifiers.find(s=>(s.exported.name||s.exported.value)===name);
        if(s)return statement.source?exported(dependency(ctx,statement.source.value),s.local.name):resolveBinding(ctx,binding(ctx,s.local.name,s));
      }
      const matches=[];
      for(const s of ctx.tree.program.body.filter(s=>s.type==='ExportAllDeclaration')) {
        try{matches.push(exported(dependency(ctx,s.source.value),name));}catch(e){if(e.message!=='missing_component_export')throw e;}
      }
      if(matches.length!==1)fail(matches.length?'ambiguous_component_export':'missing_component_export');
      return matches[0];
    });
  }
  function factoryTarget(ctx,fn,arg) {
    if(fn.params?.length!==1||fn.params[0].type!=='Identifier')fail('unsupported_hoc_contract');
    const value=directReturn(fn);
    if(value?.type==='Identifier'&&ctx.paths.get(value).scope.getBinding(value.name)?.identifier===fn.params[0])return arg;
    if(!['ArrowFunctionExpression','FunctionExpression'].includes(value?.type)||value.params.length!==1||value.params[0].type!=='Identifier')fail('unsupported_hoc_contract');
    const rendered=directReturn(value);
    if(rendered?.type!=='JSXElement'||rendered.openingElement.name.type!=='JSXIdentifier'
      ||rendered.children.some(n=>n.type!=='JSXText'||n.value.trim())||rendered.openingElement.attributes.length!==1)fail('unsupported_hoc_contract');
    const elementPath=ctx.paths.get(rendered),spread=rendered.openingElement.attributes[0];
    if(elementPath.scope.getBinding(rendered.openingElement.name.name)?.identifier!==fn.params[0]
      ||spread.type!=='JSXSpreadAttribute'||spread.argument.type!=='Identifier'
      ||elementPath.scope.getBinding(spread.argument.name)?.identifier!==value.params[0])fail('unsupported_hoc_contract');
    return arg;
  }
  function expression(ctx,node) {
    used.add(ctx);if(!node)fail('missing_component_expression');
    if(node.type==='Identifier'||node.type==='JSXIdentifier')return resolveBinding(ctx,binding(ctx,node.name,node));
    if(['MemberExpression','JSXMemberExpression'].includes(node.type)&&!node.computed&&node.object.type.endsWith('Identifier')) {
      const b=binding(ctx,node.object.name,node);
      if(b.path.node.type==='ImportNamespaceSpecifier')return exported(dependency(ctx,b.path.parent.source.value),node.property.name);
      fail('unsupported_component_member');
    }
    const own=ctx.definitions.find(d=>d.fn===node&&d.forwarded.length);
    if(own) {
      const b=ctx.paths.get(node).scope.getBinding(own.name);
      if(b&&b.path.node===own.binding&&!b.constant)fail('unstable_component_binding');
      return {ctx,definition:own};
    }
    if(['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(node.type))return {ctx,factory:node};
    if(node.type==='CallExpression') {
      const wrapper=instances.reactWrapper(node,ctx.paths.get(node).scope);
      if(wrapper) {
        const target=expression(ctx,node.arguments[0]);
        if(target.definition)return target;
        const definition=ctx.definitions.find(d=>d.fn===node.arguments[0]&&d.forwarded.length);
        if(definition)return {ctx,definition};
        fail('unsupported_react_render_contract');
      }
      if(node.arguments.length!==1)fail('unsupported_hoc_contract');
      const hoc=expression(ctx,node.callee),arg=expression(ctx,node.arguments[0]);
      if(!hoc.factory||!arg.definition)fail('unsupported_hoc_contract');
      return factoryTarget(hoc.ctx,hoc.factory,arg);
    }
    fail('unsupported_component_expression');
  }
  const main=load(file);
  function describe(node) {
    used=new Set([main]);active=new Set();
    node=main.elements.get(`${node.start}:${node.end}`);if(!node)fail('callsite_range_mismatch');
    const intrinsic=node.openingElement.name.type==='JSXIdentifier'&&/^[a-z]/.test(node.openingElement.name.name);
    const target=intrinsic?{ctx:main,definition:{root:node,forwarded:['className','style','title']}}:expression(main,node.openingElement.name);
    if(!target.definition?.forwarded.length)fail('no_verified_presentation_forwarding');
    if(node.openingElement.attributes.some(a=>a.type==='JSXSpreadAttribute'))fail('instance_spread_not_supported');
    const names=node.openingElement.attributes.map(a=>a.name.name);
    if(new Set(names).size!==names.length)fail('duplicate_jsx_attribute');
    const p=main.paths.get(node);let cursor=node;
    const keyAttribute=node.openingElement.attributes.find(a=>a.type==='JSXAttribute'&&a.name.name==='key'),key=keyAttribute?.value?.expression;
    function literal(n) {return ['StringLiteral','NumericLiteral','BooleanLiteral','NullLiteral'].includes(n.type)||n.type==='ObjectExpression'&&n.properties.every(p=>p.type==='ObjectProperty'&&!p.computed&&literal(p.value));}
    // Repicking a previously specialized element wraps the existing specialization.
    while(true) {
      const parent=main.paths.get(cursor).parent,fn=parent?.callee,e=fn?.params?.[0],body=fn?.body;
      if(parent?.type!=='CallExpression'||parent.arguments.length!==1||parent.arguments[0]!==cursor||fn.type!=='ArrowFunctionExpression'||fn.params.length!==1||e.type!=='Identifier'||body.type!=='ConditionalExpression')break;
      const test=body.test,chosen=body.consequent,b=chosen.type==='CallExpression'&&chosen.callee.type==='Identifier'?main.paths.get(chosen.callee).scope.getBinding(chosen.callee.name):null;
      if(test.type!=='BinaryExpression'||test.operator!=='==='||test.left.type!=='MemberExpression'||test.left.computed||test.left.object.name!==e.name||test.left.property.name!=='key'||test.right.type!=='StringLiteral'
        ||body.alternate.name!==e.name||chosen.arguments[0]?.name!==e.name||chosen.arguments.length!==2||chosen.arguments[1].type!=='ObjectExpression'
        ||!chosen.arguments[1].properties.every(p=>p.type==='ObjectProperty'&&!p.computed&&['className','style','title'].includes(p.key.name||p.key.value)&&literal(p.value))
        ||!b?.constant||b.path.type!=='ImportSpecifier'||b.path.node.imported.name!=='cloneElement'||b.path.parent.source.value!=='react')break;
      cursor=parent;
    }
    const callback=main.paths.get(cursor).findParent(p=>p.isFunction());
    let loop=null;
    if(callback?.node.type==='ArrowFunctionExpression'&&callback.node.body===cursor&&callback.parent.type==='CallExpression'
      &&callback.parent.arguments[0]===callback.node&&callback.parent.callee.type==='MemberExpression'
      &&!callback.parent.callee.computed&&callback.parent.callee.property.name==='map') {
      let base=key;while(base?.type==='MemberExpression'&&!base.computed)base=base.object;
      if(!key||base?.type!=='Identifier'||callback.node.params[0]?.type!=='Identifier'
        ||main.paths.get(base)?.scope.getBinding(base.name)?.identifier!==callback.node.params[0])fail('stable_first_item_key_required');
      if(callback.node.async)fail('asynchronous_loop_not_supported');
      if(p.scope.getBinding('JSON')||p.scope.getBinding('encodeURIComponent'))fail('shadowed_instance_encoder');
      loop={keyExpression:main.code.slice(key.start,key.end)};
    }
    if(intrinsic&&!loop)fail('keyed_intrinsic_required');
    const sharedOwner=Boolean(instances.owner(main.tree,node,main.definitions,babel.traverse));
    const reactImports=main.tree.program.body.filter(n=>n.type==='ImportDeclaration'&&n.source.value==='react').flatMap(n=>n.specifiers
      .filter(s=>s.type==='ImportSpecifier'&&p.scope.getBinding(s.local.name)?.path.node===s)
      .map(s=>({imported:s.imported.name,local:s.local.name,kind:s.importKind==='type'||n.importKind==='type'?'type':'value'})));
    const dependencies=[...used].map(c=>({file:c.full,sha256:c.hash})).sort((a,b)=>a.file<b.file?-1:a.file>b.file?1:0);
    return {file:main.relative,start:node.start,end:node.end,tag:main.code.slice(node.openingElement.name.start,node.openingElement.name.end),hash:main.hash,id:id(main,node),
      templateId:id(target.ctx,target.definition.root),templateFile:target.ctx.full,forwardedProps:target.definition.forwarded,
      projectRoot:main.root,dependencies,sharedOwner,reactImports,intrinsic,replaceStart:cursor.start,replaceEnd:cursor.end,...(loop?{loop}:{}),node,tree:main.tree,code:main.code};
  }
  return {main,describe};
}
function decodeIdentity(value) {
  const match=/^([a-f0-9]{24})(?::(.+))?$/.exec(value||'');if(!match)fail('invalid_instance_identity');
  if(!match[2])return {id:match[1]};
  let key;try{key=JSON.parse(decodeURIComponent(match[2]));}catch{fail('invalid_instance_key');}
  if(!Array.isArray(key)||key.length!==2||!['string','number'].includes(key[0])||typeof key[1]!==key[0]||(key[0]==='number'&&!Number.isFinite(key[1])))fail('invalid_instance_key');
  return {id:match[1],key:{type:key[0],value:key[1]}};
}
module.exports={graph,decodeIdentity};
