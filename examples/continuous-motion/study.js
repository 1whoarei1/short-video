/* SPDX-License-Identifier: MIT. Absolute-time scene model, reusable without a browser. */
(function(root){
 const M=typeof module==='object'?require('./motion.js'):root.ContinuousMotion;
 const D=6.5,HIT=.8,DOWN=2.4,UP=3.4,CLOSE=5.4;
 const targets={w:[[0,300],[HIT,520],[1.02,620],[CLOSE,300]],h:[[0,86],[HIT,230],[1.02,290],[CLOSE,86]],r:[[0,43],[HIT,30],[CLOSE,43]]};
 const drag=t=>M.hermite(t,{t:DOWN,x:-150,v:0},{t:UP,x:210,v:150});
 function move(t,a,b,p,q){const u=M.smooth((t-a)/(b-a));return{x:M.mix(p.x,q.x,u),y:M.mix(p.y,q.y,u)};}
 function pointer(t){
  if(t<=HIT)return move(t,0,.65,{x:250,y:130},{x:100,y:0});
  if(t<1.3)return{x:100,y:0};
  if(t<DOWN)return move(t,1.3,2.25,{x:100,y:0},{x:-150,y:50});
  if(t<=UP)return{x:drag(t).x,y:50};
  if(t<3.75)return{x:M.hermite(t,{t:UP,x:210,v:150},{t:3.75,x:260,v:0}).x,y:50-95*M.smooth((t-UP)/.35)};
  if(t<CLOSE)return move(t,4.1,5.15,{x:260,y:-45},{x:270,y:-100});
  return move(t,5.6,6.4,{x:270,y:-100},{x:240,y:140});
 }
 function state(t){
  t=M.clamp(t,0,D);
  const w=Math.max(1,M.track(t,targets.w).x),h=Math.max(1,M.track(t,targets.h).x);
  const r=M.clamp(M.track(t,targets.r).x,0,Math.min(w,h)/2);
  const camera={x:640,y:360,zoom:1+.12*M.smooth((t-1.3)/2)};
  const p=pointer(t),release=drag(UP);
  const thumb=t<DOWN?{x:-150,v:0}:t<=UP?drag(t):M.spring(t-UP,release.x,release.v,170);
  const content=M.smooth((t-1.02)/.25)*(1-M.smooth((t-CLOSE)/.1));
  return{t,shell:{w,h,r},camera,pointer:p,pointerScreen:M.toScreen(p,camera),thumb,content,
   pressed:(t>=HIT&&t<HIT+.1)||(t>=DOWN&&t<=UP)||(t>=CLOSE&&t<CLOSE+.1),dragging:t>=DOWN&&t<=UP};
 }
 const api=Object.freeze({duration:D,state,drag,targets,events:{HIT,DOWN,UP,CLOSE}});
 if(typeof module==='object')module.exports=api;else root.ContinuousStudy=api;
})(typeof window==='object'?window:globalThis);
