window.__BEATS__=[{"text": "摄入量、持续时间和个人基础，", "start": 0.0, "end": 2.875}, {"text": "都影响实际风险。", "start": 2.875, "end": 4.5}];
window.__SEG__={"id": "03a_exposure", "duration": 4.5, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
