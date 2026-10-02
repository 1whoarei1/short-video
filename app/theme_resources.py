"""Small offline discovery/copy tools for optional HTML theme resources."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from .workflow import Workflow, process_lock
ROOT=Path(__file__).resolve().parents[1]
PACKS=ROOT/'theme-packs'
EXTENSIONS={'.html','.css','.js','.svg','.png','.webp','.jpg','.jpeg','.json','.md','.txt','.woff','.woff2','.glb','.gltf'}

def safe_path(base, relative):
    rel=Path(relative)
    if rel.is_absolute() or not rel.parts or any(x.startswith('.') for x in rel.parts) or '\\' in str(relative):raise ValueError('需要非隐藏的相对路径')
    current=base
    for part in rel.parts:
        current=current/part
        if current.is_symlink():raise ValueError('资源路径不能包含符号链接')
    target=current.resolve()
    if not target.is_relative_to(base.resolve()):raise ValueError('资源路径超出范围')
    return target

def catalog():
    result=json.loads((PACKS/'catalog.json').read_text(encoding='utf-8'))
    if not isinstance(result.get('packs'),list):raise ValueError('主题目录格式错误')
    return result['packs']

def select(identifier):
    identifier=identifier.removeprefix('pack-')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',identifier):raise ValueError('主题ID格式错误')
    entry=next((p for p in catalog() if p['id']==identifier),None)
    if entry is None:raise ValueError('未找到主题包')
    manifest_path=safe_path(ROOT,entry['manifest'])
    if not manifest_path.is_relative_to(PACKS):raise ValueError('主题索引路径错误')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('id')!=identifier:raise ValueError('主题索引与清单ID不匹配')
    return manifest

def discover(query=''):
    words=[x.casefold() for x in query.split() if x]
    matches=[]
    for entry in catalog():
        hay=' '.join(str(entry.get(k,'')) for k in ('id','name','displayName','description','tags','compatibleThemeIds')).casefold()
        score=sum(word in hay for word in words)
        if words and not score:continue
        matches.append({**entry,'matchedTerms':[w for w in words if w in hay],'score':score})
    return sorted(matches,key=lambda x:-x['score'])

def copy_pack(identifier, workspace, destination='assets/theme-resources', task_id=None, revision=None):
    manifest=select(identifier);identifier=manifest['id'];root=Path(workspace).resolve()
    for rel in ('.studio','.studio/write.lock','.studio/theme-resources.lock'):
        if (root/rel).is_symlink():raise ValueError('内部目录不能是符号链接')
    flow=Workflow(root);dest=safe_path(root,destination)
    files=[];seen=set();total=0
    def include(relative):
        nonlocal total
        if relative in seen:return
        source=safe_path(ROOT,relative)
        if not source.is_relative_to(PACKS) or not source.is_file():raise ValueError('资源必须来自内置主题目录')
        if source.suffix.lower() not in EXTENSIONS and source.name!='LICENSE':raise ValueError('不支持的资源类型：'+source.name)
        remaining=64_000_000-total
        with source.open('rb') as handle:data=handle.read(remaining+1)
        if len(data)>remaining or len(files)>=4096:raise ValueError('资源包超过本地复制限额')
        files.append((relative,data));seen.add(relative);total+=len(data)
    for folder in (PACKS/identifier,PACKS/'shared'):
        for item in sorted(folder.rglob('*')):
            if item.is_symlink():raise ValueError('资源包中含符号链接')
            if item.is_file():include(item.relative_to(ROOT).as_posix())
    # Cross-pack material references retain their original relative locations.
    for asset in manifest.get('assets',[]):include(asset['path'])
    for dependency in manifest.get('dependencies',{}).get('shared',[]):include(dependency)
    include('theme-packs/LICENSE')
    record={'schemaVersion':1,'pack':identifier,'version':manifest['version'],'source':'bundled-theme-resource-pack','files':[{ 'path':rel,'sha256':hashlib.sha256(data).hexdigest()} for rel,data in files]}
    with process_lock(root/'.studio/write.lock'),process_lock(root/'.studio/theme-resources.lock'):
        state=flow.read()
        if task_id is not None:
            request=state.get('taskRequest') or {}
            if request.get('id')!=task_id or request.get('status')!='running' or state['revision']!=revision:raise ValueError('任务已变化或已取消，请重新读取状态')
        # Preflight the entire set before creating anything. Never replace user edits.
        safe_path(root,destination)
        plans=[]
        for rel,data in files:
            target=safe_path(root,str(Path(destination)/rel))
            if target.exists() and (not target.is_file() or target.read_bytes()!=data):raise ValueError('已有文件含修改，未覆盖：'+str(target.relative_to(root)))
            plans.append((target,data))
        receipt=safe_path(root,str(Path(destination)/('resource-kit-'+identifier+'.json')))
        serialized=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
        if receipt.exists():
            if not receipt.is_file():raise ValueError('已有资源清单不同，选择新的目标目录')
            previous=receipt.read_bytes()
            if previous!=serialized:
                # Preserve an unchanged legacy receipt; its source label was not
                # a statement that every included image was hand-authored.
                try: legacy=json.loads(previous)
                except (ValueError,UnicodeDecodeError):legacy=None
                if legacy!={**record,'source':'bundled-original-resource-pack'}:raise ValueError('已有资源清单不同，选择新的目标目录')
                serialized=previous
        for target,data in plans+[(receipt,serialized)]:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():
                with target.open('xb') as out:out.write(data)
        return {'pack':identifier,'destination':str(dest),'preview':str(dest/manifest['entrypoints']['preview']),'manifest':str(dest/'theme-packs'/identifier/'manifest.json'),'receipt':str(receipt),'copiedFiles':len(files),'note':'按内容自由改写副本；复制不会改变当前视频主题、人物、音色或语速'}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('list');s.add_argument('--query',default='')
    s=sub.add_parser('show');s.add_argument('id')
    s=sub.add_parser('copy');s.add_argument('id');s.add_argument('--workspace',required=True);s.add_argument('--destination',default='assets/theme-resources');s.add_argument('--task-id');s.add_argument('--revision',type=int)
    a=p.parse_args()
    try:
        if a.command=='list':result=discover(a.query)
        elif a.command=='show':result=select(a.id)
        else:result=copy_pack(a.id,a.workspace,a.destination,a.task_id,a.revision)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error:p.exit(1,str(error)+'\n')
if __name__=='__main__':main()
