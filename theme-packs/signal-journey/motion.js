/* SPDX-License-Identifier: MIT. Original projected SVG scene. No React, WebGL,
   timers, random state or physical-network claims. Geometry and time are remixable. */
(function(){'use strict';
const N=window.NarrativeMotion, q=s=>document.querySelector(s), NS='http://www.w3.org/2000/svg';
const requested=new URLSearchParams(location.search).get('variant');
const variant=requested==='route-map'?'route-map':'depth-flight';
q('.stage').dataset.variant=variant;q('.variant-name').textContent=variant==='route-map'?'02 / ROUTE MAP':'01 / DEPTH FLIGHT';
const colors=['#baffdc','#c0b6f4','#f2c891'];
const points={origin:[-465,0,-50],split:[-285,0,-50],a:[-5,-105,-110],b:[10,0,35],c:[-5,105,180],join:[270,0,0],end:[435,0,0]};
const links=[['origin','split',0,1.1,1.3],['split','a',0,2.5,2],['split','b',1,2.5,2],['split','c',2,2.5,2],['a','join',0,5.1,2.4],['b','join',1,5.1,2.4],['c','join',2,5.1,2.4],['join','end',0,8,1.6]];
function el(name,attrs,parent=q('.world')){const e=document.createElementNS(NS,name);Object.entries(attrs||{}).forEach(([k,v])=>e.setAttribute(k,v));parent.appendChild(e);return e;}
const planeDefs=[{x:-285,z:-50,title:'01 / ORIGIN',w:98,h:132},{x:0,z:35,title:'02 / EXPLORE',w:145,h:140},{x:270,z:0,title:'03 / GATHER',w:98,h:132}];
const planes=planeDefs.map(p=>{const g=el('g',{});return {...p,g,back:el('path',{class:'plane-edge',fill:'url(#glass)',opacity:.32},g),struts:el('path',{class:'plane-grid'},g),face:el('path',{class:'plane-edge',fill:'url(#glass)'},g),grid:el('path',{class:'plane-grid'},g),label:el('text',{class:'plane-label'},g)};});
const routeGroup=el('g',{}), routes=links.map(link=>{const g=el('g',{},routeGroup);return {link,base:el('path',{class:'route-base'},g),lit:el('path',{class:'route-light',stroke:colors[link[2]]},g)};});
const nodeGroup=el('g',{});const names={origin:'一个想法',split:'展开',a:'观察',b:'连接',c:'尝试',join:'汇合',end:'新的理解'};
const nodes=Object.entries(points).map(([id,p])=>({id,p,ring:el('circle',{class:'node',stroke:id==='b'?colors[1]:id==='c'?colors[2]:colors[0]},nodeGroup),core:el('circle',{fill:colors[id==='b'?1:id==='c'?2:0]},nodeGroup),label:el('text',{class:'node-label','text-anchor':'middle'},nodeGroup)}));
const moving=el('g',{});const packets=links.map(link=>{const g=el('g',{},moving);return {link,g,halo:el('circle',{r:24,fill:colors[link[2]],opacity:.16,filter:'url(#glow)'},g),token:el('rect',{x:-5,y:-5,width:10,height:10,rx:3,fill:colors[link[2]],stroke:'#effff7','stroke-width':.7},g)};});
const arrival=el('g',{}),arrivalRing=el('circle',{fill:'none',stroke:colors[0],'stroke-width':1},arrival),arrivalToken=el('image',{href:'assets/packet-token.svg',width:46,height:46,x:-23,y:-23},arrival);
const phaseData=[['01 / 发出','每一次探索，都从清晰的起点开始','保持同一份好奇，沿着路径向前。'],['02 / 分路','换几个角度，让理解逐渐丰富','观察、连接与尝试，各自带回新的发现。'],['03 / 汇合','不同的发现，可以在这里相遇','沿着各自的路径，把线索重新连接。'],['04 / 抵达','把发现汇在一起，让想法继续生长','下一段旅程，从更完整的理解出发。']];
const curve=(a,b)=>[a,[a[0]+(b[0]-a[0])*.52,a[1],a[2]],[b[0]-(b[0]-a[0])*.52,b[1],b[2]],b];
function cubic(c,t){const u=1-t;return [0,1,2].map(i=>u*u*u*c[0][i]+3*u*u*t*c[1][i]+3*u*t*t*c[2][i]+t*t*t*c[3][i]);}
function sample(c,project,end=1,start=0){const out=[];for(let i=0;i<=40;i++){const p=project(cubic(c,start+(end-start)*i/40));out.push(`${i?'L':'M'}${p.x.toFixed(3)},${p.y.toFixed(3)}`);}return out.join(' ');}
window.drawTheme=function(t){
const flat=variant==='route-map';const entry=N.smooth(N.phase(t,0,1.2));const inspect=N.smooth(N.phase(t,3.3,1.4))*(1-N.smooth(N.phase(t,6.1,1.5)));
const rx=flat?0:.34, ry=flat?0:-.23+.12*N.smooth(N.phase(t,0,8));const scale=(flat?1:.94)+inspect*(flat?.025:.11);
function project(v){let [x,y,z]=v;if(flat)z=0;const xx=x*Math.cos(ry)+z*Math.sin(ry),zz=-x*Math.sin(ry)+z*Math.cos(ry);const yy=y*Math.cos(rx)-zz*Math.sin(rx),z2=y*Math.sin(rx)+zz*Math.cos(rx);const p=1050/(1050+z2);return {x:640+(xx-inspect*18)*p*scale,y:365+(yy+25*(1-entry))*p*scale,s:p*scale,z:z2};}
planes.forEach((p,i)=>{const corners=[[-p.w,-p.h],[p.w,-p.h],[p.w,p.h],[-p.w,p.h]].map(([x,y])=>project([p.x+x,y,p.z]));const back=[[-p.w,-p.h],[p.w,-p.h],[p.w,p.h],[-p.w,p.h]].map(([x,y])=>project([p.x+x,y,p.z+45]));p.back.setAttribute('d',back.map((v,j)=>`${j?'L':'M'}${v.x},${v.y}`).join(' ')+'Z');p.struts.setAttribute('d',back.map((v,j)=>`M${v.x},${v.y}L${corners[j].x},${corners[j].y}`).join(' '));p.face.setAttribute('d',corners.map((v,j)=>`${j?'L':'M'}${v.x},${v.y}`).join(' ')+'Z');let d='';for(let v=-1;v<=1;v++){for(const ends of [[[p.x-p.w,v*p.h/2,p.z],[p.x+p.w,v*p.h/2,p.z]],[[p.x+v*p.w/2,-p.h,p.z],[p.x+v*p.w/2,p.h,p.z]]]){const [a,b]=ends.map(project);d+=`M${a.x},${a.y}L${b.x},${b.y}`;}}p.grid.setAttribute('d',d);p.label.textContent=p.title;p.label.setAttribute('x',corners[0].x+9);p.label.setAttribute('y',corners[0].y-13);p.g.style.opacity=String((.3+.7*entry)*(1-inspect*(i===1?0:.56)));});
routes.forEach(r=>{const [from,to,col,start,duration]=r.link,c=curve(points[from],points[to]),progress=N.phase(t,start,duration);r.base.setAttribute('d',sample(c,project));r.lit.setAttribute('d',sample(c,project,progress));r.lit.style.opacity=String(progress? .95:0);});
nodes.forEach(n=>{const p=project(n.p);const important=['a','b','c'].includes(n.id);const active=t>({origin:0,split:2.3,a:4.5,b:4.5,c:4.5,join:7.5,end:9.6}[n.id]);n.ring.setAttribute('cx',p.x);n.ring.setAttribute('cy',p.y);n.ring.setAttribute('r',(important?14:19)*p.s);n.ring.style.opacity=String(active?1:.45);n.core.setAttribute('cx',p.x);n.core.setAttribute('cy',p.y);n.core.setAttribute('r',(active?4.5:2.5)*p.s);n.core.style.opacity=String(active?1:.3);n.label.textContent=names[n.id];n.label.setAttribute('x',p.x);n.label.setAttribute('y',p.y+34*p.s);n.label.style.opacity=String(1-inspect*(important?0:.45));});
packets.forEach(r=>{const [from,to,col,start,duration]=r.link,progress=N.phase(t,start,duration),p=project(cubic(curve(points[from],points[to]),progress));r.g.setAttribute('transform',`translate(${p.x},${p.y}) scale(${p.s}) rotate(45)`);r.g.style.opacity=String(t>=start&&t<start+duration?1:0);});
const reached=N.smooth(N.phase(t,9.4,.7)),target=project(points.end);arrival.setAttribute('transform',`translate(${target.x},${target.y}) scale(${target.s})`);arrival.style.opacity=String(reached);arrivalToken.setAttribute('transform',`scale(${.7+.3*reached})`);arrivalRing.setAttribute('r',String(21+19*N.smooth(N.phase(t,9.6,1))));arrivalRing.style.opacity=String(1-N.smooth(N.phase(t,9.6,1.2)));
const index=t<2.5?0:t<5.1?1:t<8?2:3;const text=phaseData[index];q('.chapter').textContent=text[0];q('.caption h2').textContent=text[1];q('.detail').textContent=text[2];q('.progress').style.strokeDasharray='120';q('.progress').style.strokeDashoffset=String(120*(1-t/12));
};
window.SignalJourney=Object.freeze({variant,points,links,duration:12});
})();
