/* SPDX-License-Identifier: MIT
 * 山间来信: original 28-second composition by the current Codex author.
 * Asset reuse is documented in provenance.json. No existing preview is embedded.
 * Pure time sampling. Asset readiness is an explicit promise, not a timer.
 */
(function(){'use strict';
const c=document.querySelector('canvas').getContext('2d',{alpha:false});
const I=Object.fromEntries(['ridge','pine','fern','terrace','bird','grain'].map(id=>[id,document.getElementById(id)]));
const {clamp,smooth,mix}=ThemeMotion, {converge}=NarrativeMotion;
const R=(t,a,b)=>smooth(clamp((t-a)/(b-a))), PI=Math.PI;
const serif='"Noto Serif CJK SC","Songti SC",SimSun,serif';
const sans='"Noto Sans CJK SC","Microsoft YaHei",sans-serif';
let ready=false,last=0;
window.__assetsReady=Promise.all(Object.values(I).map(i=>i.decode())).then(()=>{ready=true;draw(last);});
const rect=(x,y,w,h,color)=>{c.fillStyle=color;c.fillRect(x,y,w,h);};
function line(points,color,width=1){c.beginPath();points.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));c.strokeStyle=color;c.lineWidth=width;c.stroke();}
function poly(points,color){c.beginPath();points.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));c.closePath();c.fillStyle=color;c.fill();}
function text(s,x,y,size=30,color='#e7ddc4',font=serif){c.fillStyle=color;c.font=`${size}px ${font}`;c.fillText(s,x,y);}
function img(id,x,y,w,h){if(ready)c.drawImage(I[id],x,y,w,h);}
function grain(x,y,w,h,a=.12){c.save();c.globalAlpha*=a;img('grain',x,y,w,h);c.restore();}
function hash(n){let v=Math.sin(n*34.321+11.82)*3914.343;return v-Math.floor(v);}
function landscape(t){
 const g=c.createLinearGradient(0,0,0,720);g.addColorStop(0,'#102b36');g.addColorStop(.5,'#aeb6ab');g.addColorStop(1,'#264d52');rect(0,0,1280,720,g);
 const sun=c.createRadialGradient(920,210,0,920,210,350);sun.addColorStop(0,'#f6e4b4a0');sun.addColorStop(.3,'#ecd6a339');sun.addColorStop(1,'#e4c68500');rect(420,-160,800,780,sun);
 c.fillStyle='#e8d9b7';c.beginPath();c.arc(920,210,33,0,7);c.fill();
 c.save();c.translate(-20-t*1.2,30);img('ridge',0,0,1390,720);c.restore();
 for(let j=0;j<7;j++){c.save();c.translate(-160+hash(j)*1500+t*(3+j),340+hash(j+50)*220);c.scale(5.5,.13);const fog=c.createRadialGradient(0,0,0,0,0,120);fog.addColorStop(0,'#dedac13c');fog.addColorStop(1,'#ddd9c000');rect(-120,-120,240,240,fog);c.restore();}
 c.save();c.globalAlpha=.85;c.translate(-165-t*4,190);c.rotate(-.12);img('pine',0,0,490,660);c.restore();
 c.save();c.translate(1420+t*3,310);c.scale(-1,1);c.rotate(.08);img('pine',0,0,410,580);c.restore();
 const vig=c.createRadialGradient(650,360,230,650,360,790);vig.addColorStop(0,'#09253200');vig.addColorStop(1,'#071c2caa');rect(0,0,1280,720,vig);
}
function memory(t,w,h){
 const enter=R(t,10.2,12.6),exit=1-R(t,18.6,20.7);
 c.save();c.globalAlpha*=enter*exit;
 // A new asymmetrical spread, not the contact-sheet pack's six-card layout.
 c.save();c.translate(-w*.235,-h*.015);c.rotate((-.055+.009*Math.sin(t*.25))*enter);
 c.shadowColor='#352c2348';c.shadowBlur=16;c.shadowOffsetY=8;rect(-w*.225,-h*.37,w*.45,h*.73,'#f7edce');c.shadowColor='transparent';
 img('terrace',-w*.211,-h*.346,w*.421,h*.567);
 text('那天的光，走得很慢。',-w*.185,h*.294,21,'#5b6052');
 c.globalAlpha=.65;rect(-w*.06,-h*.395,w*.15,h*.055,'#b39d6980');c.restore();
 const fernIn=R(t,11.1,13.5);c.save();c.translate(w*.025+18*(1-fernIn),h*.135+35*(1-fernIn));c.rotate(.105);c.globalAlpha*=fernIn;c.shadowColor='#473d3233';c.shadowBlur=12;c.shadowOffsetY=6;rect(-w*.058,-h*.29,w*.205,h*.405,'#e9dab8');c.shadowColor='transparent';img('fern',-w*.048,-h*.272,w*.185,h*.343);c.restore();
 c.save();c.globalAlpha*=R(t,12.2,14.2);text('寄给',w*.222,-h*.25,18,'#96967f',sans);text('忙碌的你',w*.222,-h*.151,36,'#274c49');text('捎一片山色，',w*.222,h*.033,26,'#5f695b');text('让心里有个',w*.222,h*.12,26,'#5f695b');text('可以停一停的地方。',w*.222,h*.207,26,'#5f695b');line([[w*.224,h*.28],[w*.412,h*.28]],'#aeb39b');c.restore();
 // A loose paper bird turns a generic folded-paper asset into a keepsake.
 const bp=R(t,13.3,15.7);c.save();c.translate(-w*.015+35*bp,h*.245);c.rotate(-.14-.06*bp);img('bird',-65,-65,130,130);c.restore();
 c.restore();
}
function letter(t){
 const flight=converge(t,{start:.7,duration:7,points:[[-65,450],[320,90],[930,660],[665,359]]});
 const unfold=R(t,8.1,11.3)*(1-R(t,19.0,22.0)),enlarge=R(t,7.1,10.5),land=R(t,21.2,24.2);
 const x=mix(flight.x,865,land),y=mix(flight.y,512,land);
 const w=mix(mix(195,1040,enlarge),382,land),h=w*.51;
 const angle=mix(mix(-.20+.10*Math.sin(t*1.3),-.012,enlarge),-.065,land);
 const closedH=h*.58,hh=mix(closedH,h,unfold);
 c.save();c.translate(x,y);c.rotate(angle);
 // The shadow's tightening is what makes the final letter visibly land.
 c.save();c.translate(12*(1-land),20*(1-land)+7);c.shadowBlur=mix(28,9,land);c.shadowColor='#08171370';rect(-w/2,-hh/2,w,hh,'#0b251525');c.restore();
 rect(-w/2,-hh/2,w,hh,'#e7dcbb');
 const face=c.createLinearGradient(-w/2,-hh/2,w/2,hh/2);face.addColorStop(0,'#fbf0d4');face.addColorStop(.7,'#e7dbba');face.addColorStop(1,'#d5c9a8');rect(-w/2,-hh/2,w,hh,face);
 grain(-w/2,-hh/2,w,hh,.27);
 // The same persistent sheet opens, contains the collage, then closes again.
 c.save();c.beginPath();c.rect(-w/2+4,-hh/2+4,w-8,hh-8);c.clip();memory(t,w,h);c.restore();
 c.save();
 poly([[-w/2,-hh/2],[0,-hh/2+hh*.56*(1-unfold)],[w/2,-hh/2]],'#d9ceb0');
 line([[-w/2,-hh/2],[0,-hh/2+hh*.56*(1-unfold)],[w/2,-hh/2]],'#aa9c7c80',1.2);
 poly([[-w/2,hh/2],[0,hh/2-hh*.56*(1-unfold)],[w/2,hh/2]],'#eee2c2');
 line([[-w/2,hh/2],[0,hh/2-hh*.56*(1-unfold)],[w/2,hh/2]],'#b0a38570');
 // Leaf-green seal keeps the envelope identifiable throughout the journey.
 c.globalAlpha=1-unfold;c.fillStyle='#49675b';c.beginPath();c.arc(0,hh*.015,w*.037,0,7);c.fill();
 c.strokeStyle='#ddce9f';c.lineWidth=.8;c.beginPath();c.arc(0,hh*.015,w*.027,0,7);c.stroke();
 text('山',-w*.014,hh*.015+w*.013,w*.03,'#eddfbc');c.restore();
 c.save();c.globalAlpha=unfold*.24;line([[-w*.15,-hh/2],[-w*.15,hh/2]],'#968e78');line([[w*.16,-hh/2],[w*.16,hh/2]],'#968e78');c.restore();
 c.restore();
 return {x,y,w,unfold,land};
}
function room(t){const p=R(t,20.5,23.5);c.save();c.globalAlpha=p;
 // Window and sill retain the originating landscape, now within reach.
 rect(0,0,1280,720,'#14373538');rect(0,0,65,720,'#153832');rect(1210,0,70,720,'#153832');rect(0,615,1280,105,'#a79d7f');
 const wood=c.createLinearGradient(0,580,0,720);wood.addColorStop(0,'#d5c7a0');wood.addColorStop(1,'#948b73');poly([[0,579],[1280,561],[1280,720],[0,720]],wood);
 for(let j=0;j<11;j++)line([[0,620+j*11],[1280,603+j*11]],'#726e5825');
 // Final landing plane raised into the image, rather than disappearing offscreen.
 poly([[565,452],[1170,447],[1260,640],[525,648]],'#b8ad8e');line([[565,452],[1170,447]],'#f0dfb9',3);
 c.restore();}
function draw(t){last=t;t=clamp(Number(t)||0,0,28);landscape(t);
 const mid=R(t,8.0,10.7)*(1-R(t,20.0,22.7));rect(0,0,1280,720,`rgba(14,29,28,${mid*.70})`);
 const opening=R(t,.6,1.8)*(1-R(t,5.5,7.5));c.save();c.globalAlpha=opening;text('山间来信',94,172,62);text('风起时，一封信离开了山谷。',98,228,24,'#dad8bc');line([[98,259],[225,259]],'#ceccb77a');c.restore();
 room(t);const pose=letter(t);
 const end=R(t,23.2,25.0);c.save();c.globalAlpha=end;text('山间来信',102,253,60);text('把远方，留在手边。',105,317,30);text('给自己，留一点空白。',106,363,21,'#dadcc6');line([[106,400],[272,400]],'#c3c8af90');c.restore();
 grain(0,0,1280,720,.055);
 c.save();c.globalAlpha=.65;text('原创虚构意象 · 无声短片',42,684,13,'#e7e5cf',sans);c.restore();
 window.mountainLetterState=Object.freeze({time:t,phase:t<8?'journey':t<19?'memory':t<23.2?'fold':'arrival',...pose});
}
window.drawTheme=draw;
})();
