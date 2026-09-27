/* eslint-disable @typescript-eslint/no-require-imports */
// Standalone Node exporter: render the live React components without a Next.js runtime.
// The CommonJS hooks are process-local adapters for TSX, CSS modules, and Next links.
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const destination = process.argv[2];
if (!destination) throw new Error('Usage: node scripts/export-landing.cjs /path/to/output-directory');
const outputDirectory = path.resolve(destination);
const configuredUrl = new URL(process.env.GRIDBRIDGE_APP_URL || 'http://127.0.0.1:3001');
if (!['http:', 'https:'].includes(configuredUrl.protocol) || configuredUrl.username || configuredUrl.password) {
  throw new Error('GRIDBRIDGE_APP_URL must be an HTTP(S) origin without credentials.');
}
const appOrigin = configuredUrl.origin;
const escapeAttribute = value => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
const ts = require(root+'/node_modules/typescript');
const React = require(root+'/node_modules/react');
const {renderToStaticMarkup} = require(root+'/node_modules/react-dom/server');
const originalLoad = Module._load;
Module._load = function(request, parent, isMain) {
  if(request === 'next/link') return function Link({href, children, ...props}) {return React.createElement('a',{...props,href},children);};
  if(request === 'next/navigation') return {usePathname:()=>'/'};
  if(request.endsWith('.module.css')) return new Proxy({}, {get:(_,key)=>key==='__esModule'?false:typeof key==='string'?'gb-'+key:undefined});
  return originalLoad.call(this, request, parent, isMain);
};
require.extensions['.tsx'] = function(module, filename) {
  const output = ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText;
  module._compile(output,filename);
};
const {LandingPage}=require(root+'/components/landing/LandingPage.tsx');
const {Nav}=require(root+'/components/nav/Nav.tsx');
let body=renderToStaticMarkup(React.createElement(React.Fragment,null,React.createElement(Nav),React.createElement(LandingPage)));
body=body.replace(/href="\/"/g,'href="#top"').replace(/href="\/(?!\/)([^"#]+)"/g,(_, route) => 'href="'+escapeAttribute(appOrigin+'/'+route)+'"');
const scope=css=>css.replace(/\.([a-zA-Z_][\w-]*)/g,'.gb-$1');
const css=fs.readFileSync(root+'/app/globals.css','utf8')+'\n'+scope(fs.readFileSync(root+'/components/landing/landing.module.css','utf8'))+'\n'+scope(fs.readFileSync(root+'/components/nav/Nav.module.css','utf8'))+'\n:root{--gb-sans:Arial,sans-serif;--gb-display:Arial,sans-serif;--gb-mono:monospace}html{scroll-behavior:smooth}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}';
const road=fs.readFileSync(root+'/components/landing/road-scene.js','utf8').replace('export function startRoadScene','function startRoadScene');
const storySource=fs.readFileSync(root+'/components/landing/HeroStory.tsx','utf8');
if (!storySource.includes('    const reduced=') || !storySource.includes('    return()=>')) throw new Error('HeroStory structure changed; update the standalone scroll adapter.');
const storyLogic=ts.transpileModule(storySource.slice(storySource.indexOf('    const reduced='),storySource.indexOf('    return()=>')),{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;
const behavior=`
(()=>{
 const hero=document.querySelector('.gb-hero');
 const scene=hero.querySelector('.gb-scene');
 const buttons=[...hero.querySelectorAll('[aria-label="Illustration view"] button')];
 const pause=hero.querySelector('.gb-pause');
 const caption=hero.querySelector('.gb-sceneCaption');
 let view='road',paused=false;
 const dispose=startRoadScene(scene.querySelector('canvas'),()=>paused);
 function render(){
  scene.className='gb-scene'+(view==='network'?' gb-sceneNetwork':'')+(paused?' gb-paused':'');
  buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String((i===0)===(view==='road'))));
  pause.textContent=paused?'Play animation':'Pause animation';pause.setAttribute('aria-pressed',String(paused));
  caption.innerHTML='<span class="gb-statusDot"></span>'+(view==='road'?'Separate projects. A shared horizon.':'One region. More possibilities.')+'<span>Illustrative animation</span>';
 }
 buttons[0].addEventListener('click',()=>{view='road';render()});buttons[1].addEventListener('click',()=>{view='network';render()});
 pause.addEventListener('click',()=>{paused=!paused;hero.closest('[data-gridbridge-story]').dataset.animationPaused=String(paused);render()});
 addEventListener('pagehide',()=>dispose());render();
 const element=document.querySelector('[data-gridbridge-story]');
 ${storyLogic}
})();`;
// Embed the app's fonts so the logo and typography also work offline.
let fontCss='';
const cssDir=root+'/.next/static/css';
if(!fs.existsSync(cssDir)) throw new Error('Build the app with npm run build -- --webpack before exporting so fonts can be embedded.');
if(fs.existsSync(cssDir))for(const file of fs.readdirSync(cssDir)){
 if(!file.endsWith('.css'))continue;
 const built=fs.readFileSync(cssDir+'/'+file,'utf8');
 for(const face of built.match(/@font-face\{[^}]+\}/g)||[]){
  if(!face.includes('woff2'))continue;
  const embedded=face.replace(/url\(([^)]+)\)/g,(all,url)=>{
   const name=url.replace(/["']/g,'').split('/').pop();
   const f=root+'/.next/static/media/'+name;
   return fs.existsSync(f)?'url(data:font/woff2;base64,'+fs.readFileSync(f).toString('base64')+')':all;
  });
  fontCss+=embedded;
 }
}
const familyFor=(part)=>{const m=fontCss.match(new RegExp('font-family:([^;}]*'+part+'[^;}]*)'));return m?m[1]:part;};
fontCss+=':root{--gb-display:'+familyFor('Big Shoulders')+',"Arial Narrow",sans-serif;--gb-sans:'+familyFor('Public Sans')+',Arial,sans-serif;--gb-mono:'+familyFor('Martian Mono')+',monospace}';
const html='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#000"><title>GridBridge — Every mile. Connected.</title><style>'+css+fontCss+'</style></head><body id="top">'+body+'<script>'+road+'\n'+behavior+'</script></body></html>\n';
if(html.includes('/_next/')) throw new Error('Export contains unresolved Next.js asset paths.');
new Function(road+'\n'+behavior);
fs.mkdirSync(outputDirectory, {recursive:true});
fs.writeFileSync(path.join(outputDirectory,'GridBridge.html'),html);
console.log('Created '+path.join(outputDirectory,'GridBridge.html')+' ('+Buffer.byteLength(html)+' bytes)');
console.log('Styles inline:', !/<link[^>]+stylesheet/i.test(html));
console.log('Scripts inline:', !/<script[^>]+src=/i.test(html));
console.log('No Next runtime imports:', !html.includes('/_next/'));
new Function(road+'\n'+behavior);console.log('Animation script syntax verified');
