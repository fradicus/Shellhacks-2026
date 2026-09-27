import geo from "./illustration-geography.json";
import s from "./landing.module.css";

// The supplied design's illustrative geography is never used by the matching engine.
const corridors = [
  ["MIA", "FLL", "WPB", "DAB", "JAX", "SAV", "FLO", "FAY", "RIC"],
  ["TPA", "OCA", "VLD", "MCN", "ATL", "CHA", "KNX"],
  ["JAX", "TLH", "PNS", "MOB", "GPT", "MSY"],
  ["MGM", "ATL", "GSP", "CLT", "GSO", "RDU"],
  ["JAN", "MER", "BHM", "ATL", "AUG", "COL", "FLO"],
  ["CHS", "COL", "GSP", "AVL"], ["MOB", "MGM", "BHM", "HSV", "NSH"],
  ["MEM", "NSH", "KNX", "AVL", "WS", "GSO", "RDU", "ILM"],
  ["MCN", "SAV"], ["NSH", "CHA", "ATL"], ["CHS", "SAV"],
];
const cities = geo.cities as Record<string, number[]>;
const names: Record<string, string> = {ATL:"Atlanta", SAV:"Savannah", COL:"Columbia", CHS:"Charleston", CLT:"Charlotte", JAX:"Jacksonville", NSH:"Nashville", BHM:"Birmingham", ORL:"Orlando", MIA:"Miami"};

export function NetworkIllustration() {
  return (
    <svg className={s.networkSvg} viewBox="150 40 760 700" fill="none" aria-hidden="true">
      {geo.states.map(state => <path key={state.c} d={state.r.map(r => `M${r[0]},${r[1]} ${Array.from({length:r.length/2-1},(_,i)=>`L${r[i*2+2]},${r[i*2+3]}`).join(" ")}Z`).join(" ")} fill={state.c === "GA" || state.c === "SC" ? "#161a20" : "#0b0d10"} stroke="#292c32" strokeWidth=".8" />)}
      {corridors.map((route,i)=><polyline key={i} points={route.map(c=>cities[c].join(",")).join(" ")} stroke="#ffe2b0" strokeOpacity=".28" strokeWidth="1.3"/>)}
      {corridors.slice(0,6).map((route,i)=><polyline className={s.networkFlow} style={{animationDelay:`-${i*1.7}s`}} key={i} points={route.map(c=>cities[c].join(",")).join(" ")} stroke="#ffe2b0" strokeWidth="2.5" strokeDasharray="3 190"/>)}
      <circle cx="606" cy="299" r="38" fill="#2997ff" fillOpacity=".07" stroke="#2997ff" strokeOpacity=".45"/>
      <circle cx="640" cy="280" r="38" fill="#2997ff" fillOpacity=".07" stroke="#2997ff" strokeOpacity=".45"/>
      <path d="M606 299 Q614 264 640 280" stroke="#2997ff" strokeWidth="2"/>
      {["606,299","640,280"].map(p=><circle key={p} cx={p.split(",")[0]} cy={p.split(",")[1]} r="3.5" fill="#e5f3ff"/>)}
      {Object.entries(names).map(([key,name])=><g key={key}><circle cx={cities[key][0]} cy={cities[key][1]} r="2.7" fill="#ffe2b0"/><text x={cities[key][0]+8} y={cities[key][1]-8} fill="#9c9da4" fontSize="11" fontFamily="sans-serif">{name}</text></g>)}
      <text x="448" y="413" fill="#61666e" fontSize="11" letterSpacing="5">GEORGIA</text>
      <text x="661" y="228" fill="#61666e" fontSize="10" letterSpacing="3">S. CAROLINA</text>
    </svg>
  );
}
