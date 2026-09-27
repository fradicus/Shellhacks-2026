/** Truck artwork adapted from the user-supplied GridBridge_updated.html.
 * Decorative illustration only; no operational fleet data is represented.
 * @param {HTMLCanvasElement} cv
 * @param {boolean | (() => boolean)} paused
 * @returns {() => void}
 */
export function startRoadScene(cv, paused) {
 const ctx = cv.getContext("2d");
 if (!ctx) return () => {};
 const brand = document.querySelector("header a span");
 const DISP = brand ? getComputedStyle(brand).fontFamily : '"Arial Narrow", sans-serif';
 const clamp = (v, a=0, b=1) => Math.max(a, Math.min(b, v));
 let W=1,H=1,DPR=1,L=1,roadY=1,frameId=0,visible=true,disposed=false;
 let elapsed=0,last=performance.now();
 const story=cv.closest("[data-gridbridge-story]");
 const reduced = matchMedia('(prefers-reduced-motion: reduce)');
 const motes=Array.from({length:50},(_,i)=>({x:(i*.618)%1,y:(i*.371)%1,v:.2+(i%5)*.1,r:.6+(i%3)*.3,p:i}));
 function resize() {
   const box=cv.getBoundingClientRect(); W=box.width; H=box.height;
   DPR=Math.min(2,devicePixelRatio||1); cv.width=Math.round(W*DPR); cv.height=Math.round(H*DPR);
   L=W<700?W*.88:Math.min(W*.72,1080); roadY=H*.76;
   render(performance.now());
 }
function beam(xf,h,t){
  if(h<=0)return;const lx=xf+L*.016,ly=roadY-L*.115,R=Math.max(W*1.1,L*1.4);
  ctx.save();ctx.globalCompositeOperation='lighter';
  let g=ctx.createLinearGradient(lx,0,lx-R,0);g.addColorStop(0,`rgba(255,238,210,${.26*h})`);g.addColorStop(.4,`rgba(255,238,210,${.07*h})`);g.addColorStop(1,'rgba(255,238,210,0)');
  ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(lx,ly-L*.01);ctx.lineTo(lx-R,ly-R*.17);ctx.lineTo(lx-R,ly+R*.24);ctx.lineTo(lx,ly+L*.01);ctx.fill();
  ctx.save();ctx.translate(lx-L*.45,roadY+1);ctx.scale(1,.06);g=ctx.createRadialGradient(0,0,0,0,0,L*.7);g.addColorStop(0,`rgba(255,232,196,${.28*h})`);g.addColorStop(1,'rgba(255,232,196,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,L*.7,0,7);ctx.fill();ctx.restore();
  for(const m of motes){const x=((m.x*W-t*m.v*30)%W+W)%W,y=m.y*H,dx=lx-x;if(dx<=0)continue;const half=dx*.2+L*.01,off=y-(ly+dx*.035);if(Math.abs(off)>half)continue;
    const a=h*(1-dx/R)*(1-Math.abs(off)/half)*(.5+.5*Math.sin(t*1.5+m.p))*.7;if(a<.02)continue;ctx.fillStyle=`rgba(255,240,215,${a})`;ctx.beginPath();ctx.arc(x,y,m.r,0,7);ctx.fill()}
  g=ctx.createRadialGradient(lx,ly,0,lx,ly,L*.1);g.addColorStop(0,`rgba(255,252,242,${h})`);g.addColorStop(.1,`rgba(255,236,200,${.45*h})`);g.addColorStop(1,'rgba(255,220,170,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(lx,ly,L*.1,0,7);ctx.fill();
  ctx.save();ctx.translate(lx,ly);ctx.scale(1,.008);g=ctx.createRadialGradient(0,0,0,0,0,W*.6);g.addColorStop(0,`rgba(255,245,230,${.35*h})`);g.addColorStop(1,'rgba(255,245,230,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,W*.6,0,7);ctx.fill();ctx.restore();
  ctx.restore();
}
function wheel(x,r,rot){
  ctx.fillStyle='#030303';ctx.beginPath();ctx.arc(x,-r,r,0,7);ctx.fill();
  const g=ctx.createRadialGradient(x-r*.15,-r*1.15,0,x,-r,r*.58);g.addColorStop(0,'#5C5F66');g.addColorStop(1,'#1C1D21');ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,-r,r*.56,0,7);ctx.fill();
  ctx.strokeStyle='rgba(0,0,0,.55)';ctx.lineWidth=.004;for(let i=0;i<8;i++){const a=rot+i*Math.PI/4;ctx.beginPath();ctx.moveTo(x+Math.cos(a)*r*.16,-r+Math.sin(a)*r*.16);ctx.lineTo(x+Math.cos(a)*r*.5,-r+Math.sin(a)*r*.5);ctx.stroke()}
  ctx.fillStyle='#0A0A0B';ctx.beginPath();ctx.arc(x,-r,r*.12,0,7);ctx.fill();
}
function truck(xf,rot,mk,hd){
  if(xf>W+10||xf+L<-10)return;
  ctx.save();ctx.translate(xf,roadY);ctx.scale(L,L);
  ctx.save();ctx.scale(1,.04);const sg=ctx.createRadialGradient(.5,0,0,.5,0,.62);sg.addColorStop(0,'rgba(0,0,0,.9)');sg.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=sg;ctx.fillRect(-.12,-.7,1.24,1.4);ctx.restore();
  // trailer: satin aluminium catching the light
  let g=ctx.createLinearGradient(0,-.31,0,-.085);g.addColorStop(0,'#2A2C31');g.addColorStop(.08,'#1A1B1F');g.addColorStop(.6,'#111215');g.addColorStop(1,'#08080A');
  ctx.fillStyle=g;ctx.fillRect(.3,-.31,.7,.225);
  g=ctx.createLinearGradient(.3,0,1,0);g.addColorStop(0,`rgba(255,240,215,${.05*hd})`);g.addColorStop(1,'rgba(255,240,215,0)');ctx.fillStyle=g;ctx.fillRect(.3,-.31,.7,.225);
  ctx.fillStyle=`rgba(255,255,255,${.1+.2*hd})`;ctx.fillRect(.3,-.31,.7,.0018);
  ctx.fillStyle='#040405';ctx.fillRect(.3,-.087,.7,.013);ctx.fillRect(.43,-.075,.005,.05);
  // cab
  g=ctx.createLinearGradient(0,-.3,0,-.07);g.addColorStop(0,'#26282D');g.addColorStop(.35,'#141518');g.addColorStop(1,'#08080A');ctx.fillStyle=g;
  ctx.beginPath();ctx.moveTo(.012,-.075);ctx.lineTo(.012,-.16);ctx.quadraticCurveTo(.014,-.178,.034,-.18);ctx.lineTo(.13,-.19);ctx.lineTo(.146,-.272);
  ctx.quadraticCurveTo(.15,-.286,.167,-.287);ctx.lineTo(.236,-.289);ctx.lineTo(.246,-.3);ctx.lineTo(.322,-.3);ctx.quadraticCurveTo(.33,-.298,.33,-.288);ctx.lineTo(.33,-.085);ctx.lineTo(.3,-.07);ctx.lineTo(.012,-.07);ctx.closePath();ctx.fill();
  ctx.strokeStyle=`rgba(255,255,255,${.08+.28*hd})`;ctx.lineWidth=.0018;ctx.beginPath();ctx.moveTo(.012,-.16);ctx.quadraticCurveTo(.014,-.178,.034,-.18);ctx.lineTo(.13,-.19);ctx.lineTo(.146,-.272);ctx.quadraticCurveTo(.15,-.286,.167,-.287);ctx.lineTo(.236,-.289);ctx.stroke();
  g=ctx.createLinearGradient(.14,-.27,.2,-.2);g.addColorStop(0,'#3A3F48');g.addColorStop(.45,'#0B0C0F');g.addColorStop(1,'#1A1D22');ctx.fillStyle=g;
  ctx.beginPath();ctx.moveTo(.139,-.2);ctx.lineTo(.15,-.266);ctx.lineTo(.19,-.268);ctx.lineTo(.19,-.2);ctx.fill();
  ctx.beginPath();ctx.moveTo(.197,-.205);ctx.lineTo(.197,-.266);ctx.lineTo(.229,-.268);ctx.lineTo(.229,-.205);ctx.fill();
  ctx.fillStyle='#1E1F23';ctx.fillRect(-.003,-.082,.038,.028);ctx.fillStyle=`rgba(255,255,255,${.12+.3*hd})`;ctx.fillRect(-.003,-.082,.038,.002);
  ctx.fillStyle='#0C0C0E';ctx.fillRect(.012,-.158,.007,.074);
  g=ctx.createLinearGradient(.237,0,.245,0);g.addColorStop(0,'#2A2B30');g.addColorStop(.5,'#8E9097');g.addColorStop(1,'#1E1F23');ctx.fillStyle=g;ctx.fillRect(.237,-.365,.007,.185);
  ctx.fillStyle='#000';ctx.beginPath();ctx.arc(.085,-.044,.054,Math.PI,0);ctx.fill();
  // Tires have positive clearance: axle spacing exceeds the sum of tire radii.
  wheel(.085,.044,rot);
  [.254,.332,.855,.937].forEach(x=>wheel(x,.032,rot));
  ctx.fillStyle=hd>0?`rgba(255,250,238,${.3+.7*hd})`:'#1E1F23';ctx.fillRect(.012,-.123,.012,.016);
  ctx.fillStyle=`rgba(255,59,48,${.3+.7*mk})`;ctx.fillRect(.994,-.117,.006,.018);
  ctx.restore();
  // Use the application's overlapping utility mark and condensed uppercase wordmark.
  ctx.save();
  const logoX=xf+L*.46,logoY=roadY-L*.197,r=L*.018;
  ctx.lineWidth=L*.0023;
  ctx.strokeStyle='#5cc8ff';ctx.beginPath();ctx.arc(logoX-L*.009,logoY,r,0,Math.PI*2);ctx.stroke();
  ctx.strokeStyle='#ffae42';ctx.beginPath();ctx.arc(logoX+L*.009,logoY,r,0,Math.PI*2);ctx.stroke();
  ctx.fillStyle='#f4efe6';ctx.beginPath();ctx.arc(logoX,logoY,L*.003,0,Math.PI*2);ctx.fill();
  ctx.font=`800 ${L*.052}px ${DISP}`;ctx.textBaseline='middle';ctx.letterSpacing=`${L*.003}px`;
  ctx.fillStyle='rgba(244,239,230,.86)';ctx.fillText('GRIDBRIDGE',xf+L*.51,logoY,L*.40);ctx.restore();
  // marker lights
  const mks=[];for(let i=0;i<5;i++)mks.push([.168+i*.015,-.29]);for(let x=.34;x<1;x+=.109)mks.push([x,-.306]);
  ctx.save();ctx.globalCompositeOperation='lighter';
  mks.forEach(([x,y],i)=>{const on=clamp((mk*mks.length-i));if(on<=0)return;const sx=xf+x*L,sy=roadY+y*L,rr=Math.max(1,L*.0022);
    const gg=ctx.createRadialGradient(sx,sy,0,sx,sy,rr*6);gg.addColorStop(0,`rgba(255,196,120,${.4*on})`);gg.addColorStop(1,'rgba(255,196,120,0)');ctx.fillStyle=gg;ctx.fillRect(sx-rr*6,sy-rr*6,rr*12,rr*12);
    ctx.fillStyle=`rgba(255,222,170,${on})`;ctx.beginPath();ctx.arc(sx,sy,rr,0,7);ctx.fill()});
  const tx=xf+L,ty=roadY-L*.108,tg=ctx.createRadialGradient(tx,ty,0,tx,ty,L*.05);tg.addColorStop(0,`rgba(255,59,48,${.4*mk})`);tg.addColorStop(1,'rgba(255,59,48,0)');ctx.fillStyle=tg;ctx.fillRect(tx-L*.05,ty-L*.05,L*.1,L*.1);
  ctx.restore();
}

 function render(now) {
   if(disposed) return;
   const dt=Math.min(.05,Math.max(0,(now-last)/1000));last=now;
   if(!(typeof paused === "function" ? paused() : paused)&&!reduced.matches)elapsed+=dt;
   const t=elapsed;
   const reveal=reduced.matches?1:clamp((t-.8)/1.6);
   const ease=reveal*reveal*(3-2*reveal);
   const introL=Math.min(W*.84,1100),finalL=W<700?W*.88:Math.min(W*.55,860);
   L=introL+(finalL-introL)*ease;
   const p=reduced.matches?0:Number(story?.style.getPropertyValue('--story-progress')||0);
   const seg=(a,b)=>clamp((p-a)/(b-a));
   const smooth=x=>x*x*(3-2*x);
   roadY=H*(.65+.16*ease-.12*smooth(seg(.02,.14)));
   ctx.setTransform(DPR,0,0,DPR,0,0); ctx.clearRect(0,0,W,H);
   const road=ctx.createLinearGradient(0,roadY,0,H);
   road.addColorStop(0,'#111114'); road.addColorStop(1,'#000');
   ctx.fillStyle=road;ctx.fillRect(0,roadY,W,H-roadY);
   ctx.strokeStyle='rgba(255,226,176,.12)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,roadY);ctx.lineTo(W,roadY);ctx.stroke();
   ctx.strokeStyle='rgba(255,255,255,.09)';ctx.setLineDash([48,100]);ctx.lineDashOffset=t*30;
   ctx.beginPath();ctx.moveTo(0,roadY+30);ctx.lineTo(W,roadY+30);ctx.stroke();ctx.setLineDash([]);
   const startX=(W-L)*.5,endX=W<700?(W-L)*.5:W-L-W*.04;
   let xf=startX+(endX-startX)*ease;
   if(p>=.04 && p<.28)xf=endX+(-L-80-endX)*smooth(seg(.04,.28));
   else if(p>=.28 && p<.34)xf=-L-80;
   else if(p>=.34 && p<.58)xf=W+60+(-L-80-W-60)*smooth(seg(.34,.58));
   else if(p>=.58)xf=-L-80;
   if(story){
     const edge=`${clamp((xf+L)/W)*100}%`;
     story.style.setProperty('--wipe-one',p<.04?'100%':p<.28?edge:'0%');
     story.style.setProperty('--wipe-two',p<.34?'100%':p<.58?edge:'0%');
   }
   beam(xf,1,t); truck(xf,xf/(L*.032),1,1);
 }
 function tick(now) { frameId=0; if(disposed||!visible||document.hidden) return;render(now);if(!reduced.matches)frameId=requestAnimationFrame(tick); }
 function schedule() {cancelAnimationFrame(frameId);frameId=requestAnimationFrame(tick);}
 const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;schedule();});observer.observe(cv);
 const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(cv);
 document.addEventListener('visibilitychange',schedule);reduced.addEventListener('change',schedule);
 resize();schedule();
 return ()=>{disposed=true;cancelAnimationFrame(frameId);observer.disconnect();resizeObserver.disconnect();document.removeEventListener('visibilitychange',schedule);reduced.removeEventListener('change',schedule);};
}
