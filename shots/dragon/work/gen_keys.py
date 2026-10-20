"""Keys for the dragon from the measurements: the doodle placed once on frame 10 (scale S, offset O, neck
anchor on the measured head pivot), the head turned about the neck by the measured angle, then the
camera's settle (frame-10 -> frame f similarity) applied to every point. usage: gen_keys.py out.json S ox oy [frames...]"""
import json, math, sys, numpy as np
r=json.load(open('shots/dragon/work/measure.json')); sp=json.load(open('rigs/dragon_spec.json'))
out=sys.argv[1]; S=float(sys.argv[2]); O=np.array([float(sys.argv[3]),float(sys.argv[4])])
frames=[int(x) for x in sys.argv[5:]] or list(range(32))
A={k:np.array(v,float)*S+O for k,v in sp['anchors'].items()}
P={}
for f in frames:
    a=math.radians(r[f]['head_deg']); R=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    M=np.array(r[f]['cam']); pts=dict(A)
    pts['nose']=A['neck']+R@(A['nose']-A['neck'])
    P[str(f)]={k:[round(float(x),1) for x in M[:,:2]@v+M[:,2]] for k,v in pts.items()}
json.dump(P,open(out,'w'),indent=0)
