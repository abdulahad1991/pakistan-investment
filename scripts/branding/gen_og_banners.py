#!/usr/bin/env python3
"""Regenerate OG share banners in the new brand (lime accent + pakInvestlysis wordmark)."""
import os, re, glob, html
from PIL import Image, ImageDraw, ImageFont

ROOT = "/Users/abdulahad/Desktop/Projects/Innovations/pakistan-investment"
OG   = os.path.join(ROOT, "assets/og")
FDIR = "/Users/abdulahad/Desktop/Projects/UPI/backoffice-portal/frontend/src/assets/fonts"
BOLD = os.path.join(FDIR, "Poppins-Bold.ttf")
SEMI = os.path.join(FDIR, "Poppins-SemiBold.ttf")
REG  = os.path.join(FDIR, "Poppins-Regular.ttf")

GREEN_D=(5,60,48); ACID=(237,248,4); WHITE=(255,255,255); SAGE=(204,223,211)
W,H=1200,630

def page_for(name):
    if name=="home": return "index.html"
    if name=="guides-index": return "guides/index.html"
    if name=="blog-index": return "blog/index.html"
    if name.startswith("guides-"): return "guides/%s.html"%name[len("guides-"):]
    if name.startswith("blog-"): return "blog/%s.html"%name[len("blog-"):]
    return "%s.html"%name

def og_title(path):
    try: t=open(os.path.join(ROOT,path),encoding="utf-8").read()
    except FileNotFoundError: return None
    m=re.search(r'<meta property="og:title" content="([^"]*)"',t)
    if not m: m=re.search(r'<title>([^<]*)</title>',t)
    return html.unescape(m.group(1)).strip() if m else None

def kicker_for(name):
    if "calculator" in name: return "FREE CALCULATOR"
    if name=="home": return "INVESTING TOOLKIT"
    if name.startswith("guides"): return "GUIDE"
    if name.startswith("blog"): return "ANALYSIS"
    return "PAKINVESTLYSIS"

def draw_tracked(d,xy,text,font,fill,track):
    x,y=xy
    for ch in text:
        d.text((x,y),ch,font=font,fill=fill)
        x+=d.textlength(ch,font=font)+track
    return x

def wrap(d,text,font,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textlength(t,font=font)<=maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def fit_title(d,text,maxw,maxlines=3):
    for size in range(74,40,-2):
        f=ImageFont.truetype(BOLD,size)
        lines=wrap(d,text,f,maxw)
        if len(lines)<=maxlines: return f,lines,size
    f=ImageFont.truetype(BOLD,42); return f,wrap(d,text,f,maxw)[:maxlines],42

logo=Image.open(os.path.join(OG,"..","logo-light.png")).convert("RGBA")
lh=64; lw=int(logo.width*lh/logo.height); logo=logo.resize((lw,lh),Image.LANCZOS)

def build(name,title):
    img=Image.new("RGB",(W,H),GREEN_D); d=ImageDraw.Draw(img)
    d.rectangle([0,0,W,10],fill=ACID)                       # top accent
    img.paste(logo,(64,52),logo)                            # wordmark
    # kicker
    kf=ImageFont.truetype(SEMI,24)
    draw_tracked(d,(66,150),kicker_for(name),kf,ACID,6)
    # title block, vertically centred in [200,540]
    tf,lines,size=fit_title(d,title,1072)
    lh2=int(size*1.12); block=lh2*len(lines)
    y=200+((560-200)-block)//2
    for ln in lines:
        d.text((64,y),ln,font=tf,fill=WHITE); y+=lh2
    img.save(os.path.join(OG,name+".png"))

count=0; missing=[]
for p in sorted(glob.glob(os.path.join(OG,"*.png"))):
    name=os.path.splitext(os.path.basename(p))[0]
    title=og_title(page_for(name))
    if not title: missing.append(name); continue
    build(name,title); count+=1

# bonus: dedicated banner for the new Apna Ghar calculator page
for slug2 in ["blog-pm-apna-ghar-housing-finance-calculator","blog-top-dividend-stocks-pakistan"]:
    t=og_title("blog/"+slug2[len("blog-"):]+".html")
    if t: build(slug2,t); count+=1

print("generated",count,"banners; missing titles:",missing)
