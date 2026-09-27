"use client";

import { useEffect, useRef, type ReactNode } from "react";
import s from "./landing.module.css";

export function HeroStory({children}:{children:ReactNode}) {
  const root=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    const element=root.current;
    if(!element)return;
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');
    let frame=0, current=0, last=performance.now();
    function update(){
      frame=0;
      if(!element)return;
      const rect=element.getBoundingClientRect();
      const target=reduced.matches?0:Math.max(0,Math.min(1,(52-rect.top)/Math.max(1,rect.height-innerHeight+52)));
      const now=performance.now(),dt=Math.min(.05,(now-last)/1000);last=now;
      current+= (target-current)*(1-Math.exp(-12*dt));
      if(Math.abs(target-current)<.0001)current=target;
      const segment=(a:number,b:number)=>Math.max(0,Math.min(1,(current-a)/(b-a)));
      element.style.setProperty('--story-progress',String(current));
      element.style.setProperty('--network-progress',String(segment(.60,.88)));
      element.style.setProperty('--intro-opacity',String(1-segment(.04,.14)));
      element.style.setProperty('--beat-one',String(segment(.04,.07)*(1-segment(.36,.46))));
      element.style.setProperty('--beat-two',String(segment(.34,.37)*(1-segment(.62,.73))));
      if(current!==target)frame=requestAnimationFrame(update);
    }
    function schedule(){if(!frame)frame=requestAnimationFrame(update);}
    addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);reduced.addEventListener('change',schedule);update();
    return()=>{cancelAnimationFrame(frame);removeEventListener('scroll',schedule);removeEventListener('resize',schedule);reduced.removeEventListener('change',schedule);};
  },[]);
  return <div ref={root} className={s.story} data-gridbridge-story="">{children}</div>;
}
