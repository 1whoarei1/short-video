#!/usr/bin/env python3
"""Maintainer utility: subset bundled preview fonts to the checked-in sample text.
Requires fonttools[woff]. Optional --noto-source uses locally installed Noto CJK
TTCs (SIL OFL) to recreate the three CJK subsets. Existing binary subsets are
sufficient for offline preview rendering; this script is never run at startup.
"""
import argparse,pathlib,re
from fontTools.ttLib import TTFont
from fontTools import subset
ROOT=pathlib.Path(__file__).resolve().parents[1];DIR=ROOT/'web/presets/themes/fonts'
ap=argparse.ArgumentParser();ap.add_argument('--noto-source');a=ap.parse_args()
text=''.join(p.read_text() for p in DIR.parent.glob('*.html'))
text=re.sub('<[^>]+>','',text);text+=''.join(chr(x) for x in range(32,127))

def save(font,dest):
    options=subset.Options();options.flavor='woff2';options.name_IDs=['*'];options.name_legacy=True;options.name_languages=['*'];options.recalc_timestamp=False
    sub=subset.Subsetter(options=options);sub.populate(text=text);sub.subset(font)
    # Avoid using Reserved Font Names as modified subsets' primary names.
    for n in font['name'].names:
        if n.nameID in [1,3,4,6,16,17]:
            try:n.string=('Studio Preview '+n.toUnicode()).encode(n.getEncoding())
            except (UnicodeEncodeError,LookupError):pass
    font.flavor='woff2';font.save(dest)

if a.noto_source:
    src=pathlib.Path(a.noto_source)
    for name,path in [('noto-sc-regular.woff2','NotoSansCJK-Regular.ttc'),('noto-sc-bold.woff2','NotoSansCJK-Bold.ttc'),('noto-serif-sc.woff2','NotoSerifCJK-Regular.ttc')]:
        save(TTFont(src/path,fontNumber=2),DIR/name)
for p in DIR.glob('*.woff2'):
    save(TTFont(p),p)
for p in DIR.glob('*.css'):
    s=p.read_text().replace("format('truetype')","format('woff2')").replace('font-display: swap','font-display: block');p.write_text(s)
print('Font subsets:',len(list(DIR.glob('*.woff2'))),'files;',sum(p.stat().st_size for p in DIR.glob('*.woff2')),'bytes')
