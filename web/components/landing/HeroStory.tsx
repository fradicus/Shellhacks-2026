"use client";

import { useEffect, useRef, type ReactNode } from "react";
import s from "./landing.module.css";

export function HeroStory({ children }: { children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');
    let frame=0, current=0, last=performance.now(), elapsed=0;
    let autoplay=!reduced.matches && scrollY<80 && !location.hash;
    function takeControl(event:Event){
      if(event.type==='keydown' && !['ArrowDown','ArrowUp','PageDown','PageUp','Home','End',' ','Tab','Escape'].includes((event as KeyboardEvent).key))return;
      if((event.target as HTMLElement).closest?.('[data-animation-pause]') && (event.type!=='keydown' || [' ','Enter'].includes((event as KeyboardEvent).key)))return;
      autoplay=false;
    }
    function update(){
      frame=0;
      if(!element)return;
      const now=performance.now(),dt=Math.min(.05,(now-last)/1000);last=now;
      if(reduced.matches)autoplay=false;
      let rect=element.getBoundingClientRect();
      if(autoplay && !document.hidden && element.dataset.animationPaused!=='true'){
        elapsed+=dt;
        if(elapsed>1.2){
          const travel=Math.max(1,rect.height-innerHeight+52);
          // Same roads on arrival, one truck pass turns it into One network, then Common Ground.
          const position=Math.min(travel+innerHeight*.55,(elapsed-1.2)*travel/12);
          scrollTo({top:scrollY+rect.top-52+position,behavior:'instant'});
          rect=element.getBoundingClientRect();
          if(position>=travel+innerHeight*.55)autoplay=false;
        }
      }
      const target=reduced.matches?0:Math.max(0,Math.min(1,(52-rect.top)/Math.max(1,rect.height-innerHeight+52)));
      current+=(target-current)*(1-Math.exp(-12*dt));
      if(Math.abs(target-current)<.0001)current=target;
      const segment=(a:number,b:number)=>Math.max(0,Math.min(1,(current-a)/(b-a)));
      element.style.setProperty('--story-progress',String(current));
      element.style.setProperty('--beat-two',String(1-segment(.56,.68)));
      element.style.setProperty('--brand-reveal',String(segment(.64,.86)));
      if(autoplay || current!==target)frame=requestAnimationFrame(update);
    }
    function schedule(){if(!frame)frame=requestAnimationFrame(update);}
    addEventListener('click',takeControl);addEventListener('wheel',takeControl,{passive:true});addEventListener('pointerdown',takeControl,{passive:true});addEventListener('keydown',takeControl);
    addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);reduced.addEventListener('change',schedule);update();
    return()=>{cancelAnimationFrame(frame);removeEventListener('click',takeControl);removeEventListener('wheel',takeControl);removeEventListener('pointerdown',takeControl);removeEventListener('keydown',takeControl);removeEventListener('scroll',schedule);removeEventListener('resize',schedule);reduced.removeEventListener('change',schedule);};
  }, []);
  return (
    <div
      ref={root}
      className={s.story}
      data-common-ground-story=""
      data-gridbridge-story=""
    >
      {children}
    </div>
  );
}
