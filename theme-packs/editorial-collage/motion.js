/* SPDX-License-Identifier: MIT. Pure time-driven reference motion; no dependencies. */
(function(){'use strict';const M=window.ThemeMotion,q=s=>document.querySelector(s);
window.drawTheme=function(t){
M.reveal(q('.article'),t,.12,.9,20);
 const p=M.ease(M.progress(t,.35,1.2));
 M.set(q('.clipping'),{opacity:p,transform:`translate(${(1-p)*70}px,${(1-p)*20}px) rotate(${(1-p)*10-1}deg)`});
 const n=M.ease(M.progress(t,1.7,.8));M.set(q('.note-card'),{opacity:n,transform:`translateY(${(1-n)*45}px) rotate(${-6+(1-n)*-12}deg)`});
 q('.red-circle').style.clipPath=`inset(0 ${100*(1-M.smooth(M.progress(t,2.6,1.1)))}% 0 0)`;
 [q('.tape-one'),q('.tape-two')].forEach((el,i)=>{el.style.opacity=String(M.progress(t,1.2+i*.3,.4));});
 q('.register').style.transform=`rotate(${Math.sin(t*.5)*5}deg)`;
};
})();
