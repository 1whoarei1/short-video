window.__BEATS__=[{"text": "红肉按来源定义，", "start": 0.0, "end": 1.7083333333333333}, {"text": "加工肉按处理方式定义。", "start": 1.7083333333333333, "end": 4.0}, {"text": "两者可以重叠。", "start": 4.0, "end": 5.5}];
window.__SEG__={"id": "04a_overlap", "duration": 5.5, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
