/* SPDX-License-Identifier: MIT. Original analytic 2D compositing, not ray tracing or physical optics. */
(function(){'use strict';
const M=ThemeMotion,q=s=>document.querySelector(s),params=new URLSearchParams(location.search),stage=q('.stage');
const variant=params.get('variant')==='pearl-studio'?'pearl-studio':'spectral-nocturne';stage.dataset.variant=variant;
const number=(key,fallback,min,max)=>{const x=Number(params.get(key));return params.has(key)&&Number.isFinite(x)?M.clamp(x,min,max):fallback;};
// All creative controls are bounded, reusable and independent of playback history.
const config=Object.freeze({variant,spread:number('spread',1,.3,1.8),glow:number('glow',1,0,1.6),camera:number('camera',1,0,1.3)});window.prismaticConfig=config;
q('.variant-label').textContent=variant==='pearl-studio'?'PEARL STUDIO':'SPECTRAL NOCTURNE';
if(variant==='pearl-studio'){q('.kicker').textContent='A STUDY IN QUIET REFLECTION';q('h1').innerHTML='换个角度，<br><em>看见新颜色。</em>';q('.copy p').innerHTML='让目光慢下来，<br>看看边缘的微光。';q('.detail-glass img').src='assets/faceted-glass.svg';q('.detail-glass img').alt='Original editable geometric facet construction';q('.detail-window p').textContent='FACET / VECTOR CONSTRUCTION';}
const s=(t,a,d)=>M.smooth(M.progress(t,a,d));
window.drawTheme=function(seconds){const t=M.clamp(Number(seconds)||0,0,12),open=s(t,.1,1.65),pull=s(t,.3,3.6),light=s(t,2.7,1.6),macro=s(t,7,1.9),end=s(t,10.3,1.7),c=config.camera;
q('.world').style.transform=`translate(${(1-pull)*(-90)*c+macro*14*c}px,${(1-pull)*34*c-macro*9*c}px) scale(${1+(1-pull)*.59*c+macro*.045*c})`;
q('.aperture-top').style.transform=`scaleY(${1-open})`;q('.aperture-bottom').style.transform=`scaleY(${1-open})`;
q('.prism').style.transform=`translateY(${(1-pull)*24+Math.sin(t*.5)*3}px) rotate(${(1-pull)*-6+macro*1.3+(variant==='pearl-studio'?-4:0)}deg)`;
q('.surface-sweep').style.transform=`translateX(${(-35+65*s(t,3,4))}px)`;q('.surface-sweep').style.opacity=String((.12+.35*Math.sin(Math.PI*s(t,2.6,5.5)))*config.glow);
q('.incoming').style.opacity=String(light*.82*(1-end*.5)*config.glow);q('.incoming').style.transform=`rotate(${-3+7*s(t,3,4)}deg) scaleX(${.2+.8*light})`;
q('.outgoing').style.opacity=String(light*(variant==='pearl-studio'?.35:.8)*config.glow);q('.outgoing').style.transform=`rotate(${-5+9*s(t,4,5)}deg) scaleY(${config.spread*(.58+.42*light)})`;
q('.caustic').style.transform=`translate(${(-50+76*s(t,2,7))}px,${macro*7}px) rotate(${-8+5*pull}deg) scale(${.9+.15*light},${config.spread*(.7+.23*light)})`;
q('.caustic').style.opacity=String((.15+.55*light)*(variant==='pearl-studio'?.75:1)*config.glow);
q('.glint').style.opacity=String((.18+.82*Math.pow(Math.sin(Math.PI*s(t,2.4,6.9)),8))*config.glow);q('.glint').style.transform=`scale(${.65+.8*light})`;
q('.reflection').style.opacity=String((variant==='pearl-studio'?.1:.16)*open);q('.ground-shadow').style.opacity=String(.25+.35*pull);
M.reveal(q('.copy'),t,1.1,1.3,18);M.reveal(q('.phase'),t,1.6,.9,8);M.reveal(q('.specimen'),t,4.1,1,6);M.reveal(q('.detail-window'),t,7.1,1,10);
q('.phase-no').textContent=t<3?'01':t<7?'02':'03';q('.phase-title').textContent=t<3?'FIND THE EDGE':t<7?'RELEASE THE SPECTRUM':'LOOK A LITTLE CLOSER';q('.phase-track i').style.transform=`scaleX(${t/12})`;
};})();
