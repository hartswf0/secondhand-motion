import sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '.')
import gen
args=sys.argv[2:]
cfg=[tuple(float(x) for x in a.split(',')) for a in args]   # yaw,rot,hy
W=330; cols=5; rows=(len(cfg)+cols-1)//cols; im=Image.new('RGB',(W*cols,300*rows),'white'); d=ImageDraw.Draw(im)
for i,(yaw,rot,hy) in enumerate(cfg):
    st,ex=gen.view(yaw,rot,hy)
    C=np.array([(i%cols)*W+W/2,(i//cols)*300+150.]); s=1.5
    for j,q in enumerate(st+list(ex.values())):
        pts=[tuple(p) for p in q*s+C]; d.line(pts,fill=(0,0,0) if j<12 else (0,0,200),width=2)
    d.text(((i%cols)*W+4,(i//cols)*300+4),f'{yaw},{rot},{hy}',fill=(200,0,0))
im.save(sys.argv[1])
