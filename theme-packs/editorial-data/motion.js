/* SPDX-License-Identifier: MIT. Each pose is computed from seconds, never accumulated. */
(function(){'use strict';const M=ThemeMotion,q=s=>document.querySelector(s),columns=[...document.querySelectorAll('.column')];
window.drawTheme=function(t){M.reveal(q('.headline'),t,.1,1,15);M.reveal(q('.margin-note'),t,2,1,10);M.reveal(q('.reading-mark'),t,1.7,.9,12);q('.floor').style.opacity=String(.2+.45*M.ease(M.progress(t,.5,1.8)));
columns.forEach((el,i)=>{const p=M.ease(M.progress(t,.35+i*.16,1.5)),settle=Math.sin(t*.65+i*.48)*3;const height=[.74,.9,.83,1,.88][i];el.style.opacity=String(p);el.style.transform=`translateY(${(1-p)*75+settle}px) scaleY(${height*(.58+.42*p)})`;});
q('.baseline').style.opacity=String(M.ease(M.progress(t,1.6,1)));};})();
