/* SPDX-License-Identifier: MIT. Seedless analytic poses; illustrative, not biological simulation. */
(function(){'use strict';const M=ThemeMotion,q=s=>document.querySelector(s);window.drawTheme=function(t){
const p=M.ease(M.progress(t,.15,1.6)),separate=M.smooth(M.progress(t,1.3,2.8));
q('.section').style.opacity=String(p);q('.section').style.transform=`scale(${.92+.08*p}) rotate(${-8+Math.sin(t*.32)*2}deg)`;
q('.membrane-back').style.transform=`translate(${separate*38}px,${-separate*35}px) rotate(${-20+separate*8}deg)`;q('.membrane-back').style.opacity=String(.42*p);
q('.membrane-front').style.transform=`translate(${-separate*57}px,${separate*45}px) rotate(${12-separate*9}deg)`;q('.membrane-front').style.opacity=String(.24+.13*p);
q('.scan-line').style.transform=`translateY(${40+Math.sin(t*.42)*150}px)`;q('.scan-line').style.opacity=String(.4*p);
M.reveal(q('.lab-title'),t,.1,1,12);['.callout-a','.callout-b','.callout-c'].forEach((s,i)=>M.reveal(q(s),t,1+i*.65,1,8));q('.leaders').style.opacity=String(M.ease(M.progress(t,1.1,1.8)));};})();
