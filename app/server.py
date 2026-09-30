import argparse, json, mimetypes, secrets, sys, base64, uuid, webbrowser, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from .workflow import Workflow
BASE=Path(__file__).resolve().parent.parent

def serve(root,port=8765,open_browser=False):
 default_flow=Workflow(root); token=secrets.token_urlsafe(32)
 projects={"default":default_flow}
 sample=BASE/"examples"/"processed-meat"
 if sample.exists() and sample.resolve()!=default_flow.root: projects["sample"]=Workflow(sample)
 class Handler(BaseHTTPRequestHandler):
  def reply(self,code,body,kind='application/json'):
   data=json.dumps(body,ensure_ascii=False).encode() if kind=='application/json' else body
   self.send_response(code); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.send_header('X-Frame-Options','DENY'); self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
  def get_flow(self):
   key=parse_qs(urlparse(self.path).query).get('project',['default'])[0]
   if key not in projects: raise ValueError('未知项目')
   return projects[key]
  def valid_host(self):
   return self.headers.get('Host','').split(':')[0] in ('127.0.0.1','localhost')
  def do_GET(self):
   if not self.valid_host(): return self.reply(403,{'error':'仅允许本机访问'})
   path=unquote(urlparse(self.path).path)
   try:
    flow=self.get_flow()
    if path=='/api/projects': return self.reply(200,{'projects':[{'id':k,'title':('当前项目' if k=='default' else '示例：加工肉与癌症')} for k in projects]})
    if path=='/api/state': return self.reply(200,{'project':flow.read(),'token':token})
    if path=='/api/health': return self.reply(200,{'ok':True,'workspace':str(flow.root),'python':sys.version.split()[0]})
    if path.startswith('/assets/'):
     p=flow.asset(path[8:])
     if any(part.startswith('.') for part in Path(path[8:]).parts): raise ValueError('隐藏的内部文件不可下载')
     kind=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
     if kind in ['text/html','image/svg+xml']: kind='text/plain; charset=utf-8'
     size=p.stat().st_size; start=0; end=size-1; status=200
     requested=self.headers.get('Range')
     if requested:
      import re
      match=re.fullmatch(r'bytes=(\d+)-(\d*)',requested)
      if not match: return self.reply(416,{'error':'无效字节范围'})
      start=int(match.group(1)); end=min(int(match.group(2)) if match.group(2) else end,end);status=206
      if start>end: return self.reply(416,{'error':'范围超出文件'})
     self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1));self.send_header('X-Content-Type-Options','nosniff')
     if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
     self.end_headers()
     with p.open('rb') as file:
      file.seek(start);remaining=end-start+1
      while remaining>0:
       chunk=file.read(min(remaining,65536))
       if not chunk:break
       self.wfile.write(chunk);remaining-=len(chunk)
     return
    p=(BASE/'web'/('index.html' if path=='/' else path.lstrip('/'))).resolve()
    if not p.is_relative_to(BASE/'web') or not p.is_file(): return self.reply(404,{'error':'未找到文件'})
    self.reply(200,p.read_bytes(),mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
   except (ValueError,OSError) as e: self.reply(404,{'error':str(e)})
  def do_POST(self):
   if not self.valid_host(): return self.reply(403,{'error':'仅允许本机访问'})
   if self.headers.get('X-Workspace-Token')!=token: return self.reply(403,{'error':'请刷新本地工作台后重试'})
   origin=self.headers.get('Origin')
   if origin and origin not in [f'http://127.0.0.1:{port}',f'http://localhost:{port}']: return self.reply(403,{'error':'拒绝跨站写入'})
   try:
    flow=self.get_flow()
    length=int(self.headers.get('Content-Length','0'))
    if length>12_000_000: raise ValueError('请求过大')
    data=json.loads(self.rfile.read(length))
    if not isinstance(data,dict):raise ValueError('请求应为 JSON 对象')
    action=urlparse(self.path).path.removeprefix('/api/')
    if action=='upload':
     import re
     filename=Path(str(data.get('name','material.txt'))).name
     extension=Path(filename).suffix.lower()
     if extension not in ('.txt','.md','.pdf','.csv','.json','.png','.jpg','.jpeg','.webp','.mp4','.webm'):raise ValueError('支持文档、图片和视频；不接受可执行文件或 HTML')
     raw=base64.b64decode(data['data'].split(',',1)[-1],validate=True)
     if len(raw)>8_000_000:raise ValueError('单文件不能超过 8 MB；大文件请由 Codex 直接放入项目目录')
     folder=flow.root/'materials';folder.mkdir(exist_ok=True)
     safe=re.sub(r'[^\w.\-]','_',filename)[:120];name=f'materials/{uuid.uuid4().hex[:10]}-{safe}';(flow.root/name).write_bytes(raw)
     project=flow.mutate('artifact',{'stage':data.get('stage','research'),'path':name,'label':filename,'role':'用户参考素材','revision':data.get('revision')})
     return self.reply(200,{'project':project,'path':name})
    if action=='capture':
     raw=base64.b64decode(data['data'].split(',',1)[-1],validate=True)
     if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('需要 PNG 截图')
     folder=flow.root/'annotations'; folder.mkdir(exist_ok=True); name=f'annotations/{uuid.uuid4().hex}.png'; (flow.root/name).write_bytes(raw)
     return self.reply(200,{'path':name})
    self.reply(200,{'project':flow.mutate(action,data)})
   except (ValueError,KeyError,TypeError,OSError) as e: self.reply(400,{'error':str(e)})
 print(f'视频工作台: http://127.0.0.1:{port}\n项目目录: {default_flow.root}',flush=True)
 if open_browser: threading.Timer(.5,lambda:webbrowser.open(f'http://127.0.0.1:{port}')).start()
 ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--workspace',default=str(BASE/'workspace')); p.add_argument('--port',type=int,default=8765); p.add_argument('--open',action='store_true'); a=p.parse_args(); serve(a.workspace,a.port,a.open)
