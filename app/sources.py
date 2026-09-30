"""Validate evidence-ledger shape, not the truth of its claims or remote reachability."""
import json,sys
from urllib.parse import urlparse
from pathlib import Path

def validate(data):
 errors=[]
 if not isinstance(data,list) or not data:return ['来源清单应为非空数组']
 seen=set()
 for i,item in enumerate(data):
  prefix=f'来源 {i+1}'
  if not isinstance(item,dict):errors.append(prefix+' 应为对象');continue
  for field in ('id','title','url','accessed','claims','limitations'):
   if field not in item:errors.append(prefix+' 缺少 '+field)
  uid=str(item.get('id',''))
  if uid in seen:errors.append(prefix+' ID 重复')
  seen.add(uid)
  url=urlparse(str(item.get('url','')))
  if url.scheme not in ('https','http') or not url.netloc:errors.append(prefix+' URL 无效')
  if not isinstance(item.get('claims'),list) or not item.get('claims'):errors.append(prefix+' 应列出其支持的具体说法')
 return errors
if __name__=='__main__':
 try:
  errors=validate(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
  if errors:print('\n'.join(errors));sys.exit(1)
  print('来源结构检查通过。尚需实际阅读、核对说法与证据边界；本命令不验证网页可访问性或事实真伪。')
 except (OSError,ValueError,IndexError) as e:print(str(e),file=sys.stderr);sys.exit(1)
