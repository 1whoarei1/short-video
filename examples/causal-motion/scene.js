/* Original drawing/composition. HXM numerical motions: MIT (c) 2026 Moh,
 * ../../vendor/html-explainer/LICENSE. No timers or accumulated draw state. */
(function () {
  'use strict';
  const H = window.HXM, stage = document.querySelector('.stage');
  const ctx = stage.querySelector('canvas').getContext('2d');
  const offset = Number(stage.dataset.offset || 0);
  const css = getComputedStyle(document.documentElement);
  const color = name => css.getPropertyValue('--' + name).trim();
  const ink = color('ink'), paper = color('paper'), accent = color('accent');
  const x = [480, 700, 920], heights = [110, 210, 290], hits = [2, 2.8, 3.6];
  const camera = t => H.camTrack(t, [{t:0,x:640,y:360,zoom:1}, {t:4.5,x:640,y:360,zoom:1}, {t:5.5,x:660,y:346,zoom:1.04}, {t:10,x:660,y:346,zoom:1.04}]);
  function subject(t) {
    if (t < 2) return H.arcHop(t, .35, 2, {x:205,y:415}, {x:x[0],y:450}, {height:170});
    if (t < 2.8) return H.arcHop(t, 2, 2.8, {x:x[0],y:450}, {x:x[1],y:350}, {height:100});
    if (t < 3.6) return H.arcHop(t, 2.8, 3.6, {x:x[1],y:350}, {x:x[2],y:270}, {height:95});
    // The same subject crosses the 5s scene boundary and becomes a cause marker.
    return H.arcHop(t, 4.5, 6.5, {x:x[2],y:270}, {x:815,y:290}, {height:65});
  }
  function text(value, px, py, size, fill, alpha=1, weight=600) {
    ctx.globalAlpha = alpha; ctx.fillStyle = fill;
    ctx.font = `${weight} ${size}px Arial, 'Microsoft YaHei', sans-serif`;
    ctx.fillText(value, px, py); ctx.globalAlpha = 1;
  }
  function draw(local) {
    const t = H.clamp(local, 0, Number(stage.dataset.duration)) + offset;
    const dark = H.tween(t, 4.5, 5.5, H.ease.smoother);
    ctx.setTransform(1,0,0,1,0,0); ctx.globalAlpha=1;
    ctx.fillStyle=paper;ctx.fillRect(0,0,1280,720);
    ctx.globalAlpha=dark;ctx.fillStyle=ink;ctx.fillRect(0,0,1280,720);ctx.globalAlpha=1;
    const foreground = dark < .5 ? ink : paper;
    text('MOTION STUDY / 01',64,62,16,foreground,.7,500);
    const intro = H.riseWord(t,.05,{dist:18});
    text('一个点，带出变化',64,139+intro.y,49,foreground,intro.op);
    text('示意图 · 数字与因果均为动画演示',64,179,19,foreground,.65,400);
    const mat=H.layerMatrix(camera(t),{W:1280,H:720});ctx.setTransform(...mat);
    ctx.strokeStyle=foreground;ctx.lineWidth=2;ctx.globalAlpha=.32;
    ctx.beginPath();ctx.moveTo(390,560);ctx.lineTo(1040,560);ctx.stroke();ctx.globalAlpha=1;
    const current=[];
    for(let i=0;i<3;i++) {
      // A visible landing mark triggers each bar; it is an illustration, not physics.
      ctx.globalAlpha=.28;ctx.strokeStyle=foreground;ctx.lineWidth=2;
      ctx.beginPath();ctx.moveTo(x[i]-18,560-heights[i]);ctx.lineTo(x[i]+18,560-heights[i]);ctx.stroke();ctx.globalAlpha=1;
      const p=H.clamp(H.spring(t-hits[i],.72,13));
      const h=heights[i]*p;current.push(h);
      ctx.globalAlpha=i===0?.45:1;ctx.fillStyle=i===0?foreground:accent;
      ctx.fillRect(x[i]-45,560-h,90,h);ctx.globalAlpha=1;
      text(['起点','触发','结果'][i],x[i]-28,600,24,foreground,1,500);
      if(t>=hits[i]+.4) text(['100','190','264'][i],x[i]-29,540-h,24,foreground);
    }
    // Baseline stays in place. The path grows on the same graph, rather than replacing it.
    const path=H.tween(t,5.2,6.4,H.ease.smoother);
    ctx.strokeStyle=accent;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(480,450);
    ctx.lineTo(H.lerp(480,815,path),H.lerp(450,290,path));ctx.stroke();
    const dot=subject(t),hit=H.landHit(t,hits.findLast(v=>v<=t) || 2);
    ctx.save();ctx.translate(dot.x,dot.y);ctx.scale(hit.sx,hit.sy);
    ctx.fillStyle=accent;ctx.beginPath();ctx.arc(0,0,17,0,Math.PI*2);ctx.fill();ctx.restore();
    const note=H.riseWord(t,6.4,{dist:14});
    text('沿着变化，标出原因',660,210+note.y,27,foreground,note.op);
    ctx.globalAlpha=note.op;ctx.strokeStyle=foreground;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(815,246);ctx.lineTo(815,268);ctx.stroke();ctx.globalAlpha=1;
    ctx.setTransform(1,0,0,1,0,0);
    const end=H.riseWord(t,8.2,{dist:16});
    text('变化从哪里来，画面里看得见',64,668+end.y,32,foreground,end.op);
    window.causalMotionState={time:t,subject:dot,bars:current,camera:camera(t),dark,contactTimes:hits};
  }
  window.drawTheme=draw;
  window.__motion=(a,b)=>{
    const t0=offset+a,t1=offset+b,p=subject(t0),q=subject(t1);
    return Math.hypot(p.x-q.x,p.y-q.y)+H.screenTravel(camera(t0),camera(t1),camera((t0+t1)/2),{W:1280,H:720});
  };
  window.__meta={dur:Number(stage.dataset.duration),fps:24,w:1280,h:720};
  window.__assetsReady=document.fonts.ready.then(()=>draw(0));
})();
