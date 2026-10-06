"""Agent-facing engine commands for the local video workflow (silent or optional Azure Speech)."""
import argparse, os, subprocess, sys, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/'vendor/html-explainer'
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['configure','synthesize','timeline','preview','render','layout','cover','style','bgm-prepare','soundtrack']);p.add_argument('project');p.add_argument('--scene');p.add_argument('--at',default='50');p.add_argument('--concurrency',type=int,default=2);p.add_argument('--source');p.add_argument('--cues');p.add_argument('--retain-source',action='append',default=[]);p.add_argument('--stem',action='append',default=[])
 # Rendering remains conservative unless explicitly requested; style advice never
 # selects a render profile, shutter setting, or the user's theme.
 p.add_argument('--profile');p.add_argument('--quality');p.add_argument('--shutter',type=float);p.add_argument('--samples',type=int);p.add_argument('--workers',type=int);p.add_argument('--recycle',type=int);p.add_argument('--shutter-only');p.add_argument('--resume',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--only',choices=['169','34','916']);a=p.parse_args()
 project=Path(a.project).resolve()
 if a.action=='configure':
  workflow=json.loads((project/'.studio/workflow.json').read_text(encoding='utf-8'))
  settings=workflow.get('settings',{})
  target=project/'project.json'
  config=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {'slug':project.name,'lang':'zh','order':[],'progress':True}
  before=dict(config)
  for key,default in [('width',1920),('height',1080),('fps',24)]:config[key]=int(settings.get(key,default))
  mode=settings.get('audio_mode','silent')
  if mode not in ('silent','azure','edge'):raise ValueError('Unknown audio_mode')
  config.update(gap=0,audio_mode=mode,provider=mode if mode!='silent' else 'none',azure_voice=settings.get('azure_voice','zh-CN-YunfanMultilingualNeural'),azure_rate=settings.get('azure_rate','0%'),edge_voice=settings.get('edge_voice','zh-CN-YunxiNeural'),edge_rate=settings.get('edge_rate','0%'))
  from soundtrack import DEFAULTS
  config.update({key:settings.get(key,value) for key,value in DEFAULTS.items()})
  if before != config:
   from azure_tts import invalidate
   # Music-only changes do not erase measured narration or alter scene timing.
   if any(before.get(k)!=config.get(k) for k in ('width','height','fps','audio_mode','azure_voice','azure_rate','edge_voice','edge_rate')):invalidate(project)
   (project/'audio/soundtrack.json').unlink(missing_ok=True)
  target.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  (project/'frames').mkdir(exist_ok=True);(project/'assets').mkdir(exist_ok=True)
  shutil.copy2(VENDOR/'assets/gsap.min.js',project/'assets/gsap.min.js')
  # Optional composable primitives; copying a library does not impose a scene.
  if not (project/'assets/motion.js').exists():shutil.copy2(VENDOR/'assets/motion.js',project/'assets/motion.js')
  print('Engine dimensions/fps synchronized. Author narration duration, scenes and style from the approved brief.');return 0
 if not (project/'project.json').is_file():raise SystemExit('Need engine project.json in the selected video workspace')
 env=os.environ.copy();env['HTML_EXPLAINER_ROOT']=str(VENDOR)
 config=json.loads((project/'project.json').read_text(encoding='utf-8'))
 mode=config.get('audio_mode','silent')
 if mode not in ('silent','azure','edge'):raise ValueError('Unknown audio_mode')
 if a.action in ('preview','render','layout','soundtrack'):
  from video_contract import validate_audio
  validate_audio(project, require_mix=a.action=='render')
 if a.action=='bgm-prepare':
  from soundtrack import prepare
  print(json.dumps(prepare(project,a.source,a.cues,a.retain_source,a.stem),ensure_ascii=False,indent=2));return 0
 if a.action=='soundtrack':
  from soundtrack import mix
  print(json.dumps(mix(project),ensure_ascii=False,indent=2));return 0
 if a.action=='style':
  cmd=[sys.executable,str(VENDOR/'scripts/style_director.py'),'--project',str(project)]
  if a.dry_run:cmd+=['--dry-run']
 elif a.action=='cover':
  cmd=['node',str(VENDOR/'scripts/check_cover.mjs'),str(project)]
  if a.only:cmd+=['--only',a.only]
 elif a.action=='synthesize':
  if mode=='silent':raise ValueError('Select Azure or Edge audio mode and run configure first')
  cmd=[sys.executable,str(ROOT/'scripts/azure_tts.py'),str(project)]
 elif a.action=='timeline':cmd=[sys.executable,str(ROOT/('scripts/audio_timeline.py' if mode!='silent' else 'scripts/silent_timeline.py')),str(project)]
 elif a.action=='preview':
  cmd=['node',str(VENDOR/'scripts/peek_frame.mjs'),str(project)]
  cmd+=([a.scene] if a.scene else ['--all'])+['--at',a.at]
 elif a.action=='layout':cmd=['node',str(VENDOR/'scripts/check_layout.mjs'),str(project)]
 else:
  cmd=['node',str(VENDOR/'scripts/render_video.mjs'),str(project),'--concurrency',str(max(1,a.concurrency))]
  if a.profile is None:cmd+=['--jpeg','--jpeg-quality','95','--crf','18','--preset','medium']
  for key in ('profile','quality','shutter','samples','workers','recycle','shutter_only'):
   value=getattr(a,key)
   if value is not None:cmd+=['--'+key.replace('_','-'),str(value)]
  if a.resume:cmd+=['--resume']
 return subprocess.run(cmd,env=env).returncode
if __name__=='__main__':raise SystemExit(main())
