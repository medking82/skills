// Bounded, same-module function-component provenance. Never execute component code.
const PRESENTATION=new Set(['className','style','title']);
const PROP='__designLiveInstance';
const MARKER='data-design-live-instance';
function reactWrapper(node,scope) {
  if(node?.type!=='CallExpression'||node.arguments.length!==1)return null;
  const callee=node.callee,member=callee.type==='MemberExpression'&&!callee.computed;
  const binding=scope.getBinding(member?callee.object.name:callee.name),p=binding?.path;
  if(!binding?.constant||p?.parent?.source?.value!=='react')return null;
  const name=member&&['ImportDefaultSpecifier','ImportNamespaceSpecifier'].includes(p.type)?callee.property.name
    :p.type==='ImportSpecifier'?p.node.imported.name:null;
  return ['memo','forwardRef'].includes(name)?name:null;
}
function renderDefinition(name,fn,binding,forwardRef=false) {
  const simple=fn.body?.type!=='BlockStatement'||(fn.body.body.length===1&&fn.body.body[0].type==='ReturnStatement');
  const root=fn.body?.type==='BlockStatement'?fn.body.body.find(n=>n.type==='ReturnStatement')?.argument:fn.body;
  const parameter=(fn.params?.length===1||(forwardRef&&fn.params?.length===2))?fn.params[0]:null,forwarded=[];
  function observesArguments(n) {
    if(!n||typeof n!=='object')return false;
    if(n.type==='Identifier'&&['arguments','eval'].includes(n.name))return true;
    return Object.entries(n).some(([k,v])=>!['loc','extra','comments'].includes(k)&&(Array.isArray(v)?v:[v]).some(observesArguments));
  }
  if(simple&&root?.type==='JSXElement'&&root.openingElement.name.type==='JSXIdentifier'&&/^[a-z]/.test(root.openingElement.name.name)
    &&parameter?.type==='ObjectPattern'&&parameter.properties.every(p=>p.type==='ObjectProperty'&&!p.computed&&p.key.name!==PROP)&&!observesArguments(root)) {
    const bindings=new Map(parameter.properties.map(p=>[p.value.type==='AssignmentPattern'?p.value.left.name:p.value.name,p.key.name]));
    const attributes=root.openingElement.attributes,names=attributes.map(a=>a.name?.name);
    if(!attributes.some(a=>a.type==='JSXSpreadAttribute')&&new Set(names).size===names.length)for(const a of attributes) {
      const prop=bindings.get(a.value?.expression?.type==='Identifier'?a.value.expression.name:null);
      if(a.type==='JSXAttribute'&&PRESENTATION.has(a.name.name)&&prop===a.name.name)forwarded.push(prop);
    }
  }
  return {name,fn,binding,root,parameter,forwarded};
}
function components(tree,traverse,relative='') {
  const result=[];
  const scopes=new WeakMap();traverse(tree,{enter(p){scopes.set(p.node,p.scope);}});
  const commonExports=new Map();
  for(const statement of tree.program.body) {
    const assignment=statement.expression,left=assignment?.left;
    if(assignment?.type==='AssignmentExpression'&&left?.type==='MemberExpression'&&!left.computed
      &&((left.object.name==='module'&&left.property.name==='exports')||left.object.name==='exports')) {
      commonExports.set(assignment.right.type==='Identifier'?assignment.right.name:assignment.right,
        left.object.name==='module');
    }
  }
  for(const statement of tree.program.body) {
    const declaration=statement.type.startsWith('Export')?statement.declaration:statement;
    const entries=declaration?.type==='FunctionDeclaration'||declaration?.type==='ClassDeclaration'?[{name:declaration.id?.name||'DefaultExport',fn:declaration,binding:declaration}]
      :statement.type==='ExportDefaultDeclaration'&&['ArrowFunctionExpression','CallExpression'].includes(declaration?.type)?[{name:'DefaultExport',fn:declaration,binding:declaration}]
      :commonExports.has(statement.expression?.right)&&['FunctionExpression','ArrowFunctionExpression'].includes(statement.expression.right?.type)?[{name:'DefaultExport',fn:statement.expression.right,binding:statement.expression.right}]
      :declaration?.type==='VariableDeclaration'?declaration.declarations.map(d=>({name:d.id.name,fn:d.init,binding:d})):[];
    for(const entry of entries) {
      let fn=entry.fn,forwardRef=false;
      while(reactWrapper(fn,scopes.get(fn))){forwardRef=reactWrapper(fn,scopes.get(fn))==='forwardRef'||forwardRef;fn=fn.arguments[0];}
      if(!/^[A-Z]/.test(entry.name||'') || !['FunctionDeclaration','ArrowFunctionExpression','FunctionExpression','ClassDeclaration'].includes(fn?.type))continue;
      const exported=statement.type.startsWith('Export')||commonExports.has(entry.name)||commonExports.has(fn);
      const routeEntry=(statement.type==='ExportDefaultDeclaration'||commonExports.get(entry.name)||commonExports.get(fn))&&/(^|\/)app\/(?:.*\/)?page\.(jsx|tsx)$/.test(relative);
      if(fn.type==='ClassDeclaration'){result.push({...entry,exported,reusable:exported&&!routeEntry,forwarded:[],calls:[]});continue;}
      result.push({...renderDefinition(entry.name,fn,entry.binding,forwardRef),exported,reusable:exported&&!routeEntry,calls:[]});
    }
  }
  traverse(tree,{ReferencedIdentifier(p) {
    if(!((p.parent.type==='VariableDeclarator'&&p.parent.init===p.node)
      ||(p.parent.type==='AssignmentExpression'&&p.parent.right===p.node&&!commonExports.has(p.node.name))
      ||['CallExpression','OptionalCallExpression','NewExpression','ObjectProperty','ArrayExpression','ReturnStatement','ExportDefaultDeclaration','ExportSpecifier'].includes(p.parent.type)))return;
    const binding=p.scope.getBinding(p.node.name),candidate=result.find(c=>binding?.path.node===c.binding);
    if(candidate)candidate.reusable=true;
  },JSXElement(p) {
    const name=p.node.openingElement.name;
    if(name.type!=='JSXIdentifier')return;
    const binding=p.scope.getBinding(name.name);
    const candidate=result.find(c=>c.name===name.name&&binding?.path.node===c.binding);
    if(candidate){candidate.reusable=true;if(binding.constant)candidate.calls.push(p.node);}
  }});
  return result;
}
function owner(tree,node,definitions,traverse) {
  let found;
  traverse(tree,{JSXElement(p) {if(p.node===node){found=definitions.find(c=>c.reusable&&p.findParent(a=>a.node===c.fn));p.stop();}}});
  return found;
}
function instanceContract(node,code,forwarded,isStatic) {
  const opening=node.openingElement;
  const names=opening.attributes.filter(a=>a.type==='JSXAttribute').map(a=>a.name.name);
  if(new Set(names).size!==names.length)throw Error('duplicate_jsx_attribute');
  if(opening.attributes.some(a=>a.type==='JSXSpreadAttribute'))throw Error('instance_spread_not_supported');
  const protectedAttributes=opening.attributes.filter(a=> {
    if(!forwarded.includes(a.name.name))return true;
    if(a.value?.type==='JSXExpressionContainer'&&!isStatic(a.value.expression))throw Error('dynamic_instance_presentation_prop');
    return false;
  }).map(a=>code.slice(a.start,a.end));
  return {name:code.slice(opening.name.start,opening.name.end),protectedAttributes,
    children:node.children.map(n=>code.slice(n.start,n.end)),selfClosing:opening.selfClosing};
}
module.exports={components,owner,instanceContract,reactWrapper,renderDefinition,PROP,MARKER};
