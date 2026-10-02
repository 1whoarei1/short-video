/* SPDX-License-Identifier: MIT.
 * Original deterministic scenic renderer. Time is the ONLY changing input.
 * No simulation stepping, network, libraries, random(), or accumulated state.
 * Layer profiles, atmosphere(), ridge(), river(), pine(), and camera() can be
 * borrowed individually. All coordinates refer to the reference 1280x720 stage.
 */
(function(){'use strict';
const stage=document.querySelector('.stage'),canvas=stage.querySelector('canvas'),c=canvas.getContext('2d',{alpha:false,willReadFrequently:true});
const moon=new URLSearchParams(location.search).get('variant')==='moonlit-valley';
stage.dataset.variant=moon?'moonlit-valley':'first-light';
const q=s=>stage.querySelector(s),clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)),smooth=v=>{v=clamp(v);return v*v*(3-2*v);},ramp=(t,a,b)=>smooth((t-a)/(b-a));
const hash=n=>{const v=Math.sin(n*127.1+311.7)*43758.5453123;return v-Math.floor(v);};
function noise(x,seed){const a=Math.floor(x),f=smooth(x-a);return hash(a+seed)*(1-f)+hash(a+1+seed)*f;}
function color(a,b,p){return a.map((v,i)=>Math.round(v+(b[i]-v)*p));}const rgb=(a,alpha=1)=>`rgba(${a.join(',')},${alpha})`;
const dawn={sky:[[16,39,54],[118,135,135],[242,192,127]],sun:[255,238,178],fog:[235,203,153],ridge:[[136,153,151],[100,135,138],[67,111,117],[37,82,88],[21,58,63],[12,37,42]]};
const night={sky:[[6,17,38],[38,68,92],[105,145,158]],sun:[216,238,243],fog:[141,181,186],ridge:[[82,116,138],[53,94,119],[33,73,100],[20,55,78],[11,36,55],[5,23,35]]};const P=moon?night:dawn;
const layers=[{y:389,a:77,z:.10,s:31},{y:429,a:103,z:.18,s:63},{y:474,a:129,z:.31,s:19},{y:526,a:154,z:.49,s:48},{y:601,a:193,z:.73,s:82},{y:745,a:221,z:1.02,s:13}];
function camera(t){return {travel:190*ramp(t,0,11.3),lift:21*ramp(t,1,9),zoom:1+.045*ramp(t,0,12)};}
function profile(x,L){const basin=Math.exp(-Math.pow((x-710)/330,2))*L.a*.56;const peaks=Math.max(0,1-Math.abs(x-245)/215)*L.a*.60+Math.max(0,1-Math.abs(x-1135)/240)*L.a*.76;return L.y+basin-peaks-L.a*(.35+.36*noise(x/227,L.s)+.20*noise(x/73,L.s+40)+.085*noise(x/24,L.s+71));}
function sky(t){const g=c.createLinearGradient(0,0,0,640);P.sky.forEach((v,i)=>g.addColorStop(i/2,rgb(v)));c.fillStyle=g;c.fillRect(0,0,1280,720);
 if(moon){for(let i=0;i<125;i++){const x=hash(i+400)*1280,y=hash(i+1300)*335,a=(.2+hash(i+2000)*.6)*(1-y/500);c.fillStyle=rgb([219,239,252],a);c.beginPath();c.arc(x,y,.45+hash(i+820)*.9,0,7);c.fill();}}
 const sx=916-18*ramp(t,0,12),sy=312-69*ramp(t,1,10),glow=c.createRadialGradient(sx,sy,2,sx,sy,410);glow.addColorStop(0,rgb(P.sun,.58));glow.addColorStop(.2,rgb(P.sun,.19));glow.addColorStop(1,rgb(P.sun,0));c.fillStyle=glow;c.fillRect(350,0,930,690);
 c.save();c.translate(sx,sy);c.globalCompositeOperation='screen';for(let i=0;i<7;i++){c.rotate(.17);const g=c.createLinearGradient(0,0,0,520);g.addColorStop(0,rgb(P.sun,.075));g.addColorStop(1,rgb(P.sun,0));c.fillStyle=g;c.beginPath();c.moveTo(-5,0);c.lineTo(-45,570);c.lineTo(45,570);c.lineTo(5,0);c.fill();}c.restore();
 c.fillStyle=rgb(P.sun);c.beginPath();c.arc(sx,sy,moon?35:47,0,Math.PI*2);c.fill();if(moon){c.fillStyle='rgba(102,140,156,.1)';for(let i=0;i<9;i++){c.beginPath();c.arc(sx-21+hash(i+30)*42,sy-23+hash(i+60)*46,3+hash(i+52)*7,0,7);c.fill();}}
 // Long low cloud brushstrokes: elliptical gradients, rather than CSS blur.
 for(let i=0;i<15;i++){const x=hash(i+66)*1450-100+t*(.7+i*.07),y=178+hash(i+95)*163;c.save();c.translate(x,y);c.scale(3.8,.1);const g=c.createRadialGradient(0,0,0,0,0,65);g.addColorStop(0,rgb(P.sun,moon?.07:.15));g.addColorStop(1,rgb(P.sun,0));c.fillStyle=g;c.fillRect(-65,-65,130,130);c.restore();}}
function ridge(L,index,cam){const shift=cam.travel*L.z,dy=cam.lift*L.z;
 c.save();c.translate(-shift,dy);c.beginPath();c.moveTo(-100,800);for(let x=-100;x<=1600;x+=5)c.lineTo(x,profile(x,L));c.lineTo(1600,800);c.closePath();const g=c.createLinearGradient(0,L.y-L.a,0,760);g.addColorStop(0,rgb(P.ridge[index]));g.addColorStop(1,rgb(color(P.ridge[index],[4,27,34],.42)));c.fillStyle=g;c.fill();c.save();c.clip();
 // Tangential erosion/faceted faces respond to slope, and remain attached to world terrain.
 for(let x=-100;x<1600;x+=9){let y=profile(x,L),slope=(profile(x+7,L)-profile(x-7,L))/14;const depth=35+hash(x+index*80)*210;c.strokeStyle=rgb(slope<0?P.sun:[4,23,33],Math.min(.10,Math.abs(slope)*.045)+.015);c.lineWidth=1+hash(x+50)*2;c.beginPath();c.moveTo(x,y+3);c.bezierCurveTo(x-12,y+depth*.28,x+19,y+depth*.65,x-7,y+depth);c.stroke();}
 for(let i=0;i<700;i++){const x=-100+hash(i+index*983)*1700,y=L.y-L.a+hash(i+index*829+71)*(800-L.y+L.a);c.fillStyle=rgb(hash(i+2)>.5?P.sun:[3,20,28],.035);c.fillRect(x,y,1+hash(i+90)*2,.7);}
 c.restore();
 if(index>=3){for(let i=0;i<53;i++){const x=-20+i*31+hash(i+L.s)*17,y=profile(x,L);pine(x,y,4+hash(i+index*200)*14*(index/4),rgb(P.ridge[index]));}}
 c.restore();
 // Backlit fog separates every layer and makes overlap/depth explicit.
 if(index<5){const y=L.y+20+dy,fg=c.createLinearGradient(0,y-42,0,y+84);fg.addColorStop(0,rgb(P.fog,0));fg.addColorStop(.45,rgb(P.fog,index<3?.13:.065));fg.addColorStop(1,rgb(P.fog,0));c.fillStyle=fg;c.fillRect(0,y-42,1280,126);}}
function pine(x,y,h,col){c.fillStyle=col;c.beginPath();c.moveTo(x,y-h);c.lineTo(x+h*.27,y-3);c.lineTo(x+h*.08,y-4);c.lineTo(x+h*.08,y+2);c.lineTo(x-h*.08,y+2);c.lineTo(x-h*.08,y-4);c.lineTo(x-h*.29,y-3);c.closePath();c.fill();}
function river(t,cam){c.save();const x=722-cam.travel*.27,y=467+cam.lift*.3;c.beginPath();c.moveTo(x,y);c.bezierCurveTo(x-55,502,x+64,523,x-9,551);c.bezierCurveTo(x-100,588,x-30,632,x-140,720);c.lineWidth=1.5;c.strokeStyle=rgb(P.sun,.52);c.stroke();for(let i=0;i<50;i++){const p=i/50,yy=y+p*242,xx=x+Math.sin(p*9)*22-p*p*115;const a=.1+hash(i+780)*.27;c.fillStyle=rgb(P.sun,a);c.fillRect(xx-4-p*10,yy,6+p*18,.5+hash(i+500));}c.restore();}
function atmosphere(t){c.save();c.globalCompositeOperation='screen';for(let i=0;i<43;i++){const x=(hash(i+333)*1440-80+t*(3+hash(i+43)*5))%1440,y=400+hash(i+212)*280-Math.sin(t*.22+i)*9,r=.4+hash(i+76)*1.9;c.fillStyle=rgb(P.sun,(.05+hash(i+632)*.29)*ramp(t,0,2));c.beginPath();c.arc(x,y,r,0,7);c.fill();}c.restore();const g=c.createRadialGradient(670,365,180,670,365,850);g.addColorStop(0,'rgba(0,7,14,0)');g.addColorStop(1,'rgba(0,7,14,.65)');c.fillStyle=g;c.fillRect(0,0,1280,720);}
if(moon){q('.overline').textContent='山间 · 月光习作';q('h1').textContent='让夜色慢下来';q('.scene-caption p').textContent='远处，也有微光。';q('.end-caption h2').textContent='月落山谷';q('.end-caption p').textContent='静静地，再看一会儿。';}
window.LandscapeScene=Object.freeze({camera,profile,noise,layerCount:layers.length,variant:stage.dataset.variant});
window.drawTheme=function(t){const cam=camera(t);c.setTransform(1,0,0,1,0,0);sky(t);c.save();c.translate(640,350);c.scale(cam.zoom,cam.zoom);c.translate(-640,-350);for(let i=0;i<layers.length;i++){ridge(layers[i],i,cam);if(i===3)river(t,cam);}c.restore();atmosphere(t);
 q('.branch-left').style.transform=`translate(${-cam.travel*.86}px,${cam.lift*1.7}px) rotate(-9deg) scale(1.1)`;q('.branch-right').style.transform=`translate(${cam.travel*.7}px,${cam.lift*1.3}px) scaleX(-1) rotate(-8deg)`;
 const a=ramp(t,.2,1.6)*(1-ramp(t,4.9,6.1)),b=ramp(t,7.1,8.5);q('.scene-caption').style.opacity=a.toFixed(5);q('.scene-caption').style.transform=`translateY(${(1-ramp(t,.2,1.6))*13}px)`;q('.end-caption').style.opacity=b.toFixed(5);q('.end-caption').style.transform=`translateY(${(1-b)*10}px)`;q('.shot-marker span').textContent=t<5.6?'01 / 远山':t<8?'02 / 穿过薄雾':'03 / 抵达微光';};
})();
