import json, math, sys
# frame: cx, cy, r, body angle deg, depth, open, spout angle deg
K = json.load(open(sys.argv[1])); out={}
for f,(cx,cy,r,b,dep,op,sa) in K.items():
    br=math.radians(b); bx,by=math.cos(br),math.sin(br); dx,dy=by,-bx
    sw=math.radians(sa-(b+68)); sw=math.atan2(math.sin(sw),math.cos(sw))
    out[f]={"rim_h":[round(cx-r*dx,1),round(cy-r*dy,1)],"rim_o":[round(cx+r*dx,1),round(cy+r*dy,1)],
            "rim_c":[cx,cy],"open":op,"depth":dep,"swing":round(sw,3),"_face":1}
json.dump(out,open(sys.argv[2],'w'),indent=1)
