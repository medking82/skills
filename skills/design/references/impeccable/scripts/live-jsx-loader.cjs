// Optional webpack pre-loader. Leaves the existing JSX/TSX transform in charge.
const path=require('node:path');
const {createRequire}=require('node:module');
module.exports=function(source,inputMap) {
  if(this.mode!=='development')return this.callback(null,source,inputMap);
  const root=this.getOptions().root;
  const babel=createRequire(path.join(root,'package.json'))('@babel/core');
  const result=babel.transformSync(source,{filename:this.resourcePath,configFile:false,babelrc:false,
    sourceMaps:true,inputSourceMap:inputMap||undefined,
    parserOpts:{plugins:['jsx',...(this.resourcePath.endsWith('.tsx')?['typescript']:[])]},
    plugins:[[require('./live-jsx-source.cjs'),{development:true,root}]]});
  this.callback(null,result.code,result.map);
};
