"""Project-local asset planning and actual-image receipts; never calls a model API."""
import argparse
import hashlib
import json
import os
import io
import re
from pathlib import Path
from .workflow import Workflow, process_lock, now

KINDS = ('ai-generated', 'user-supplied', 'code-generated', 'licensed-reference')

def local(root, value):
    rel = Path(value)
    if rel.is_absolute() or not rel.parts or any(p.startswith('.') for p in rel.parts) or '\\' in str(value):
        raise ValueError('素材路径必须是项目内非隐藏相对路径')
    result = (root / rel).resolve()
    if not result.is_relative_to(root):
        raise ValueError('素材路径超出项目')
    return result

def short(value, limit=20000):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('素材说明格式错误或过长')
    return value

def load_ledger(root):
    path=root/'.studio/image-assets.json'
    if path.is_symlink(): raise ValueError('素材索引不能是符号链接')
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schemaVersion':1,'plans':[], 'assets':[]}

def write_ledger(root, data):
    path=root/'.studio/image-assets.json';temp=path.with_suffix('.tmp')
    if temp.is_symlink(): raise ValueError('素材索引临时路径不能是符号链接')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,path)

def decode_image(path):
    try:
        from PIL import Image
    except ImportError:
        raise ValueError('登记图片需要 Pillow 解码器；请安装 python -m pip install Pillow。工作台其他功能可继续使用') from None
    if not path.is_file() or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise ValueError('需要PNG/JPEG/WebP图片')
    with path.open('rb') as source:
        content=source.read(64_000_001)
    if not content or len(content)>64_000_000:raise ValueError('图片大小无效或超过64MB')
    try:
        with Image.open(io.BytesIO(content)) as im:
            if im.format not in ('PNG','JPEG','WEBP') or im.width*im.height>40_000_000 or max(im.size)>16384:raise ValueError('图片尺寸或格式无效')
            im.verify()
        with Image.open(io.BytesIO(content)) as im:im.load()
    except (OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError('图片无法完整解码') from error
    return content

def operate(workspace, command, *, file=None, purpose='', prompt='', source='ai-generated', model='', origin='', task_id=None, revision=None):
    root=Path(workspace).resolve()
    if any((root/rel).is_symlink() for rel in ('.studio', '.studio/image-assets.lock', '.studio/write.lock')): raise ValueError('内部目录不能是符号链接')
    flow=Workflow(root)
    path=local(root,file) if file is not None else None
    content=decode_image(path) if command=='record' else None
    with process_lock(root/'.studio/write.lock'), process_lock(root/'.studio/image-assets.lock'):
        state=flow.read()
        if task_id is not None:
            request=state.get('taskRequest') or {}
            if request.get('id')!=task_id or request.get('status') not in ('claimed','running') or state['revision']!=revision:
                raise ValueError('视频任务已变化、未领取或已取消；请重新读取状态')
        ledger=load_ledger(root)
        if command=='list': return ledger
        if command=='plan':
            path=local(root,file)
            if path.stat().st_size>256000:raise ValueError('素材计划超过256KB')
            data=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data,list) or not 1<=len(data)<=64:raise ValueError('素材计划需为1至64项数组')
            plans=[]
            for item in data:
                if not isinstance(item,dict):raise ValueError('素材计划项格式错误')
                plans.append({key:short(item.get(key,'')) for key in ('id','purpose','prompt','aspect','transparency','consistency','references')})
                if not plans[-1]['id'] or not plans[-1]['purpose']:raise ValueError('每项需提供id和用途')
            if len({x['id'] for x in plans})!=len(plans):raise ValueError('素材计划id重复')
            ledger['plans']=plans;ledger['updated']=now();write_ledger(root,ledger);return ledger
        if command!='record':raise ValueError('不支持的素材操作')
        if source not in KINDS:raise ValueError('素材来源类型错误')
        if source=='ai-generated' and state.get('settings',{}).get('image_mode','auto')=='existing':raise ValueError('用户选择了仅使用现有素材')
        sha=hashlib.sha256(content).hexdigest()
        folder=local(root,'assets/generated');folder.mkdir(parents=True,exist_ok=True)
        target=folder/(sha+path.suffix.lower())
        if target.is_symlink():raise ValueError('素材快照不能是符号链接')
        if not target.exists():
            with target.open('xb') as out:out.write(content)
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=sha:raise ValueError('同名素材快照已损坏')
        record={'id':sha[:20],'path':target.relative_to(root).as_posix(),'sha256':sha,'bytes':len(content),'source':source,'purpose':short(purpose),'prompt':short(prompt),'modelReported':short(model,200),'origin':short(origin,2000),'created':now(),'verification':'image-bytes-validated; provenance is author-declared'}
        previous=next((x for x in ledger['assets'] if x['sha256']==sha),None)
        if previous:return previous
        ledger['assets'].append(record);ledger['updated']=now();write_ledger(root,ledger);return record

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',required=True);parser.add_argument('--task-id');parser.add_argument('--revision',type=int)
    sub=parser.add_subparsers(dest='command',required=True);sub.add_parser('list');p=sub.add_parser('plan');p.add_argument('--file',required=True)
    p=sub.add_parser('record');p.add_argument('--file',required=True);p.add_argument('--purpose',required=True);p.add_argument('--prompt',default='');p.add_argument('--source',choices=KINDS,default='ai-generated');p.add_argument('--model',default='');p.add_argument('--origin',default='')
    args=vars(parser.parse_args())
    try:print(json.dumps(operate(**args),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as error:parser.exit(1,str(error)+'\n')
if __name__=='__main__':main()
