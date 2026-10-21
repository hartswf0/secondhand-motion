"""Writes rigs/ladder_scene.json: scenery doodles plus the climbing man, drawn by agent from keyed joints."""
import json, math, sys
import numpy as np
R='/home/claude/cartoon-archive/'
cam=json.load(open(R+'shots/ladder-sam/camera.json')); n=len(cam)
MK=json.load(open(sys.argv[1]))   # man keys {frame: {head,neck,hip,lh,rh,lf,rf}}
ks=sorted(int(k) for k in MK)
def cr(f, name):
    # Catmull-Rom through keys for body points
    if f<=ks[0]: return np.array(MK[str(ks[0])][name],float)
    if f>=ks[-1]: return np.array(MK[str(ks[-1])][name],float)
    i=max(j for j,k in enumerate(ks) if k<=f); a,b=ks[i],ks[i+1]; t=(f-a)/(b-a)
    P=lambda j: np.array(MK[str(ks[min(max(j,0),len(ks)-1)])][name],float)
    p0,p1,p2,p3=P(i-1),P(i),P(i+1),P(i+2)
    return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3)
def hold(f,name):
    # hands and feet stay planted until the next key moves them; the move eases over the last frames before the key
    if f<=ks[0]: return np.array(MK[str(ks[0])][name],float)
    if f>=ks[-1]: return np.array(MK[str(ks[-1])][name],float)
    i=max(j for j,k in enumerate(ks) if k<=f); a,b=ks[i],ks[i+1]
    A=np.array(MK[str(a)][name],float); B=np.array(MK[str(b)][name],float)
    if np.allclose(A,B): return A
    t=(f-a)/(b-a); t=t*t*(3-2*t)
    lift=math.sin(math.pi*t)*3  # the hand or foot comes off the rung a little as it moves
    return A+(B-A)*t+np.array([-lift*0.5,-lift])
def limb(p,q,L,side):
    d=q-p; D=np.hypot(*d)
    if D>=2*L-0.5: return [p.tolist(),((p+q)/2).tolist(),q.tolist()]
    h=math.sqrt(L*L-(D/2)**2); m=(p+q)/2; nrm=np.array([-d[1],d[0]])/D*side
    return [p.tolist(),(m+nrm*h).tolist(),q.tolist()]
def man(f):
    H,N,P=cr(f,'head'),cr(f,'neck'),cr(f,'hip')
    ax=(P-N)/np.hypot(*(P-N)); pr=np.array([-ax[1],ax[0]])   # pr points to the man's left on screen when climbing up-right
    st=[]
    st.append([(H+6.5*np.array([math.cos(a),math.sin(a)])).tolist() for a in np.linspace(0,2*math.pi,13)])
    sw,hw=16,19; L=np.hypot(*(P-N))
    body=[N+pr*sw*0.6-ax*2, N+pr*sw, N+pr*hw+ax*L*0.6, P+pr*hw*0.9, P+ax*4, P-pr*hw*0.9, N-pr*hw+ax*L*0.6, N-pr*sw, N-pr*sw*0.6-ax*2, N+pr*sw*0.6-ax*2]
    st.append([q.tolist() for q in body])
    sl,sr=N+pr*sw*0.8+ax*3, N-pr*sw*0.8+ax*3
    st.append(limb(sl,hold(f,'lh'),17,-1)); st.append(limb(sr,hold(f,'rh'),17,-1))
    hl,hr=P+pr*7,P-pr*7
    st.append(limb(hl,hold(f,'lf'),27,1)); st.append(limb(hr,hold(f,'rf'),27,1))
    return [[[round(x-cam[f][0],1),round(y-cam[f][1],1)] for x,y in s] for s in st]
objs=[
 {"id":"trees","plane":"far","qd":"tree","box":[-10,-10,130,170],"skip":1},
 {"id":"fence","plane":"far","qd":"fence","box":[300,-5,390,130],"skip":2},
 {"id":"haystack","plane":"stack","qd":"mountain","box":[0,-40,440,265],"strokes":1,"skip":3},
 {"id":"ground","plane":"ground","class":"ground","why":"no Quick, Draw! category is a ground line; this is the edge of the sand in front of the haystack, sloping down to the right as in the film","strokes":[[[-10,262],[90,258],[200,262],[300,268],[394,262]]]},
]
for f in range(n):
    objs.append({"id":f"man{f:02d}","plane":"man","class":"man","why":"the man who climbs the ladder; no Quick, Draw! category is a person who can be posed, so he is drawn by agent each frame from joints keyed by eye on the film (head, neck, hip, both hands and both feet), with hands and feet held on the rungs between moves","strokes":man(f),"visible":[f,f]})
S={"z_ref":2,
 "camera":{"x":[c[0] for c in cam],"y":[c[1] for c in cam],"source":"shots/ladder-sam/camera.json: phase correlation of the footage; the shot is locked off, so this is only the film's frame shake of up to 3 px, checked on the fence and the ground"},
 "planes":[{"id":"far","z":8,"label":"Trees and fence behind the haystack","z_from_depth":"top"},
           {"id":"stack","z":2.7,"label":"Haystack","z_from_depth":"middle"},
           {"id":"man","z":2,"label":"The man climbing"},
           {"id":"char","z":2,"label":"Ladder"},
           {"id":"ground","z":1.8,"label":"Sand in front","z_from_depth":"bottom"}],
 "objects":objs,
 "notes":{"0":"the ladder leans against the haystack; a man comes in from the left","4":"he reaches the foot of the ladder and takes hold of it","10":"his first foot is on the bottom rungs","19":"halfway up, climbing one rung at a time","28":"his head reaches the top of the ladder","37":"he is at the top, about to step onto the haystack"},
 "no_cel":"the SAM mask covers the man in most frames, so cel paint would erase the man and leave the ladder alone"}
json.dump(S,open(R+'rigs/ladder_scene.json','w'),indent=1)
print(len(objs))
