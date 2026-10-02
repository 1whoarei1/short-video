/* SPDX-License-Identifier: MIT. Optional, DOM-free narrative poses. No clock/state/randomness.
   All distances are caller-defined local units; all times are seconds. */
(function(root){'use strict';
const clamp=n=>Math.min(1,Math.max(0,Number.isFinite(n)?n:0));
const phase=(t,start,duration)=>clamp((t-start)/Math.max(.000001,duration));
const smooth=p=>{p=clamp(p);return p*p*(3-2*p);};
const lerp=(a,b,p)=>a+(b-a)*p;
function cutaway(t,{start=0,duration=1,axis='x',reverse=false}={}){const p=smooth(phase(t,start,duration)),v=100*(reverse?p:1-p);return {progress:p,clipPath:axis==='y'?`inset(0 0 ${v}% 0)`:`inset(0 ${v}% 0 0)`};}
function lens(t,{start=0,duration=1,from=[50,50,0],to=[50,50,35]}={}){const p=smooth(phase(t,start,duration)),[x,y,r]=from.map((n,i)=>lerp(n,to[i],p));return {x,y,r,clipPath:`circle(${r}% at ${x}% ${y}%)`};}
function focus(t,{start=0,duration=1,from=12,to=0,scaleFrom=1.06,scaleTo=1}={}){const p=smooth(phase(t,start,duration));return {filter:`blur(${lerp(from,to,p)}px)`,transform:`scale(${lerp(scaleFrom,scaleTo,p)})`};}
function converge(t,{start=0,duration=1,points=[[0,0],[0,0],[0,0],[0,0]]}={}){const p=smooth(phase(t,start,duration)),u=1-p;const at=i=>u*u*u*points[0][i]+3*u*u*p*points[1][i]+3*u*p*p*points[2][i]+p*p*p*points[3][i];return {x:at(0),y:at(1),progress:p,transform:`translate(${at(0)}px,${at(1)}px)`};}
function perspective(t,{start=0,duration=1,depth=900,from=[0,70,-160,55,-15],to=[0,0,0,0,0]}={}){const p=smooth(phase(t,start,duration)),v=from.map((n,i)=>lerp(n,to[i],p));return {progress:p,transform:`perspective(${depth}px) translate3d(${v[0]}px,${v[1]}px,${v[2]}px) rotateX(${v[3]}deg) rotateY(${v[4]}deg)`};}
root.NarrativeMotion=Object.freeze({phase,smooth,cutaway,lens,focus,converge,perspective});
})(window);
