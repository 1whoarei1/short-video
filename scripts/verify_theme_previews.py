#!/usr/bin/env python3
"""Verify checked-in preview assets, and optionally rebuild their QA contact sheet.
Default verification needs only Python's standard library. --build additionally
uses Pillow to decode images, check pixel diversity and assemble a contact sheet.
"""
from __future__ import annotations
import argparse,hashlib,json,pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'web/presets/themes'

def html_source_hash(path):
    # Git checkouts may translate LF to CRLF. Hash canonical UTF-8 source so
    # verification/build retain the same provenance on Windows and Unix.
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()

def webp_size(data):
    assert data[:4]==b'RIFF' and data[8:12]==b'WEBP','Not a WebP image'
    chunk=data[12:16]
    if chunk==b'VP8 ':
        assert data[23:26]==b'\x9d\x01\x2a';return tuple(x&0x3fff for x in struct.unpack('<HH',data[26:30]))
    if chunk==b'VP8L':
        v=int.from_bytes(data[21:25],'little');return (v&0x3fff)+1,((v>>14)&0x3fff)+1
    if chunk==b'VP8X':return int.from_bytes(data[24:27],'little')+1,int.from_bytes(data[27:30],'little')+1
    raise AssertionError(f'Unsupported WebP chunk {chunk!r}')

def verify(build=False):
    upstream=json.loads((ROOT/'vendor/html-explainer/references/style-catalog.json').read_text(encoding='utf-8'))
    catalog=json.loads((OUT.parent/'themes.json').read_text(encoding='utf-8'));themes=catalog['themes']
    assert len(themes)==len(upstream)==23
    assert [(x['id'],x['name'],x['zh_name']) for x in themes]==[(x['id'],x['name'],x['zh_name']) for x in upstream]
    hashes=set();rows=[]
    if build:
        from PIL import Image,ImageDraw,ImageFont,ImageStat
        sheet=Image.new('RGB',(1600,6*258),'#eef0f3');draw=ImageDraw.Draw(sheet)
        try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
        except OSError:font=ImageFont.load_default()
    for i,t in enumerate(themes):
        p=ROOT/'web'/t['preview'].lstrip('/');data=p.read_bytes();digest=hashlib.sha256(data).hexdigest()
        assert digest not in hashes,f'Duplicate preview {t["id"]}';hashes.add(digest)
        assert webp_size(data)==(1280,720),t['id'];assert len(data)<200_000,t['id']
        h=ROOT/'web'/t['preview_html'].lstrip('/');markup=h.read_text(encoding='utf-8')
        assert 'https://' not in markup and 'http://' not in markup.replace("xmlns='http://www.w3.org/2000/svg'",''),f'External HTML dependency: {t["id"]}'
        item={'id':t['id'],'file':t['preview'],'width':1280,'height':720,'bytes':len(data),'sha256':digest,'html_sha256':html_source_hash(h)}
        if build:
            im=Image.open(p).convert('RGB');im.load();std=max(ImageStat.Stat(im).stddev);assert std>12,f'Flat/blank image {t["id"]}'
            item['max_channel_stddev']=round(std,2)
            x=(i%4)*400;y=(i//4)*258;sheet.paste(im.resize((400,225),Image.Resampling.LANCZOS),(x,y));draw.text((x+9,y+233),f'{i+1:02d}  {t["name"]}',fill='#20252b',font=font)
        rows.append(item)
    if build:
        sheet.save(OUT/'contact-sheet.jpg',quality=65,optimize=True)
        (OUT/'manifest.json').write_text(json.dumps({'schema_version':1,'count':23,'total_image_bytes':sum(x['bytes'] for x in rows),'image_checks':'Decoded RGB; 1280×720; unique SHA-256; max channel standard deviation > 12; each < 200 KB','themes':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'));assert manifest['count']==23
        expected={x['id']:x for x in manifest['themes']}
        for row in rows:
            assert all(expected[row['id']][k]==v for k,v in row.items()),f'Manifest mismatch {row["id"]}'
    print(f'PASS: 23 exact upstream themes, local source + unique 1280×720 WebP, {sum(x["bytes"] for x in rows):,} preview bytes')
    return rows

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--build',action='store_true');a=ap.parse_args();verify(a.build)
