"""Agent-facing engine commands for the local video workflow (silent or optional Azure Speech)."""
import argparse, os, subprocess, sys, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/'vendor/html-explainer'
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['configure','synthesize','timeline','preview','render','layout']);p.add_argument('project');p.add_argument('--scene');p.add_argument('--at',default='50');p.add_argument('--concurrency',type=int,default=2);a=p.parse_args()
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
  config.update(gap=0,audio_mode=mode,provider=mode if mode!='silent' else 'none',azure_voice=settings.get('azure_voice','zh-CN-XiaoxiaoNeural'),azure_rate=settings.get('azure_rate','0%'),edge_voice=settings.get('edge_voice','zh-CN-YunxiNeural'),edge_rate=settings.get('edge_rate','0%'))
  if before != config:
   from azure_tts import invalidate
   invalidate(project)
  target.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  (project/'frames').mkdir(exist_ok=True);(project/'assets').mkdir(exist_ok=True)
  shutil.copy2(VENDOR/'assets/gsap.min.js',project/'assets/gsap.min.js')
  print('Engine dimensions/fps synchronized. Author narration duration, scenes and style from the approved brief.');return 0
 if not (project/'project.json').is_file():raise SystemExit('Need engine project.json in the selected video workspace')
 env=os.environ.copy();env['HTML_EXPLAINER_ROOT']=str(VENDOR)
 config=json.loads((project/'project.json').read_text(encoding='utf-8'))
 mode=config.get('audio_mode','silent')
 if mode not in ('silent','azure','edge'):raise ValueError('Unknown audio_mode')
 if a.action in ('preview','render','layout') and mode!='silent':
  from audio_timeline import validate_ready
  validate_ready(project)
 if a.action=='synthesize':
  if mode=='silent':raise ValueError('Select Azure or Edge audio mode and run configure first')
  cmd=[sys.executable,str(ROOT/'scripts/azure_tts.py'),str(project)]
 elif a.action=='timeline':cmd=[sys.executable,str(ROOT/('scripts/audio_timeline.py' if mode!='silent' else 'scripts/silent_timeline.py')),str(project)]
 elif a.action=='preview':
  cmd=['node',str(VENDOR/'scripts/peek_frame.mjs'),str(project)]
  cmd+=([a.scene] if a.scene else ['--all'])+['--at',a.at]
 elif a.action=='layout':cmd=['node',str(VENDOR/'scripts/check_layout.mjs'),str(project)]
 else:
  cmd=['node',str(VENDOR/'scripts/render_video.mjs'),str(project),'--jpeg','--jpeg-quality','95','--crf','18','--preset','medium','--concurrency',str(max(1,a.concurrency))]
 return subprocess.run(cmd,env=env).returncode
if __name__=='__main__':raise SystemExit(main())
