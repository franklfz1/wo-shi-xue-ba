"""
render_frames.py — 根据 script.json + voice_timeline.json 渲染每一帧 PNG（增强版 v3）。
"""
import json, sys, argparse, math, os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H    = 1080, 1920
FPS      = 30
FONT_PTH = "C:/Windows/Fonts/msyh.ttc"

COLORS = dict(
    bg_dark=(18,18,36), bg_dark2=(10,10,30),
    accent_yellow=(255,200,50), accent_orange=(255,140,50),
    accent_blue=(60,160,255), accent_purple=(160,100,255),
    accent_green=(50,220,130), accent_red=(255,80,80),
    accent_pink=(255,120,180),
    text_white=(255,255,255), text_light=(200,210,230), text_dim=(120,130,160),
    card_bg=(28,32,58), card_border=(60,70,120),
    bar_bg=(0,0,0,160),
)

def get_font(size, bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc" if bold else FONT_PTH, size)
    except Exception:
        return ImageFont.load_default()

def lerp_c(c1,c2,t): return tuple(int(a+(b-a)*t) for a,b in zip(c1,c2))
def ease_bk(t):
    c=1.70158; return 1+(c+1)*(t-1)**3+c*(t-1)**2 if t<=1 else 1
def ease_el(t):
    if t in (0,1): return t
    return 2**(-10*t)*math.sin((t*10-0.75)*2*math.pi/3)+1

def grad_bg(draw,w,h,ct,cb):
    for y in range(h):
        t=y/h; c=lerp_c(ct,cb,t)
        draw.line([(0,y),(w,y)],fill=c)

def dots(draw,w,h,t):
    random.seed(42)
    for i in range(15):
        x=random.randint(50,w-50); y0=random.randint(100,h-300)
        r=random.randint(3,8); a=random.randint(20,60)
        cols=[COLORS[k] for k in ("accent_yellow","accent_blue","accent_purple","accent_green","accent_pink")]
        dy=math.sin(t*2+i*0.7)*5
        draw.ellipse([x-r,y0+dy-r,x+r,y0+dy+r],fill=(*cols[i%5],a))

# ── renderers ─────────────────────────────────────────────────────────
def render_intro(scene, t, fi, w, h):
    img=Image.new("RGBA",(w,h),(*COLORS["bg_dark"],255)); draw=ImageDraw.Draw(img)
    grad_bg(draw,w,h,(25,20,50),(10,10,30)); dots(draw,w,h,t)
    p=min(1.0,t/1.5)
    # beam
    bw=int(w*p*1.2); ba=int(100*(1-p*0.5))
    for y in range(0,min(400,int(400*p))):
        a=int(ba*(1-y/400)); draw.line([(w//2-bw//2,y),(w//2+bw//2,y)],fill=(*COLORS["accent_yellow"],a))
    if p>0.3:
        tp=min(1.0,(p-0.3)/0.3); ty=320; tt=scene.get("tag","初中数学"); tf=get_font(32,True)
        tw=tf.getbbox(tt)[2]-tf.getbbox(tt)[0]; tbgw=tw+60; tbgx=(w-tbgw)//2
        s=ease_bk(tp)
        draw.rounded_rectangle([tbgx,ty,tbgx+tbgw,ty+50],radius=25,fill=(*COLORS["accent_orange"],int(200*s)))
        if tp>0.2: draw.text(((w-tw)//2,ty+8),tt,font=tf,fill=(255,255,255,int(255*min(1,tp*2))))
    if p>0.4:
        tp2=min(1.0,(p-0.4)/0.4); title=scene.get("subtitle",scene.get("title","")); tf2=get_font(96,True)
        bb=tf2.getbbox(title); tw2=bb[2]-bb[0]; th2=bb[3]-bb[1]
        tx,ty=(w-tw2)//2,(h-th2)//2-60
        sc=ease_el(tp2)
        if sc>0.1:
            draw.text((tx+3,ty+3),title,font=tf2,fill=(0,0,0,int(120*min(1,tp2*2))))
            draw.text((tx,ty),title,font=tf2,fill=(*COLORS["text_white"],int(255*min(1,tp2*1.5))))
    if p>0.7:
        sp=min(1.0,(p-0.7)/0.3); et=scene.get("episode","第1集"); ef=get_font(30)
        bb2=ef.getbbox(et); ew=bb2[2]-bb2[0]
        draw.text(((w-ew)//2,h//2+80),et,font=ef,fill=(*COLORS["text_dim"],int(200*sp)))
    if p>0.8:
        lw=int((w-200)*min(1,(p-0.8)/0.2)); lx=(w-lw)//2
        draw.line([(lx,h-250),(lx+lw,h-250)],fill=(*COLORS["accent_yellow"],120))
    return img

def render_diagram(scene, t, fi, w, h):
    img=Image.new("RGBA",(w,h),(*COLORS["bg_dark"],255)); draw=ImageDraw.Draw(img)
    grad_bg(draw,w,h,(22,22,45),(12,12,28)); dots(draw,w,h,t)
    p=min(1.0,t/0.8); cy=250+int((1-ease_bk(p))*300)
    draw.rectangle([0,0,w,6],fill=(*COLORS["accent_yellow"],255))
    draw.rounded_rectangle([60,cy,w-60,h-350+int((1-ease_bk(p))*300)],radius=24,fill=(*COLORS["card_bg"],230),outline=(*COLORS["card_border"],100),width=2)
    content=scene.get("subtitle",scene.get("visual_content","")); lines=content.split("\n")
    yo=cy+60
    for i,line in enumerate(lines[:10]):
        if not line.strip(): yo+=30; continue
        lp=min(1.0,max(0,(t-0.3-i*0.25)/0.4))
        if lp<=0: yo+=70; continue
        fs=48; parts=line.split("**"); xo=140; yo+=70
        f=get_font(fs)
        for j,pt in enumerate(parts):
            if not pt: continue
            ib=(j%2==1); uf=get_font(fs+4,True) if ib else f
            c=COLORS["accent_yellow"] if ib else COLORS["text_light"]
            bb=uf.getbbox(pt); pw=bb[2]-bb[0]
            if ib: draw.rounded_rectangle([xo-10,yo-2,xo+pw+10,yo+fs+8],radius=6,fill=(*COLORS["accent_yellow"],int(40*lp)))
            draw.text((xo,yo),pt,font=uf,fill=(*c,int(255*lp))); xo+=pw+8
    sl=scene.get("label",""); 
    if sl:
        lf=get_font(28,True); bb2=lf.getbbox(sl); lw2=bb2[2]-bb2[0]
        draw.rounded_rectangle([60,180,60+lw2+30,230],radius=12,fill=(*COLORS["accent_blue"],180))
        draw.text((75,185),sl,font=lf,fill=(255,255,255,230))
    return img

def render_svg(scene,t,fi,w,h,svg_dir=None):
    img=Image.new("RGBA",(w,h),(*COLORS["bg_dark"],255)); draw=ImageDraw.Draw(img)
    grad_bg(draw,w,h,(15,15,35),(8,8,25))
    if svg_dir:
        sp=Path(svg_dir)/f"svg_frame_{fi:04d}.png"
        if sp.exists():
            sf=Image.open(sp).convert("RGBA"); sf=sf.resize((w,h),Image.LANCZOS); img.paste(sf,(0,0),sf); return img
    draw.rectangle([0,0,w,6],fill=(*COLORS["accent_purple"],255))
    msg=scene.get("subtitle","[动画]"); f2=get_font(60); bb3=f2.getbbox(msg); mw3=bb3[2]-bb3[0]
    draw.text(((w-mw3)//2,(h-80)//2),msg,font=f2,fill=(*COLORS["accent_purple"],200))
    return img

def render_quiz(scene,t,fi,w,h):
    img=Image.new("RGBA",(w,h),(*COLORS["bg_dark"],255)); draw=ImageDraw.Draw(img)
    grad_bg(draw,w,h,(20,12,30),(10,8,20)); dots(draw,w,h,t)
    draw.rectangle([0,0,w,6],fill=(*COLORS["accent_red"],255))
    qd=scene.get("quiz_data",{}); qn=qd.get("question",scene.get("subtitle","?")); opts=qd.get("options",[]); ans=qd.get("answers",[])
    rt=scene.get("reveal_time",5.0)
    qp=min(1.0,t/0.6); qf=get_font(52,True); bb4=qf.getbbox(qn); qw4=bb4[2]-bb4[0]
    draw.text(((w-qw4)//2,200+int((1-ease_bk(qp))*50)),qn,font=qf,fill=(*COLORS["text_white"],int(255*min(1,qp*1.5))))
    if t<rt:
        cd=max(0,rt-t); cdf=get_font(36); cdt=f"思考一下... {cd:.1f}s"; bb5=cdf.getbbox(cdt)
        draw.text(((w-(bb5[2]-bb5[0]))//2,320),cdt,font=cdf,fill=(*COLORS["accent_yellow"],200))
    cols=[COLORS[k] for k in ("accent_blue","accent_red","accent_green","accent_purple")]; lbls=["A","B","C","D"]
    rev=(t>=rt)
    for i,opt in enumerate(opts[:4]):
        bp=min(1.0,max(0,(t-0.3-i*0.2)/0.5))
        if bp<=0: continue
        sc=ease_bk(bp); c=cols[i%4]; ic=ans[i] if i<len(ans) else False
        draw.rounded_rectangle([80,450+i*220,w-80,450+i*220+180],radius=16,fill=(*c,int(40*sc)),outline=(*c,int(180*sc)),width=3)
        draw.ellipse([130-28,450+i*220+60-28,130+28,450+i*220+60+28],fill=(*c,int(200*sc)))
        lf2=get_font(32,True); bb6=lf2.getbbox(lbls[i])
        draw.text((130-(bb6[2]-bb6[0])//2,450+i*220+60-(bb6[3]-bb6[1])//2),lbls[i],font=lf2,fill=(255,255,255,int(255*sc)))
        draw.text((200,450+i*220+50),opt,font=get_font(40,True),fill=(*COLORS["text_white"],int(230*sc)))
        if rev and i<len(ans):
            if ic: draw.text((w-180,450+i*220+55),"✓",font=get_font(50,True),fill=(*COLORS["accent_green"],255)); draw.rounded_rectangle([80,450+i*220,w-80,450+i*220+180],radius=16,outline=(*COLORS["accent_green"],255),width=4)
            else: draw.text((w-180,450+i*220+55),"✗",font=get_font(50,True),fill=(*COLORS["accent_red"],255))
    if rev: hf=get_font(32); ht="答案揭晓！"; bb7=hf.getbbox(ht); draw.text(((w-(bb7[2]-bb7[0]))//2,h-280),ht,font=hf,fill=(*COLORS["accent_yellow"],230))
    return img

def render_summary(scene,t,fi,w,h):
    img=Image.new("RGBA",(w,h),(*COLORS["bg_dark"],255)); draw=ImageDraw.Draw(img)
    grad_bg(draw,w,h,(10,30,20),(5,15,10)); dots(draw,w,h,t)
    draw.rectangle([0,0,w,6],fill=(*COLORS["accent_green"],255))
    tp=min(1.0,t/0.8); tf3=get_font(64,True); tt2=scene.get("summary_title","要点回顾"); bb8=tf3.getbbox(tt2); tw8=bb8[2]-bb8[0]
    draw.text(((w-tw8)//2,200+int((1-ease_bk(tp))*40)),tt2,font=tf3,fill=(*COLORS["accent_green"],int(255*min(1,tp*1.5))))
    pts=scene.get("subtitle","").split("\n"); y=380; pf=get_font(44,True)
    for i,pt in enumerate(pts[:6]):
        pp=min(1.0,max(0,(t-0.5-i*0.35)/0.5)); 
        if pp<=0: y+=130; continue
        sc=ease_bk(pp); ox=int((1-sc)*100)
        draw.ellipse([100+ox-22,y+8-22,100+ox+22,y+8+22],fill=(*COLORS["accent_green"],int(220*pp)))
        cf=get_font(28,True); bb9=cf.getbbox("✓")
        draw.text((100+ox-(bb9[2]-bb9[0])//2,y+8-(bb9[3]-bb9[1])//2),"✓",font=cf,fill=(255,255,255,int(255*pp)))
        draw.text((170+ox,y),pt,font=pf,fill=(*COLORS["text_white"],int(230*pp)))
        bw=int((w-200)*min(1,pp)); 
        draw.rounded_rectangle([100,y+70,100+bw,y+78],radius=4,fill=(*COLORS["accent_green"],int(60*pp)))
        draw.rounded_rectangle([100,y+70,w-100,y+78],radius=4,outline=(*COLORS["card_border"],60),width=1)
        y+=130
    return img

# ── main render loop ────────────────────────────────────────────────────
RENDERERS={"intro":render_intro,"title_card":render_intro,"concept":render_diagram,
           "static_diagram":render_diagram,"explanation":render_diagram,
           "animation":render_diagram,"svg_animation":render_diagram,
           "quiz":render_quiz,"summary":render_summary,"outro":render_intro}

def render_all(script,timeline,out_dir,svg_dir=None):
    op=Path(out_dir); op.mkdir(parents=True,exist_ok=True)
    td=timeline[-1]["end"] if timeline else 10
    tf=int(td*FPS)+2; print(f"  {td:.1f}s -> {tf} frames")
    fi=0
    for si,seg in enumerate(timeline):
        ss,se=seg["start"],seg["end"]; sf=int(se*FPS)-int(ss*FPS)
        sc=next((s for s in script["scenes"] if s["id"]==seg["scene_id"]),script["scenes"][0])
        vt=sc.get("visual_type","static_diagram")
        if vt=="svg_animation" and svg_dir:
            for f in range(sf):
                t=ss+f/FPS; img=render_svg(sc, t, fi, W, H, svg_dir)
                img=add_bar(img,seg["text"],W,H); img.save(op/f"frame_{fi:04d}.png"); fi+=1
                if fi%100==0: print(f"  {fi}/{tf}",end="\r")
        else:
            rn=RENDERERS.get(vt,render_diagram)
            for f in range(sf):
                t=ss+f/FPS; img=rn(sc,t,fi,W,H)
                img=add_bar(img,seg["text"],W,H); img.save(op/f"frame_{fi:04d}.png"); fi+=1
                if fi%100==0: print(f"  {fi}/{tf}",end="\r")
    print(f"\n  OK {fi} frames -> {out_dir}")
    return str(out_dir)

def add_bar(img,text,w,h):
    draw=ImageDraw.Draw(img); bh=110; by=h-bh
    bar=Image.new("RGBA",(w,bh+40),(0,0,0,0)); bd=ImageDraw.Draw(bar)
    for y in range(bh+40): bd.line([(0,y),(w,y)],fill=(0,0,0,int(min(180,180*y/bh))))
    img.paste(bar,(0,by-40),bar)
    draw2=ImageDraw.Draw(img); f2=get_font(34)
    # split into up to 2 lines
    mc=28; lines2=[]
    for i in range(0,len(text),mc):
        lines2.append(text[i:i+mc])
    for li,ln in enumerate(lines2[:2]):
        bb=f2.getbbox(ln); tw2=bb[2]-bb[0]
        draw2.text(((w-tw2)//2,by+15+li*42),ln,font=f2,fill=(255,255,255,245))
    return img

# ── CLI ──────────────────────────────────────────────────────────────────
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--script",required=True); ap.add_argument("--timeline",required=True)
    ap.add_argument("--output",required=True); ap.add_argument("--svg-dir",default=None)
    args=ap.parse_args()
    script=json.loads(args.script); timeline=json.load(open(args.timeline,"r",encoding="utf-8"))
    render_all(script,timeline,args.output,args.svg_dir)
