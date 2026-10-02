/* SPDX-License-Identifier: MIT. Pure time-driven reference motion; no dependencies. */
(function(){'use strict';const M=window.ThemeMotion,q=s=>document.querySelector(s);
window.drawTheme=function(t){
M.reveal(q('.organic-copy'),t,.15,1.5,18);
 const p=M.ease(M.progress(t,.2,1.7));q('.organic-scene').style.opacity=String(p);
 q('.leaf-front').style.transform=`rotate(${-14+Math.sin(t*.5)*3}deg) scale(${.96+.04*p})`;
 q('.leaf-back').style.transform=`rotate(${28+Math.sin(t*.45+1)*4}deg) scale(.9)`;
 q('.sun-fleck').style.transform=`translate(${Math.sin(t*.4)*55}px,${Math.cos(t*.45)*25}px) scale(${.92+Math.sin(t*.5)*.08})`;
 q('.sun-fleck').style.opacity=String(.48+Math.sin(t*.6)*.12);
 q('.light-wash').style.transform=`rotate(${Math.sin(t*.3)*3}deg)`;
 M.reveal(q('.swatches'),t,2.2,1.2,12);
};
})();
