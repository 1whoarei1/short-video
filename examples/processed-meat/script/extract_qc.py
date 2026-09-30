from pathlib import Path
from PIL import Image,ImageDraw
import json, subprocess
p=Path(__file__).resolve().parents[1];order=json.loads((p/'project.json').read_text())['order'];l=json.loads((p/'layout.json').read_text());out=Image.new('RGB',(1980,1600),'#deded8')
for i,s in enumerate(order):
 t=l[s]['start_sec']+l[s]['duration_sec']*.92;f=p/'out/qc'/f'{i+1:02}_{s}.png'
 subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(p/'out/processed-meat.mp4'),'-frames:v','1',str(f)],check=True)
 im=Image.open(f).convert('RGB')
 if i+1 in [1,9,10]:im.save(p/'out'/f'preview-{i+1:02}.png')
 im.thumbnail((640,360));c=Image.new('RGB',(660,400),'white');c.paste(im,(10,0));ImageDraw.Draw(c).text((15,370),f'{i+1:02} {s}',fill='black');out.paste(c,((i%3)*660,(i//3)*400))
out.save(p/'out/contact-sheet.png')
mo=Image.new('RGB',(1920,1160),'#deded8')
for i,s in enumerate(['01_hook','02a_meaning','04_definition']):
 for j,t in enumerate([.3,.7,1.3,2.2]):
  f=p/'out/qc'/f'motion-{s}-{j}.png';subprocess.run(['ffmpeg','-v','error','-y','-ss',str(l[s]['start_sec']+t),'-i',str(p/'out/processed-meat.mp4'),'-frames:v','1',str(f)],check=True)
  im=Image.open(f).convert('RGB');im.thumbnail((480,270));mo.paste(im,(j*480,i*385));ImageDraw.Draw(mo).text((j*480+10,i*385+279),f'{s} at +{t}s',fill='black')
mo.save(p/'out/qc/motion-contact-sheet.png')
