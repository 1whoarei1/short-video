/* SPDX-License-Identifier: MIT. Pure time-driven reference motion; no dependencies. */
(function(){'use strict';const M=window.ThemeMotion,q=s=>document.querySelector(s);
window.drawTheme=function(t){
const a=M.ease(M.progress(t,.05,.9)),b=M.ease(M.progress(t,.4,1.05));
 M.set(q('.word-a'),{opacity:a,transform:`translateX(${(1-a)*-100}px) scaleX(${.86+.14*a})`});
 M.set(q('.word-b'),{opacity:b,transform:`translateX(${(1-b)*150}px)`});
 const r=M.ease(M.progress(t,1,1.2));M.set(q('.poster-mark'),{opacity:r,transform:`scale(${.5+.5*r}) rotate(${t*9}deg)`});
 M.reveal(q('.poster-annotation'),t,1.8,.7,20);
 q('.ticker div').style.transform=`translateX(${-t*36}px)`;
 const k=M.ease(M.progress(t,1.3,.6));q('.ticker').style.opacity=String(k);
 q('.count').textContent=t<2.5?'01 / 03':t<5?'02 / 03':'03 / 03';
};
})();
