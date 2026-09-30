window.__BEATS__=[{"text": "相对增加约百分之十八，", "start": 0.0, "end": 2.25}, {"text": "不是增加十八个百分点，", "start": 2.25, "end": 4.458333333333333}, {"text": "也不是个人患癌概率。", "start": 4.458333333333333, "end": 6.5}];
window.__SEG__={"id": "06a_not_probability", "duration": 6.5, "speech_end": 0, "tail": 0};
function _beat(t){const norm=s=>String(s).replace(/[\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;
