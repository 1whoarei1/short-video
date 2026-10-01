#!/usr/bin/env python3
"""Build the checked-in theme catalog and its self-contained concept HTML.

The picker uses already-rendered WebP files; this script is a maintainer tool,
never an application startup dependency. Render with --render (Node, the pinned
Playwright runtime, Chromium and Pillow are needed only for regeneration).
"""
from __future__ import annotations
import argparse, hashlib, html, json, math, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/presets/themes'
CATALOG = ROOT / 'vendor/html-explainer/references/style-catalog.json'
EVIDENCE = OUT / 'source-evidence.json'

def el(text, x, y, size=24, extra='', tag='div'):
    style = html.escape(f"left:{x}px;top:{y}px;font-size:{size}px;{extra}", quote=True)
    return f'<{tag} class="copy" style="{style}">{text}</{tag}>'

def box(x,y,w,h,color,extra=''):
    return f'<div aria-hidden="true" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{color};{extra}"></div>'

def svg(content,extra=''):
    return f'<svg aria-hidden="true" class="art" viewBox="0 0 1280 720" style="{extra}">{content}</svg>'

def header(left,right,color='currentColor'):
    return el(left,60,42,14,f'font-family:"Space Mono";letter-spacing:1.5px;color:{color}')+el(right,930,42,14,f'font-family:"Space Mono";letter-spacing:1px;color:{color}')

def footer(left='把想法，讲清楚。', right='STUDIO / 01',color='currentColor'):
    return el(left,60,655,15,f'color:{color}')+el(right,1000,655,13,f'font-family:"Space Mono";color:{color}')

# Every layout below is a content-bearing HTML/CSS/SVG concept, not a swatch.
# Exact palette and motif provenance is in source-evidence.json.
def scene(id,counts):
    css=''; body=''; bg='#fff'; color='#161616'; font='Inter'
    if id=='frame-bold-poster':
        bg='#F5F2EF';color='#1C1410';font='Shrikhand'
        body=header('STUDIO / MANIFESTO','VOL. 01 — 2026')+box(60,82,1150,3,'#D8000F')
        body+=el('01',990,106,182,'color:#D8000F;transform:rotate(-6deg);line-height:1')
        body+=el('MAKE',80,108,138,'transform:rotate(-2deg);line-height:1')+el('IT MOVE.',75,243,138,'color:#D8000F;transform:rotate(-4deg);line-height:1')+el('MATTER.',88,386,138,'transform:rotate(2deg);line-height:1')
        body+=el('让想法被看见，让表达有分量。',88,554,25,'font-family:"Noto Preview Serif";font-style:italic')+box(60,630,1150,2,color)+footer('IDEAS WORTH SEEING','BOLD / 01','#1C1410')
    elif id=='frame-bold-signal':
        bg='linear-gradient(135deg,#1a1a1a,#2d2d2d,#1a1a1a)';color='#fff';font='Archivo Black'
        body=el('01<span style="opacity:.25">/03</span>',58,58,62)+el('IDEA   <span style="color:#FF5722">/   STORY</span>   /   MOTION',650,72,15,'font-family:"Space Grotesk";letter-spacing:3px')
        body+=box(405,166,875,425,'#FF5722','border-radius:28px 0 0 28px;box-shadow:0 15px 90px #ff572220')
        body+=el('CHAPTER 01 — THE START',459,216,16,'color:#1a1a1a;letter-spacing:3px;font-family:"Space Grotesk"')+el('MAKE<br>IT MOVE.',453,278,111,'color:#1a1a1a;line-height:1.03;letter-spacing:-4px')
        body+=box(60,649,32,5,'#FF5722')+el('从一个好想法开始',109,635,20,'font-family:"Noto Preview"')
    elif id=='frame-build-minimal':
        bg='radial-gradient(ellipse at 15% 10%,#d4a57413,transparent 52%),#FAFAF8';color='#1A1A18'
        body=el('S T U D I O   /   0 1',0,160,13,'width:1280px;text-align:center;color:#B0ACA4')+el('Clarity',0,241,124,'width:1280px;text-align:center;font-weight:200;letter-spacing:-6px')+box(608,414,64,1,'#D4A574')
        body+=el('让表达回归本质',0,450,20,'width:1280px;text-align:center;color:#8d8981;font-weight:300')+el('给好想法，更多呼吸的空间',0,492,16,'width:1280px;text-align:center;color:#9d988f;font-weight:300')
        body+=svg(''.join(f'<path d="{p}" fill="none" stroke="#D4A574" stroke-width="1"/>' for p in ['M40 75V40H75','M1205 40H1240V75','M40 645V680H75','M1205 680H1240V645']))
        body+=''.join(box(603+i*12,610-(i%3)*10,1,25+(i%3)*10,'#D4A574' if i%2 else '#CBC7C0') for i in range(7))
    elif id=='frame-creative-voltage':
        bg='#0d0d14';color='#fff';font='Syne'
        body=box(0,0,602,720,'#2f4bff')+header('// CREATIVE_MODE · ON','STUDIO / 01','#fff')
        body+=el('What if?',57,268,101,'font-family:Caveat;transform:rotate(-7deg)')+el('让灵感接通电源',80,430,22,'font-family:"Noto Preview"')
        body+=svg('<path d="M74 414 Q290 383 520 416" fill="none" stroke="white" stroke-width="5" stroke-linecap="round"/>')
        body+=el('MAKE',648,181,106,'font-weight:800;line-height:1;letter-spacing:-5px')+el('IT',895,300,106,'font-weight:800;color:#2f4bff;-webkit-text-stroke:2px #6f86ff;line-height:1')+el('MOVE.',667,421,106,'font-weight:800;line-height:1;letter-spacing:-5px')+el('IDEAS NEED ENERGY.',775,639,17,'font-family:"Space Mono";color:#6f86ff')
    elif id=='frame-data-chart-nyt':
        bg='#f7f5ee';color='#1a1a1a';font='IBM Plex Sans'
        body=header('DESIGN / CATALOG DATA','23 THEMES','#a91d1d')+el('23 个方向，不止一种表达',60,93,54,'font-family:"Noto Preview Serif";font-weight:700')+el('按原始目录分类 · 主题数量',62,172,18,'color:#666')
        body+=svg(''.join(f'<line x1="220" x2="1140" y1="{y}" y2="{y}" stroke="#1a1a1a" opacity=".13"/>' for y in [243,309,375,441,507,573]))
        for i,(k,label,v) in enumerate(counts):
            y=219+i*66
            body+=el(label,64,y+9,18)+box(225,y+3,v/max(c[2] for c in counts)*800,42,'#a91d1d' if i==0 else '#242424')+el(str(v),250+v/max(c[2] for c in counts)*800,y+6,27,'font-family:"Source Serif 4"')
        body+=footer('来源：随仓库发布的 style-catalog.json','COUNT / 23','#666')
    elif id=='frame-data-rollup':
        bg='#0E0E10';color='#F5F5F2';font='Inter'
        body=header('LIVE NUMBERS / CATALOG','DATA ROLLUP','#94a3b8')+el('看见数字的力量',62,103,53,'font-weight:700')+el('23 个主题 · 按分类计数',65,184,20,'color:#94a3b8')
        for i,(k,label,v) in enumerate(counts):
            h=240*v/max(c[2] for c in counts);x=97+i*182
            body+=box(x,556-h,120,h,'#FF5A2C','border-radius:12px 12px 0 0')+el(str(v),x,502-h,38,'width:120px;text-align:center;font-weight:700')+el(label,x-20,582,16,'width:160px;text-align:center;color:#cbd5e1')
        body+=footer('静态终态示意 · 原生方案为滚动计数与弹性柱形','COUNT / 23','#94a3b8')
    elif id=='frame-decision-tree':
        bg='radial-gradient(#e5e5e5 1px,transparent 1px) 0 0/16px 16px,#fff';font='Inter'
        body=header('IDEA / DECISION MAP','START HERE','#555')+el('一个想法，怎样成为作品？',60,100,40,'font-weight:600')
        body+=svg('<g fill="none" stroke="#333" stroke-width="3"><path d="M640 275V330H350V385"/><path d="M640 275V330H930V385"/><path d="M350 445V490H210V535"/><path d="M350 445V490H485V535"/><path d="M930 445V490H790V535"/><path d="M930 445V490H1065V535"/></g>')
        def node(text,x,y,w,c):return box(x,y,w,70,c,'border-radius:10px;box-shadow:0 7px 18px #00000010')+el(text,x,y+23,19,f'width:{w}px;text-align:center;font-weight:600')
        body+=node('有清楚的表达目标吗？',477,205,326,'#e8d44d')+node('有，组织成故事',225,375,250,'#c2e8a0')+node('还没有，先探索',805,375,250,'#f5c5a3')
        for txt,x,c in [('梳理信息',107,'#d4c5f9'),('选择视觉',382,'#a8d8f0'),('收集参考',687,'#f8b4c8'),('提出问题',962,'#e8d44d')]:body+=node(txt,x,530,206,c)
        body+=el('是',388,314,16,'background:#fff;padding:5px')+el('不确定',844,314,16,'background:#fff;padding:5px')+footer('从选择到行动，逐步展开','FLOW / 01','#666')
    elif id=='frame-electric-studio':
        bg='linear-gradient(#fff 0 50%,#4361ee 50% 100%)';font='Manrope'
        body=el('STUDIO',1040,46,18,'font-weight:800')+el('好的表达，',80,192,88,'font-weight:800;line-height:1.1')+el('让想法',80,260,88,'font-weight:800;line-height:1.1')+box(80,353,266,7,'#0a0a0a')+el('被看见。',80,389,88,'font-weight:800;line-height:1.1;color:#fff')
        body+=el('MAKE AN IDEA VISIBLE',86,590,20,'color:#fff;font-weight:700')+el('A STATEMENT IN TWO PARTS',86,633,13,'color:#fff;letter-spacing:3px')+el('“',1060,409,174,'color:#fff;line-height:1')
    elif id=='frame-glitch-title':
        bg='linear-gradient(#00f0ff08 1px,transparent 1px),linear-gradient(90deg,#00f0ff08 1px,transparent 1px),#0d0e10';color='#f5f5f7';font='Space Grotesk';css='main{background-size:56px 56px!important}.scan{background:repeating-linear-gradient(0deg,#0004 0 1px,transparent 1px 3px)}'
        body=header('>> SIGNAL_FOUND / CH-01','REC ●','#a3a3a3')+el('IDEA',104,187,156,'font-weight:700;text-shadow:-5px 2px #00f0ff,5px -2px #ff2bd6;letter-spacing:-8px;line-height:1')+el('ONLINE_',99,348,137,'font-weight:700;text-shadow:-5px 1px #00f0ff,4px -1px #ff2bd6;letter-spacing:-7px;line-height:1')
        body+=box(77,340,580,6,'#00f0ff')+box(850,237,300,6,'#ff2bd6')+el('打破常规，重新接通信号',108,541,23,'font-family:"Noto Preview";color:#b8bac2')+footer('SYSTEM READY / NOISE → SIGNAL','01001001','#00f0ff')+'<div class="art scan"></div>'
    elif id=='frame-kinetic-type':
        bg='#0a0a0f';color='#fff';font='Inter'
        body=header('WORDS / IN MOTION','STUDIO / 01','#8e8e96')+el('What if',80,152,62,'font-weight:300;color:#bbb')+el('IDEAS',64,227,165,'font-weight:800;letter-spacing:-9px;line-height:1')+el('MOVED?',245,397,143,'font-weight:800;letter-spacing:-8px;line-height:1')+box(81,415,100,10,'#fff')+footer('用文字本身，制造节奏','TYPE / 01','#aaa')
    elif id=='frame-light-leak-cinema':
        bg='#000';color='#f5e9d6';font='EB Garamond'
        body=box(0,92,1280,536,'radial-gradient(ellipse at 78% 18%,#ffb547 0,transparent 38%),radial-gradient(ellipse at 90% 30%,#ff7e3f 0,transparent 30%),linear-gradient(180deg,transparent 60%,#d97757 110%),radial-gradient(ellipse at 30% 60%,#2a1410 0,transparent 60%),linear-gradient(135deg,#1a0d08,#28140c 50%,#0a0502)')
        body+=el('REEL 01  ·  CHAPTER I',65,124,14,'font-family:"IBM Plex Mono";letter-spacing:3px')+el('A quiet idea.',85,309,87,'font-weight:400')+el('在光影之间，故事开始。',90,425,25,'font-family:"Noto Preview Serif"')+el('AN EXPLORATION IN MOTION',90,561,12,'font-family:"IBM Plex Mono";letter-spacing:4px')
        body+=svg('<g stroke="#f5e9d6" opacity=".18"><path d="M168 92V240M542 260V560M937 150V305"/></g>')+'<div class="art grain"></div>'
    elif id=='frame-liquid-bg-hero':
        bg='#1e1b4b';color='#fafaf8';font='Inter Tight'
        for x,y,w,h,c in [(-40,-150,620,610,'#a78bfa'),(890,164,500,500,'#7c5cff'),(347,440,490,420,'#ec4899'),(40,450,300,340,'#06b6d4')]:body+=box(x,y,w,h,c,'border-radius:50%;filter:blur(75px);opacity:.75;mix-blend-mode:screen')
        body+=header('STUDIO / AURORA','LIQUID HERO')+el('让好想法',0,216,98,'width:1280px;text-align:center;font-weight:800;letter-spacing:-4px')+el('自由流动。',0,342,98,'width:1280px;text-align:center;font-weight:800;letter-spacing:-4px')+el('Ideas without edges.',0,503,29,'width:1280px;text-align:center;font-family:"Source Serif 4";font-style:italic')+footer('FLOW / FORM / FEELING','STUDIO / 01')
    elif id=='frame-logo-outro':
        bg='radial-gradient(circle at 50% 44%,#1a1535,#08090c 70%)';color='#f5f5f7';font='Inter Tight'
        body=box(0,0,1280,4,'#7c5cff')+svg('<g transform="translate(568 189)" style="filter:drop-shadow(0 0 18px #7c5cff88)"><rect x="0" y="0" width="30" height="134" fill="#7c5cff"/><rect x="114" y="0" width="30" height="134" fill="#7c5cff"/><rect x="30" y="52" width="84" height="30" fill="#f5f5f7"/><circle cx="15" cy="0" r="15" fill="#7c5cff"/><circle cx="129" cy="134" r="15" fill="#f5f5f7"/></g>')
        body+=el('IDEA STUDIO',0,389,65,'width:1280px;text-align:center;font-weight:800;letter-spacing:-3px')+el('每一个好想法，都值得被看见。',0,493,22,'width:1280px;text-align:center;color:#aaa5bc')+el('CREATE  /  EXPLAIN  /  INSPIRE',0,633,12,'width:1280px;text-align:center;letter-spacing:4px;color:#7c5cff')
    elif id=='frame-nyt-graph':
        bg='#faf9f6';color='#333';font='Libre Franklin'
        body=el('A catalog, in perspective',64,57,43,'font-family:"Libre Baskerville";font-weight:700')+el('主题分类数量与累计占比 · 按目录顺序汇总',65,122,19,'color:#777')+el('■ 主题数量',67,171,15,'color:#5c5c5c')+el('━ 累计占比',232,171,15,'color:#326FA8')
        vals=[x[2] for x in counts];total=sum(vals);cumulative=0;pts=[]
        body+=svg(''.join(f'<line x1="90" x2="1172" y1="{y}" y2="{y}" stroke="#ddd"/>' for y in [250,350,450,550]))
        for i,(_,label,v) in enumerate(counts):
            x=133+i*178;h=v/max(vals)*244;cumulative+=v;pts.append((x+43,550-270*cumulative/total))
            body+=box(x,550-h,86,h,'#5c5c5c')+el(str(v),x,512-h,24,'width:86px;text-align:center')+el(label,x-35,574,15,'width:160px;text-align:center')
        body+=svg('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+'" fill="none" stroke="#326FA8" stroke-width="3"/>'+''.join(f'<circle cx="{x}" cy="{y}" r="5" fill="#326FA8"/>' for x,y in pts))+footer('来源：随仓库发布的 style-catalog.json','TOTAL / 23','#666')
    elif id=='frame-pentagram-stat':
        bg='linear-gradient(#0000000b 1px,transparent 1px),linear-gradient(90deg,#0000000b 1px,transparent 1px),#fff';font='Archivo';css='main{background-size:128px 120px!important}'
        body=el('23',690,47,463,'font-weight:900;letter-spacing:-42px;line-height:1;color:#00000010',tag='span')+el('DESIGN DIRECTIONS',60,83,17,'letter-spacing:5px;color:#E63946;font-weight:700')+el('23<span style="color:#E63946">.</span>',51,177,191,'font-weight:900;letter-spacing:-13px;line-height:1')+el('一个目录，二十三种视觉语言',63,391,23,'color:#999')+box(64,452,358,4,'#E63946')
        body+=''.join(box(70+i*78,597-h,54,h,'#E63946' if i==2 else '#00000020') for i,h in enumerate([47,72,122,89,143]))+box(0,624,1280,96,'#111')+el('23',63,643,34,'color:#E63946;font-weight:700')+el('方向',136,659,16,'color:#aaa')+el('5',372,643,34,'color:#E63946;font-weight:700')+el('创作阶段',424,659,16,'color:#aaa')+el('∞',740,643,34,'color:#E63946;font-weight:700')+el('原创可能',804,659,16,'color:#aaa')
    elif id=='frame-play-mode':
        bg='#0057FF';color='#fff';font='Nunito'
        body=svg('<circle cx="1102" cy="150" r="82" fill="#ffe500"/><path d="M95 511l51 33 51-33-16 58 43 40-60-1-18 58-19-58-60 1 43-40z" fill="#7fff00"/>')
        body+=el('PLAY',119,119,140,'font-weight:900;transform:rotate(-6deg);line-height:1;color:#ff2d8a;filter:drop-shadow(7px 7px 0 white) drop-shadow(13px 13px 0 #0002)')+el('WITH',379,283,127,'font-weight:900;transform:rotate(3deg);line-height:1')+el('IDEAS!',504,417,127,'font-weight:900;transform:rotate(-4deg);line-height:1;color:#ffe500;filter:drop-shadow(5px 5px 0 #0002)')
        body+=el('让创意，好玩起来',262,575,24,'font-family:"Noto Preview";font-weight:700;background:#ff2d8a;padding:16px 24px;border-radius:12px;transform:rotate(-4deg)')
    elif id=='frame-product-promo':
        bg='#0a0a0f';color='#fff';font='Inter'
        body=header('STUDIO / PRODUCT STORY','DESIGN → MOTION','#a5a5af')+el('From idea<br>to impact.',65,175,79,'font-weight:700;letter-spacing:-4px;line-height:1.06')+el('将灵感，变成看得见的作品',69,397,22,'color:#a5a5af')
        body+=box(644,141,570,447,'#171720','border:1px solid #34343e;border-radius:20px;box-shadow:0 25px 80px #0006')+box(665,166,528,36,'#24242f','border-radius:8px')+el('IDEA / CANVAS',689,175,12,'letter-spacing:2px;color:#a5a5af')
        body+=svg('<g transform="translate(730 260)"><rect width="150" height="150" rx="22" fill="#A259FF"/><circle cx="248" cy="75" r="75" fill="#1ABCFE"/><path d="M60 185h300v76H60z" fill="#0ACF83"/><path d="M0 185h75v76H0z" fill="#F24E1E"/></g>')+el('CREATE',738,297,20,'color:white;font-weight:700')+el('CONNECT',930,297,18,'color:#0a0a0f;font-weight:700')+el('MAKE IT REAL',866,467,20,'color:#0a0a0f;font-weight:700')+footer('多彩几何 / 产品界面 / 功能揭示','STUDIO / 01','#96969f')
    elif id=='frame-product-promo-30s':
        bg='radial-gradient(ellipse at 50% 100%,#23243a,transparent 65%),#000';color='#fff';font='Space Grotesk'
        body=header('STUDIO / PRODUCT FILM','30 SECOND STORY','#8b8b94')+el('Less friction.',0,155,79,'width:1280px;text-align:center;font-weight:500;letter-spacing:-4px;color:#aaa')+el('More momentum.',0,253,88,'width:1280px;text-align:center;font-weight:700;letter-spacing:-4px;background:linear-gradient(#fff,#888);background-clip:text;color:transparent')
        body+=svg('<g fill="none" stroke="#ffffff30"><path d="M200 561H1080M215 613H1065M230 665H1050M360 510L295 720M520 510L480 720M760 510L800 720M920 510L985 720"/></g>')
        for i,(a,b) in enumerate([('01','PLAN'),('02','BUILD'),('03','MONITOR')]):
            x=249+i*276;body+=box(x,433,230,118,'linear-gradient(135deg,#272936,#0c0c10)','border:1px solid #555563;border-radius:9px;box-shadow:0 12px 35px #0008')+el(a,x+21,452,12,'color:#a9b0f0')+el(b,x+21,483,23,'font-weight:600;letter-spacing:2px')
        body+=el('把复杂流程，变成清晰进展',0,623,21,'width:1280px;text-align:center;color:#bebec8')
    elif id=='frame-swiss-grid':
        bg='#f2f2f2';color='#0a1e3d';font='Inter'
        body=box(60,70,1158,8,'#0a1e3d')+el('FORM.',60,132,95,'font-weight:800;letter-spacing:-5px')+el('FOLLOWS.',60,233,95,'font-weight:800;letter-spacing:-5px')+el('FUNCTION.',60,334,95,'font-weight:800;letter-spacing:-5px')
        body+=box(842,128,360,434,'#f2f2f2','border-left:9px solid #d4a017;box-shadow:16px 16px 0 #0a1e3d18')+el('23',884,170,139,'font-weight:900;color:#d4a017;letter-spacing:-8px;line-height:1')+el('VISUAL DIRECTIONS',889,329,18,'letter-spacing:2px')+box(890,409,250,21,'#e0e0e0','border:2px solid #0a1e3d')+box(892,411,191,17,'#d4a017')+el('秩序，让信息更清楚',887,470,18)+footer('网格 / 对齐 / 信息层级','SWISS / 01','#0a1e3d')
    elif id=='frame-takram-organic':
        bg='radial-gradient(ellipse at 82% 46%,#7a9e7f22,transparent 54%),#EFEAE0';color='#3A3A34';font='Manrope'
        body=box(62,129,610,478,'#fffdf8aa','border:1px solid #fff9;border-radius:34px;box-shadow:0 20px 50px #5f574913')+el('CONNECTED THINKING',105,180,16,'color:#7A9E7F;letter-spacing:3px')+el('每个想法，<br>都有<span style="color:#C98A5E">连接</span>。',104,261,57,'font-weight:700;line-height:1.4')+el('让知识生长，让关系自然浮现',108,492,21,'color:#8A867C')
        nodes=[(913+175*math.cos(i*math.pi/4),364+175*math.sin(i*math.pi/4)) for i in range(8)]
        body+=svg(''.join(f'<path d="M913 364Q{(913+x)/2+22} {(364+y)/2-28} {x} {y}" fill="none" stroke="#B8C9BA" stroke-width="3"/>' for x,y in nodes)+''.join(f'<circle cx="{x}" cy="{y}" r="17" fill="#7A9E7F"/>' for x,y in nodes)+'<circle cx="913" cy="364" r="36" fill="#C98A5E"/>')+header('STUDIO / LIVING SYSTEMS','ORGANIC / 01','#8A867C')+footer('柔和的结构，自然的秩序','GROW / 01','#8A867C')
    elif id=='frame-vignelli':
        bg='#e8e8e8';color='#fff';font='Inter'
        body=box(438,0,405,720,'#1a1a1a')+box(472,63,337,12,'#cc0000')+el('DESIGN<br>IS A<br>LANGUAGE.',471,133,49,'font-weight:800;line-height:1.1;letter-spacing:-2px;width:340px')+el('23',467,340,172,'font-weight:800;line-height:1;letter-spacing:-10px')+box(472,528,102,8,'#cc0000')+el('用秩序<br>表达力量',472,571,33,'font-weight:700;line-height:1.3')+el('9:16',875,647,17,'font-family:"Space Mono";color:#777')
    elif id=='frame-warm-grain':
        bg='#f5f0e0';color='#3b5e3a';font='Outfit'
        body=header('STUDIO / EVERYDAY IDEAS','WARM GRAIN','#3b5e3a')+box(62,153,691,411,'#3b5e3a','border-radius:26px;box-shadow:0 15px 40px #3b5e3a25')+el('Good ideas.',105,211,79,'font-weight:600;color:#f5f0e0;letter-spacing:-3px')+el('Made human.',107,314,66,'font-weight:400;color:#cc8832;letter-spacing:-2px')+el('让表达，有温度。',109,461,27,'color:#f5f0e0;font-family:"Noto Preview"')
        body+=box(835,169,292,292,'#3b5e3a','border-radius:50%')+el('23',835,226,108,'width:292px;text-align:center;color:#f5f0e0;font-weight:600')+box(813,486,347,110,'#c45d3e','border-radius:36px;transform:rotate(-5deg)')+el('IDEAS GROW HERE',829,523,22,'color:#f5f0e0;transform:rotate(-5deg)')+'<div class="art grain"></div>'+footer('纸感 / 自然色 / 圆润几何','STUDIO / 01','#3b5e3a')
    elif id=='vfx-text-cursor':
        bg='radial-gradient(ellipse at center,#13131e,#06070a 70%)';color='#f5f5f7';font='Inter Tight'
        body=header('> CREATE_STORY()','TEXT + CURSOR','#7b7e89')+box(0,300,555,3,'linear-gradient(90deg,transparent,#ff3b6f,transparent)','transform:rotate(-12deg);filter:blur(6px)')+box(816,456,510,3,'linear-gradient(90deg,transparent,#00d4ff,transparent)','transform:rotate(15deg);filter:blur(5px)')
        body+=el('把想法写下来',110,210,78,'font-weight:800;text-shadow:2px 0 #00d4ff,-2px 0 #ff3b6f')+el('让<span style="color:#ff3b6f">故事</span>发生',110,325,92,'font-weight:800;text-shadow:2px 0 #00d4ff,-2px 0 #ff3b6f')+box(600,349,16,99,'#ff3b6f','box-shadow:0 0 28px #ff3b6f88')+el('YOUR NEXT IDEA STARTS HERE.',115,513,19,'font-family:"JetBrains Mono";color:#777d8d')+footer('INPUT / IDEA → OUTPUT / STORY','READY _','#858997')
    else:raise ValueError(id)
    return bg,color,font,css,body

CATEGORIES={'presentation':'标题与陈述','data-viz':'数据图表','explainer':'图解与流程','ambient':'电影氛围','marketing':'产品营销','intro-outro':'片头片尾','social-shorts':'竖屏短片','product-demo':'产品演示','vfx':'文字特效'}
ZH={'frame-decision-tree':'决策树','frame-kinetic-type':'动态排字','frame-nyt-graph':'新闻数据图','frame-play-mode':'趣味贴纸','frame-product-promo':'产品宣传','frame-product-promo-30s':'30 秒产品宣传','frame-swiss-grid':'瑞士网格','frame-vignelli':'维涅利竖版','frame-warm-grain':'温暖颗粒'}
DESC={
'frame-bold-poster':'暖白纸底、番红强调、倾斜巨字，像一张会动的社论海报',
'frame-bold-signal':'深灰渐变与橙色大卡片，以章节编号和粗体标题制造冲击',
'frame-build-minimal':'超细字体、暖金细线与大量留白，安静而克制',
'frame-creative-voltage':'电光蓝与暗色错位分屏，搭配描边大字和手写线条',
'frame-data-chart-nyt':'暖白新闻纸、编辑式标题与克制的红色重点，适合解释数据',
'frame-data-rollup':'柱形与计数同步增长；这里展示原生数据动画的静态终态',
'frame-decision-tree':'点阵白板、彩色便签与分支连线，让选择过程一目了然',
'frame-electric-studio':'白与电光蓝上下分屏，用跨屏引言形成鲜明对比',
'frame-glitch-title':'暗色网格、RGB 错位、扫描线与信号噪声，呈现数字故障感',
'frame-kinetic-type':'暗底巨型排字，以文字的大小、位置与节奏撑起画面',
'frame-light-leak-cinema':'宽银幕黑边、暖橙漏光、细颗粒和衬线字，营造胶片叙事',
'frame-liquid-bg-hero':'紫与粉色的柔焦流体铺满画面，适合自由感的主视觉',
'frame-logo-outro':'深色晕影、紫色几何标志与简洁品牌文字，用于片尾收束',
'frame-nyt-graph':'新闻式衬线标题、灰柱与蓝线双层图表，强调准确与可读性',
'frame-pentagram-stat':'纯白瑞士网格、巨型指标、单一红色强调与黑色数据底栏',
'frame-play-mode':'亮蓝、热粉与黄色贴纸，倾斜圆润大字带来轻松活力',
'frame-product-promo':'暗色产品舞台、多彩几何与界面卡片，适合功能展示',
'frame-product-promo-30s':'黑色网格、金属感文字与产品流程，面向多场景 30 秒宣传',
'frame-swiss-grid':'海军蓝、赭金和浅灰，严格对齐的字体与统计模块',
'frame-takram-organic':'米色、鼠尾草绿与陶土橙，柔和卡片和自然生长的节点图',
'frame-vignelli':'黑白红的 9:16 竖版，粗体字、网格秩序和红色强调条',
'frame-warm-grain':'奶油纸底、森林绿、赭黄与陶土色，圆润形状和细颗粒',
'vfx-text-cursor':'暗色背景、粉色发光光标与双色色散，像正在写入的故事'
}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--render',action='store_true');ap.add_argument('--browser');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    data=json.loads(CATALOG.read_text());assert len(data)==23 and len({x['id'] for x in data})==23
    counts=[(k,CATEGORIES.get(k,k),sum(x['category']==k for x in data)) for k in dict.fromkeys(x['category'] for x in data)]
    counts.sort(key=lambda x:-x[2])
    counts=counts[:5]+[('other','其他',sum(x[2] for x in counts[5:]))] if len(counts)>6 else counts
    evidence=json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    font_css='\n'.join(p.read_text().replace('url(', 'url(fonts/') for p in sorted((OUT/'fonts').glob('*.css')))
    font_css+='\n@font-face{font-family:"Noto Preview";src:url(fonts/noto-sc-regular.woff2);font-weight:100 500;font-display:block}@font-face{font-family:"Noto Preview";src:url(fonts/noto-sc-bold.woff2);font-weight:600 900;font-display:block}@font-face{font-family:"Noto Preview Serif";src:url(fonts/noto-serif-sc.woff2);font-weight:100 900;font-display:block}'
    base='''*{box-sizing:border-box}html,body{width:1280px;height:720px;margin:0;overflow:hidden}main{position:relative;width:1280px;height:720px;overflow:hidden}h1,h2,p{margin:0}.copy{position:absolute;z-index:2;line-height:1.3;white-space:nowrap}.art{position:absolute;inset:0;width:1280px;height:720px}.grain{opacity:.085;pointer-events:none;mix-blend-mode:multiply;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2' seed='23'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='.6'/%3E%3C/svg%3E")}'''
    themes=[]
    for theme in data:
        id=theme['id'];bg,color,font,css,body=scene(id,counts)
        content='<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1280"><meta name="description" content="HTML-rendered concept preview; original/custom design remains available"><title>'+html.escape(theme['name'])+' — 视觉方向示例</title><style>'+font_css+base+f'main{{background:{bg};color:{color};font-family:"{font}","Noto Preview",sans-serif}}'+css+'</style></head><body><main aria-label="'+html.escape(theme['name'])+' 视觉方向示例">'+body+'</main></body></html>\n'
        (OUT/f'{id}.html').write_text(content)
        palette=theme['colors'].split() or evidence.get(id,{}).get('palette',[])
        if id in evidence:palette=evidence[id].get('palette',palette)
        themes.append({'id':id,'name':theme['name'],'zh_name':theme['zh_name'],'display_name':theme['zh_name'] or ZH.get(id,theme['name']),'description':DESC[id],'category':CATEGORIES.get(theme['category'],theme['category']),'category_id':theme['category'],'subcategory':theme['subcategory'],'palette':palette,'best_for':theme['best_for'],'preview':f'/presets/themes/{id}.webp','preview_html':f'/presets/themes/{id}.html','width':1280,'height':720,'native_aspects':theme['aspects'],'source':'vendor/html-explainer/references/style-catalog.json','preview_note':'HTML 实际渲染的静态概念示例；主题是创作参考，不限制原创布局。'+(' 此方向原生支持 9:16。' if id=='frame-vignelli' else '')})
    registry={'schema_version':1,'preview_kind':'rendered-concept','count':23,'custom_style_allowed':True,'themes':themes}
    (OUT.parent/'themes.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Built 23 theme HTML sources and registry')
    if args.render:
        cmd=['node',str(ROOT/'scripts/render_theme_previews.mjs')]
        if args.browser:cmd+=['--browser',args.browser]
        subprocess.run(cmd,check=True,cwd=ROOT)
        subprocess.run([sys.executable,str(ROOT/'scripts/verify_theme_previews.py'),'--build'],check=True,cwd=ROOT)

if __name__=='__main__':main()
