window.__BEATS__=[{"text": "这里比较的是每天的摄入量，", "start": 0.0, "end": 3.0}, {"text": "五十克是研究比较单位。", "start": 3.0, "end": 5.5}];
window.__SEG__={"id": "05a_daily", "duration": 5.5, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
