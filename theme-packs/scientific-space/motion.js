/* SPDX-License-Identifier: MIT. Pure time-driven reference motion; no dependencies. */
(function(){'use strict';const M=window.ThemeMotion,q=s=>document.querySelector(s);
window.drawTheme=function(t){
M.reveal(q('.science-copy'),t,.1,.95,20);
 const p=M.ease(M.progress(t,.3,1.5));M.set(q('.atlas'),{opacity:p,transform:`scale(${.88+.12*p})`});
 const draw=M.smooth(M.progress(t,1,3));q('.orbit-path path').style.strokeDashoffset=String(1500*(1-draw));
 const path=q('.orbit-path path'),pt=path.getPointAtLength(path.getTotalLength()*((t*.1)%1));
 q('.orbit-path circle').setAttribute('cx',pt.x);q('.orbit-path circle').setAttribute('cy',pt.y);
 q('.radar').style.transform=`rotate(${t*18}deg)`;
 M.reveal(q('.coordinate-a'),t,1.8,.6,8);M.reveal(q('.coordinate-b'),t,2.3,.6,8);
 M.reveal(q('.spectrum'),t,3,.75,18);q('.spectrum img').style.clipPath=`inset(0 ${100*(1-M.progress(t,3.2,1.8))}% 0 0)`;
 q('.phase').textContent=t<3?'PHASE / TRACE':t<5.5?'PHASE / COMPARE':'PHASE / UNDERSTAND';
};
})();
