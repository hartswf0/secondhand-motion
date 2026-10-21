import sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0,'.'); import gen2
cfg=[tuple(float(x) for x in a.split(',')) for a in sys.argv[2:]]
W=300; cols=5; rows=(len(cfg)+cols-1)//cols; im=Image.new('RGB',(W*cols,260*rows),'white'); d=ImageDraw.Draw(im)
for i,c in enumerate(cfg):
    st=gen2.key(c[0],c[1],c[2],c[3] if len(c)>3 else 1)
    C=np.array([(i%cols)*W+W/2,(i//cols)*260+120.])
    for q in st: d.line([tuple(p) for p in q*1.0+C],fill=0,width=2)
    d.text(((i%cols)*W+4,(i//cols)*260+4),str(c),fill=(200,0,0))
im.save(sys.argv[1])
