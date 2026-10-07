/* SPDX-License-Identifier: MIT. Pure numerical building blocks, not a scene template. */
(function(root){
 'use strict';
 const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
 const mix=(a,b,p)=>a+(b-a)*p;
 const smooth=u=>{u=clamp(u);return u*u*u*(u*(u*6-15)+10);};
 function spring(t,x0,v0,target,omega=18,zeta=.78){
  if(!(omega>0&&zeta>0&&zeta<1))throw new RangeError('Use omega > 0 and 0 < zeta < 1');
  if(t<=0)return{x:x0,v:v0};
  const d=omega*Math.sqrt(1-zeta*zeta),a=x0-target,b=(v0+zeta*omega*a)/d;
  const e=Math.exp(-zeta*omega*t),c=Math.cos(d*t),s=Math.sin(d*t);
  return{x:target+e*(a*c+b*s),v:e*((-zeta*omega*a+d*b)*c+(-zeta*omega*b-d*a)*s)};
 }
 // Each retarget inherits the analytically evaluated position AND velocity.
 // keys: ordered [time, target], with the first target being the initial value.
 function track(t,keys,omega=18,zeta=.78){
  let state={x:keys[0][1],v:0},at=keys[0][0],target=state.x;
  for(let i=1;i<keys.length;i++){
   const [next,value]=keys[i];if(next<=at)throw new RangeError('Target times must increase');
   if(t<next)break;
   state=spring(next-at,state.x,state.v,target,omega,zeta);at=next;target=value;
  }
  return spring(Math.max(0,t-at),state.x,state.v,target,omega,zeta);
 }
 // Cubic Hermite uses endpoint velocities in units/second (not units/frame).
 function hermite(t,a,b){
  const dt=b.t-a.t;if(!(dt>0))throw new RangeError('Travel needs positive duration');
  const u=clamp((t-a.t)/dt),u2=u*u,u3=u2*u;
  return{x:(2*u3-3*u2+1)*a.x+(u3-2*u2+u)*dt*a.v+(-2*u3+3*u2)*b.x+(u3-u2)*dt*b.v,
   v:((6*u2-6*u)*a.x+(3*u2-4*u+1)*dt*a.v+(-6*u2+6*u)*b.x+(3*u2-2*u)*dt*b.v)/dt};
 }
 const toScreen=(p,c)=>({x:c.x+p.x*c.zoom,y:c.y+p.y*c.zoom});
 const toLocal=(p,c)=>({x:(p.x-c.x)/c.zoom,y:(p.y-c.y)/c.zoom});
 const api={clamp,mix,smooth,spring,track,hermite,toScreen,toLocal};
 if(typeof module==='object')module.exports=api;else root.ContinuousMotion=Object.freeze(api);
})(typeof window==='object'?window:globalThis);
