/* SPDX-License-Identifier: MIT. Pure time-driven reference motion; no dependencies. */
(function(){'use strict';const M=window.ThemeMotion,q=s=>document.querySelector(s);
window.drawTheme=function(t){
const hero=q('.hero'), product=q('.product');
 M.reveal(q('.copy'),t,.12,.9,25);M.reveal(q('.detail'),t,2.3,.75,18);
 const entry=M.ease(M.progress(t,.35,1.6));
 M.set(product,{opacity:entry,transform:`translateY(${(1-entry)*65}px) rotate(${(1-entry)*-7}deg)`});
 M.set(hero,{transform:`translateY(${Math.sin(t*.8)*5}px)`});
 [q('.callout-a'),q('.callout-b')].forEach((el,i)=>M.reveal(el,t,1.6+i*.8,.65,12));
 q('.orbit-a').style.transform=`rotate(${t*4}deg) scale(${.98+Math.sin(t*.7)*.02})`;
 q('.orbit-b').style.transform=`rotate(${-t*3}deg)`;
 q('.studio-halo').style.opacity=String(.75+Math.sin(t*.7)*.2);
};
})();
