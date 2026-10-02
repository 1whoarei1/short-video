/* SPDX-License-Identifier: MIT. Pure time-driven reference motion; no dependencies. */
(function(){'use strict';const M=window.ThemeMotion,q=s=>document.querySelector(s);
window.drawTheme=function(t){
M.reveal(q('.paper-copy'),t,.1,.9,22);
 [q('.disc-back'),q('.disc-front')].forEach((el,i)=>{const p=M.ease(M.progress(t,.3+i*.2,1));M.set(el,{opacity:p,transform:`scale(${.6+.4*p})`});});
 const g=M.ease(M.progress(t,.8,1.4));M.set(q('.garden'),{opacity:g,transform:`translateY(${(1-g)*170}px)`});
 const b=M.ease(M.progress(t,1.5,1.2));M.set(q('.bird'),{opacity:b,transform:`translate(${(1-b)*-80}px,${(1-b)*-45+Math.sin(t*1.1)*5}px) rotate(${-12+(1-b)*-12+Math.sin(t*.8)*2}deg)`});
 const s=M.ease(M.progress(t,2.7,.65));M.set(q('.sticker'),{opacity:s,transform:`scale(${.8+.2*s}) rotate(${13+(1-s)*20}deg)`});
 document.querySelectorAll('.steps span').forEach((el,i)=>{el.style.opacity=String(.35+.65*M.progress(t,1+i, .7));});
};
})();
