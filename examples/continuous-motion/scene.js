/* SPDX-License-Identifier: MIT. Original small study: one shell, causal cursor, drag/release. */
(function(){
 'use strict';
 const M=ContinuousMotion,canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
 const {duration:D,state,events:{UP}}=ContinuousStudy;
 function box(x,y,w,h,r,fill){ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();}
 function text(s,x,y,size,color='#20302d'){ctx.fillStyle=color;ctx.font=`500 ${size}px Arial,sans-serif`;ctx.fillText(s,x,y);}
 function draw(t){
  const s=state(t),g=s.shell,c=s.camera;
  ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha=1;ctx.fillStyle='#f2eee6';ctx.fillRect(0,0,1280,720);
  text('CONTINUITY / INTERACTION STUDY',50,60,17);text('One shape. A visible cause. A continuous response.',50,100,26);
  ctx.save();ctx.translate(c.x,c.y);ctx.scale(c.zoom,c.zoom);
  box(-g.w/2,-g.h/2,g.w,g.h,g.r,'#203f38'); // Exactly one uninterrupted shell.
  ctx.save();ctx.beginPath();ctx.roundRect(-g.w/2,-g.h/2,g.w,g.h,g.r);ctx.clip();
  ctx.globalAlpha=1-s.content;
  text('Open control',-113,8,25,'#fff8e9');text('→',88,9,27,'#edba65');
  ctx.globalAlpha=s.content;
  text('Drag to explore',-260,-85,25,'#fff8e9');text('×',261,-92,27,'#fff8e9');
  text('Hold, move, release',-260,-50,17,'#b6c9c1');
  box(-190,47,440,6,3,'#6d857c');
  box(-190,47,Math.max(1,s.thumb.x+190),6,3,'#edba65');
  ctx.beginPath();ctx.arc(s.thumb.x,50,s.dragging?13:10,0,2*Math.PI);ctx.fillStyle='#fff8e9';ctx.fill();
  text(s.dragging?'Attached to cursor':s.t>UP?'Velocity carried into spring':'Ready',-190,100,17,'#b6c9c1');
  ctx.restore();ctx.restore();
  // Cursor geometry is screen-sized; its TIP uses the same camera transform as the target.
  ctx.save();ctx.translate(s.pointerScreen.x,s.pointerScreen.y);const k=s.pressed?.88:1;ctx.scale(k,k);
  ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(0,29);ctx.lineTo(8,22);ctx.lineTo(15,35);ctx.lineTo(21,32);ctx.lineTo(14,20);ctx.lineTo(26,20);ctx.closePath();
  ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#20302d';ctx.lineWidth=2;ctx.stroke();ctx.restore();
  text('Illustration only · no external assets or sound',50,666,17);
  window.continuousMotionState=s;return s;
 }
 let time=0,playing=false,start=0;const scrub=document.querySelector('input'),button=document.querySelector('button');
 function seek(t){time=M.clamp(Number(t)||0,0,D);draw(time);if(scrub)scrub.value=time;return time;}
 window.__tl=Object.freeze({duration:()=>D,time:()=>time,pause(t){playing=false;if(t!==undefined)seek(t);if(button)button.textContent='Play';return this;}});
 window.__assetsReady=document.fonts.ready.then(()=>seek(0));
 const query=new URLSearchParams(location.search);if(query.get('controls')==='0')document.querySelector('nav').hidden=true;
 if(button)button.onclick=()=>{playing=!playing;if(time>=D)seek(0);start=performance.now()-time*1000;button.textContent=playing?'Pause':'Play';};
 if(scrub)scrub.oninput=()=>window.__tl.pause(Number(scrub.value));
 function tick(now){if(playing){seek((now-start)/1000);if(time>=D){playing=false;button.textContent='Play';}}requestAnimationFrame(tick);}
 window.__assetsReady.then(()=>{seek(query.has('t')?Number(query.get('t')):0);requestAnimationFrame(tick);});
})();
