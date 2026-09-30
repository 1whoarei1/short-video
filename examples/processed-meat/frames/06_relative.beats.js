window.__BEATS__=[{"text": "也就是原有风险乘以一点一八。", "start": 0.0, "end": 2.625}, {"text": "这个数字描述日常摄入的差别，", "start": 2.625, "end": 5.208333333333333}, {"text": "不能拿来计算偶尔吃一顿的后果。", "start": 5.208333333333333, "end": 8.0}];
window.__SEG__={"id": "06_relative", "duration": 8.0, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
