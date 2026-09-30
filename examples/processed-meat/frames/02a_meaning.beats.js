window.__BEATS__=[{"text": "一类，表达的是证据的确定性。", "start": 0.0, "end": 4.5}];
window.__SEG__={"id": "02a_meaning", "duration": 4.5, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
