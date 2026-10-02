/* SPDX-License-Identifier: MIT. Perspective and print poses are fully seekable. */
(function(){'use strict';const M=ThemeMotion,q=s=>document.querySelector(s),prints=[...document.querySelectorAll('.print')];window.drawTheme=function(t){
const arrive=M.ease(M.progress(t,.2,1.8));q('.contact-sheet').style.transform=`rotateX(${13-3*arrive}deg) rotateZ(${-6+Math.sin(t*.32)*.7}deg) translateY(${(1-arrive)*30}px)`;
prints.forEach((el,i)=>{const p=M.ease(M.progress(t,.25+i*.15,1.15));const focus=i===1?Math.sin(M.progress(t,2,5)*Math.PI)*24:0;el.style.opacity=String(p);el.style.transform=`translateZ(${focus}px) translateY(${(1-p)*30-focus*.3}px) rotate(${[-2,2,-1,2,-2,1][i]}deg)`;});
M.reveal(q('.archive-head'),t,.1,.9,12);q('.annotation').style.opacity=String(M.ease(M.progress(t,2.1,1.2)));q('.archive-stamp').style.opacity=String(M.ease(M.progress(t,2.8,1)));};})();
