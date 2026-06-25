from PIL import Image
A="assets/"

# ---- 1. logo-light.png: recolor the NEW logo teal->white, keep gold ----
src=Image.open(A+"logo.png").convert("RGBA")
px=src.load(); W,H=src.size
def is_gold(r,g,b):
    return r>140 and r>b+30 and g>90        # gold/amber stays
for y in range(H):
    for x in range(W):
        r,g,b,a=px[x,y]
        if a==0: continue
        if not is_gold(r,g,b):
            px[x,y]=(255,255,255,a)          # teal -> white (keep alpha for smooth edges)
src.save(A+"logo-light.png")
print("logo-light.png written", src.size)

# ---- 2. favicons from new favicon.png ----
fav=Image.open(A+"favicon.png").convert("RGBA")
# square-pad if needed
w,h=fav.size
if w!=h:
    s=max(w,h); canvas=Image.new("RGBA",(s,s),(0,0,0,0))
    canvas.paste(fav,((s-w)//2,(s-h)//2),fav); fav=canvas
for size,name in [(16,"favicon-16.png"),(32,"favicon-32.png"),(180,"apple-touch-icon.png"),
                  (192,"favicon-192.png"),(512,"favicon-512.png")]:
    fav.resize((size,size),Image.LANCZOS).save(A+name)
    print("wrote",name)

# ---- 3. favicon.ico (multi-res) at repo root ----
fav.save("favicon.ico", format="ICO", sizes=[(16,16),(32,32),(48,48)])
print("favicon.ico written")
