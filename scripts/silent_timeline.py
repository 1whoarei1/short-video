"""Build deterministic, explicitly timed subtitles and beats without speech services."""
import argparse, json, math, re
from pathlib import Path

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def build(project):
    p=Path(project).resolve()
    pj=json.loads((p/'project.json').read_text(encoding='utf-8'))
    items=json.loads((p/'narration.json').read_text(encoding='utf-8'))
    if isinstance(items,dict): items=items['items']
    ids=[i['id'] for i in items]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+',x) for x in ids):
        raise ValueError('Scene IDs must be unique safe filenames')
    order=pj.get('order') or ids
    if len(order)!=len(set(order)) or set(order)!=set(ids): raise ValueError('order must include each narration scene exactly once')
    fps=float(pj.get('fps',24))
    if not math.isfinite(fps) or not 1<=fps<=120: raise ValueError('fps must be 1..120')
    if float(pj.get('gap',0))!=0: raise ValueError('Silent pipeline requires gap=0; author holds inside scene durations')
    byid={i['id']:i for i in items}; layout={}; segments=[]; cursor_frames=0; srt=[]
    (p/'frames').mkdir(exist_ok=True)
    for sid in order:
        item=byid[sid]; duration=float(item['duration'])
        if not math.isfinite(duration) or duration<=0: raise ValueError('Positive duration required')
        frames=round(duration*fps)
        if frames<1: raise ValueError('Scene duration shorter than one frame')
        duration=frames/fps; start=cursor_frames/fps
        caps=item.get('captions')
        if caps is None:
            chunks=[s.strip() for s in item['text'].split('|') if s.strip()]
            if not chunks: raise ValueError('Subtitle text required')
            weight=sum(len(s) for s in chunks); elapsed=0; caps=[]
            for i,s in enumerate(chunks):
                end=frames if i==len(chunks)-1 else round((elapsed+len(s))/weight*frames)
                begin=round(elapsed/weight*frames); elapsed+=len(s)
                caps.append(dict(text=s,start=begin/fps,end=end/fps))
        blocks=[]; beats=[]; prev=0
        for c in caps:
            a,b=float(c['start']),float(c['end']); text=c['text']
            if not all(math.isfinite(x) for x in (a,b)) or not 0<=a<b<=duration+1e-7 or a<prev-1e-7 or not text.strip():
                raise ValueError(f'Invalid or overlapping caption in {sid}')
            prev=b
            blocks.append(dict(text=text,spoken=text,**{'from':round(a*fps),'to':round(b*fps)-1},size=int(c.get('size',44)),local_start_sec=a,global_start_sec=start+a,global_end_sec=start+b))
            beats.append(dict(text=text,start=a,end=b))
            srt.append((start+a,start+b,text))
        layout[sid]=dict(start_sec=start,duration_sec=duration)
        segments.append(dict(id=sid,duration_sec=duration,speech_end_sec=0,tail_silence_sec=0,blocks=blocks))
        js='window.__BEATS__='+json.dumps(beats,ensure_ascii=False)+';\nwindow.__SEG__='+json.dumps(dict(id=sid,duration=duration,speech_end=0,tail=0))+';\n'
        js+='''function _beat(t){const norm=s=>String(s).replace(/[\\s，。、！？；：!?;:|]/g,'');const found=window.__BEATS__.filter(x=>norm(x.text)===norm(t));if(found.length!==1)throw new Error('Beat must match exactly once: '+t);return found[0];}window.B=t=>_beat(t).start;window.Be=t=>_beat(t).end;\n'''
        (p/'frames'/f'{sid}.beats.js').write_text(js,encoding='utf-8')
        cursor_frames+=frames
    layout['_total']=dict(audio_duration_sec=0,video_duration_sec=cursor_frames/fps,gap_sec=0,fps=fps,total_frames=cursor_frames,mode='silent-author-timed')
    pj['audio_mode']='silent'; pj['order']=order; write(p/'project.json',pj)
    write(p/'layout.json',layout); write(p/'subs.json',dict(fps=fps,segments=segments,mode='silent-author-timed'))
    def stamp(s):
        ms=round(s*1000); return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    (p/'subtitles.srt').write_text('\n\n'.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{t}' for i,(a,b,t) in enumerate(srt,1))+'\n',encoding='utf-8')
    print(f'{len(order)} scenes, {cursor_frames/fps:.2f}s, {cursor_frames} frames; silent captions authored, no TTS')
    return layout
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('project');args=ap.parse_args();build(args.project)
