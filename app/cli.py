"""Codex uses this CLI, not hidden HTTP generation or model API calls."""
import argparse,json,sys
from pathlib import Path
from .workflow import Workflow, STAGES
p=argparse.ArgumentParser(description='视频工作台项目操作'); p.add_argument('--workspace',default='workspace')
sub=p.add_subparsers(dest='command',required=True)
sub.add_parser('status')
s=sub.add_parser('save'); s.add_argument('--stage',choices=STAGES,required=True); s.add_argument('--file',required=True); s.add_argument('--settings',help='Optional JSON brief configuration file')
s=sub.add_parser('artifact'); s.add_argument('--stage',choices=STAGES,required=True); s.add_argument('--path',required=True); s.add_argument('--label',default=''); s.add_argument('--role',default='')
for cmd in ['submit','approve','revise']:
 s=sub.add_parser(cmd); s.add_argument('--stage',choices=STAGES,required=True)
 if cmd=='approve': s.add_argument('--by',choices=['agent','human'],default='agent'); s.add_argument('--note',default='')
s=sub.add_parser('mode'); s.add_argument('--self-review',choices=['on','off'],required=True)
sub.add_parser('undo')
s=sub.add_parser('resolve');s.add_argument('--id',required=True);s.add_argument('--resolved',choices=['yes','no'],default='yes')
a=p.parse_args(); flow=Workflow(a.workspace)
try:
 if a.command=='status': result=flow.read()
 else:
  data=vars(a).copy()
  if a.command=='save':
   data['text']=Path(a.file).read_text(encoding='utf-8')
   if a.settings:data['settings']=json.loads(Path(a.settings).read_text(encoding='utf-8'))
   else:data.pop('settings',None)
  if a.command=='resolve':data['resolved']=a.resolved=='yes'
  if a.command=='mode': data['selfReview']=a.self_review=='on'
  result=flow.mutate(a.command,data)
 print(json.dumps(result,ensure_ascii=False,indent=2))
except (ValueError,OSError) as e: print(str(e),file=sys.stderr); sys.exit(1)
