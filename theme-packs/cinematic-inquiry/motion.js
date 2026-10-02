/* SPDX-License-Identifier: MIT. Seek-safe three-act micro-story. */
(function(){'use strict';const M=ThemeMotion,N=NarrativeMotion,q=s=>document.querySelector(s),variant=new URLSearchParams(location.search).get('variant');window.drawTheme=t=>{
const inspect=N.smooth(N.phase(t,2.2,1.6)),connect=N.smooth(N.phase(t,5.2,2)),settle=N.smooth(N.phase(t,7.2,1.2));
M.reveal(q('.headline'),t,.15,1,15);
document.querySelectorAll('.fragment').forEach((el,i)=>{const pose=N.perspective(t,{start:.2+i*.25,duration:1.5,from:[0,90,-160,35,(i-1)*22],to:[0,0,0,0,(i-1)*-4]});el.style.transform=pose.transform;el.style.opacity=String(pose.progress*(1-inspect*.72));el.style.filter=N.focus(t,{start:2.2,duration:1.5,from:0,to:3,scaleFrom:1,scaleTo:1}).filter;});
const detail=q('.detail');detail.style.clipPath=N.lens(t,{start:2.2,duration:2,from:[50,50,0],to:[50,50,variant==='wide'?75:43]}).clipPath;detail.style.opacity=String(inspect*(1-connect*.42));detail.style.transform=`scale(${1+inspect*.08})`;
q('.lens-ring').style.opacity=String(inspect*(1-connect));q('.lens-ring').style.transform=`scale(${.7+.7*inspect})`;
q('.connections').style.clipPath=N.cutaway(t,{start:5.1,duration:2,axis:'y'}).clipPath;q('.connections').style.opacity=String(connect);
[[[250,376],[330,540],[485,565],[640,493]],[[640,320],[570,410],[590,455],[640,493]],[[1030,370],[920,535],[790,560],[640,493]]].forEach((points,i)=>{const el=q(['.point-a','.point-b','.point-c'][i]);el.style.transform=N.converge(t,{start:5.3+i*.18,duration:2,points}).transform;el.style.opacity=String(connect*(1-settle));});
q('.ending').style.opacity=String(settle);q('.ending').style.transform=`translateY(${12*(1-settle)}px)`;q('.chapter').textContent=t<2.2?'01 / 观察':t<5.2?'02 / 聚焦':'03 / 连接';};})();
