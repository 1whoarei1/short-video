window.__BEATS__=[{"text": "火腿、培根、腊肠，", "start": 0.0, "end": 2.4583333333333335}, {"text": "为什么会被列为一类致癌物？", "start": 2.4583333333333335, "end": 6.0}];
window.__SEG__={"id": "01_hook", "duration": 6.0, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
