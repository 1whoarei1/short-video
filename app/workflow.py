"""File-backed, revisioned local workflow. No hosted service or model credentials."""
import json, os, uuid, threading, copy, math, hashlib, shutil, time, subprocess
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
STAGES = ['requirements','research','narration','preview','production','export']
LABELS = ['需求沟通','资料调研','旁白文案','静态预览','视频制作','导出交付']
LOCK = threading.RLock()
def now(): return datetime.now(timezone.utc).isoformat()
@contextmanager
def process_lock(path):
 with LOCK:
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('a+b') as handle:
   handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0)
   if os.name=='nt':
    import msvcrt
    deadline=time.monotonic()+15
    while True:
     try: msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);break
     except OSError:
      if time.monotonic()>deadline:raise ValueError('项目正忙，请稍后重试')
      time.sleep(.05)
   else:
    import fcntl
    fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
   try: yield
   finally:
    if os.name=='nt':
     handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
    else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

class Workflow:
 def __init__(self, root):
  self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
  self.path = self.root/'.studio'/'workflow.json'
  self.path.parent.mkdir(parents=True, exist_ok=True)
  with process_lock(self.root/'.studio'/'write.lock'):
   if not self.path.exists():
    self._write({'schema':1,'title':'新视频项目','revision':0,'active':'requirements','selfReview':False,'updated':now(),'stages':{s:{'label':l,'version':1,'status':'draft','text':'','artifacts':[],'reviewNote':''} for s,l in zip(STAGES,LABELS)},'annotations':[],'history':[]})
 def _write(self,data):
  tmp=self.path.with_name('.'+uuid.uuid4().hex+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(tmp,self.path)
 def read(self):
  with LOCK: return json.loads(self.path.read_text(encoding='utf-8'))
 def asset(self,path):
  target=(self.root/path).resolve()
  if not target.is_relative_to(self.root) or not target.is_file(): raise ValueError('文件不存在或路径超出项目目录')
  return target
 def valid_media(self,artifact,video=False):
  p=self.asset(artifact['path']);ext=p.suffix.lower()
  with p.open('rb') as f: header=f.read(32)
  if not video:
   return (ext=='.png' and header.startswith(b'\x89PNG\r\n\x1a\n') and len(header)>=24 and header[12:16]==b'IHDR' and int.from_bytes(header[16:20],'big')>0 and int.from_bytes(header[20:24],'big')>0) or (ext in ('.jpg','.jpeg') and header.startswith(b'\xff\xd8\xff')) or (ext=='.webp' and header[:4]==b'RIFF' and header[8:12]==b'WEBP')
  signature=(ext=='.mp4' and header[4:8]==b'ftyp') or (ext=='.webm' and header[:4]==b'\x1a\x45\xdf\xa3')
  if not signature:return False
  probe=shutil.which('ffprobe')
  if probe:
   try:
    result=subprocess.run([probe,'-v','error','-select_streams','v:0','-show_entries','stream=codec_type,width,height','-show_entries','format=duration','-of','json',str(p)],capture_output=True,text=True,timeout=20)
    data=json.loads(result.stdout);stream=data.get('streams',[{}])[0]
    return result.returncode==0 and stream.get('codec_type')=='video' and stream.get('width',0)>0 and stream.get('height',0)>0 and float(data.get('format',{}).get('duration',0))>0
   except (ValueError,IndexError,OSError,subprocess.TimeoutExpired):return False
  return True
 def mutate(self, action, payload):
  with process_lock(self.root/'.studio'/'write.lock'):
   d=self.read()
   if 'revision' in payload and payload['revision'] != d['revision']: raise ValueError('项目已被其他窗口更新，请刷新后重试')
   before=copy.deepcopy(d); s=payload.get('stage',d['active'])
   if s not in STAGES: raise ValueError('未知阶段')
   stage=d['stages'][s]; idx=STAGES.index(s)
   def invalidate():
    stage['version']+=1; stage['status']='draft'; stage['reviewNote']=''; d['active']=s
    for later in STAGES[idx+1:]:
     ds=d['stages'][later]
     if ds['status']!='draft' or ds['text'] or ds['artifacts']: ds['status']='stale'
   if action=='save':
    value=str(payload.get('text',''))
    settings=payload.get('settings') if s=='requirements' else None
    if settings is not None:
     if not isinstance(settings,dict):raise ValueError('项目配置格式不正确')
     for key in ('width','height','fps','duration'):
      if not isinstance(settings.get(key),(int,float)) or not math.isfinite(settings[key]):raise ValueError('配置参数必须为有限数字')
     if not (128<=settings['width']<=7680 and 128<=settings['height']<=7680 and 1<=settings['fps']<=120 and 1<=settings['duration']<=3600):raise ValueError('画幅、帧率或时长超出合理范围')
    if value!=stage['text'] or (settings is not None and settings!=d.get('settings')): invalidate(); stage['text']=value
    if settings is not None:d['settings']=settings
    if s=='requirements' and payload.get('title'): d['title']=str(payload['title'])[:200]
   elif action=='artifact':
    p=str(payload['path']); source=self.asset(p)
    if stage['status'] in ('approved','review','stale'): invalidate()
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    dest=self.root/'_artifacts'/(digest+source.suffix.lower()); dest.parent.mkdir(exist_ok=True)
    if not dest.exists():shutil.copyfile(source,dest)
    stored=dest.relative_to(self.root).as_posix()
    stage['artifacts'].append({'id':uuid.uuid4().hex,'path':stored,'sourcePath':p,'sha256':digest,'label':str(payload.get('label',Path(p).name)),'role':str(payload.get('role','')),'version':stage['version'],'created':now()})
    stage['status']='draft'
   elif action=='submit':
    if idx and any(d['stages'][x]['status']!='approved' for x in STAGES[:idx]): raise ValueError('请先确认所有前置阶段；过期内容需要重新审核')
    if not stage['text'].strip() and not any(a['version']==stage['version'] for a in stage['artifacts']): raise ValueError('请先添加阶段内容或实际产物')
    if s in ['preview','production','export'] and not any(a['version']==stage['version'] and self.valid_media(a,video=s!='preview') for a in stage['artifacts']): raise ValueError('本阶段需要实际图片预览或可验证的视频产物，文本说明不能代替媒体文件')
    if stage['status']=='stale': raise ValueError('内容已过期，请先修订并保存，或用 revise 标明完成更新')
    stage['status']='review'; d['active']=s
   elif action=='approve':
    if stage['status']!='review': raise ValueError('请先提交审核')
    if payload.get('by')=='agent' and not d['selfReview']: raise ValueError('需要用户确认；仅显式自审测试模式允许代理批准')
    note=str(payload.get('note','')).strip()
    if payload.get('by')=='agent' and not note: raise ValueError('自审必须记录实际检查结果')
    stage['status']='approved'; stage['reviewNote']=note; stage['approvedBy']=payload.get('by','human'); stage['approvedAt']=now()
    d['active']=STAGES[min(idx+1,len(STAGES)-1)]
   elif action=='revise': invalidate()
   elif action=='mode': d['selfReview']=bool(payload.get('selfReview'))
   elif action=='annotation':
    asset=str(payload.get('asset','')); self.asset(asset)
    start=float(payload.get('start',0)); end=float(payload.get('end',start)); screenshot_time=float(payload.get('screenshotTime',start))
    if not math.isfinite(screenshot_time) or screenshot_time<0 or not math.isfinite(start) or not math.isfinite(end) or start<0 or end<start: raise ValueError('时间范围无效')
    box=payload.get('box')
    if box and (len(box)!=4 or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 or x>1 for x in box) or box[2]<=0 or box[3]<=0 or box[0]+box[2]>1.001 or box[1]+box[3]>1.001): raise ValueError('框选坐标必须位于画面内')
    comment=str(payload.get('comment','')).strip()
    if not comment: raise ValueError('请填写修改意见')
    shot=str(payload.get('screenshot',''))
    if shot: self.asset(shot)
    d['annotations'].append({'id':uuid.uuid4().hex,'stage':s,'version':int(payload.get('version',stage['version'])),'asset':asset,'screenshot':shot,'screenshotTime':screenshot_time,'start':start,'end':end,'box':box,'comment':comment,'created':now(),'resolved':False})
   elif action=='resolve':
    a=next((a for a in d['annotations'] if a['id']==payload.get('id')),None)
    if not a: raise ValueError('批注不存在')
    a['resolved']=bool(payload.get('resolved',True))
   elif action=='undo':
    cursor=d.get('undoCursor',d['revision'])
    versions=sorted(p for p in (self.root/'.studio'/'history').glob('*.json') if int(p.stem)<cursor)
    if not versions: raise ValueError('没有可撤销的版本')
    snapshot=json.loads(versions[-1].read_text(encoding='utf-8'))
    # Undo is itself a revision; never destroys snapshots or source files.
    d=snapshot; d['undoCursor']=int(versions[-1].stem); d['revision']=before['revision']; d['history']=before['history']; d['history'].append({'action':'restored','snapshot':versions[-1].name,'at':now()})
   else: raise ValueError('未知操作')
   hist=self.root/'.studio'/'history'; hist.mkdir(parents=True,exist_ok=True)
   (hist/f"{before['revision']:08}.json").write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
   
   if action!='undo': d.pop('undoCursor',None)
   d['revision']+=1; d['updated']=now(); d['history'].append({'action':action,'stage':s,'at':now(),'revision':d['revision']}); self._write(d); return d
