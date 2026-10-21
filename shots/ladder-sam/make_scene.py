"""Writes rigs/ladder_scene.json: scenery doodles plus the climbing man.
usage: python3 shots/ladder-sam/make_scene.py shots/ladder-sam/man_keys.json
The man is drawn by agent each frame as a stick figure in the doodle's sparse hand (a round head, one line for the
body, a three-line wrap, two-segment arms and legs), from joints read by eye on every film frame: head and waist per
frame, and hands and feet held on the rungs where they were put until the film moves them (man_keys.json "moves").
He is drawn on the ladder's own plane so he renders in black as the subject of the event."""
import json, math, sys
import numpy as np
R='/home/claude/cartoon-archive/'
cam=json.load(open(R+'shots/ladder-sam/camera.json')); n=len(cam)
MK=json.load(open(sys.argv[1]))
def series(name):
    a=np.array([MK[name][str(f)] for f in range(n)],float)
    b=a.copy(); b[1:-1]=0.25*a[:-2]+0.5*a[1:-1]+0.25*a[2:]   # light smoothing of the by-eye readings
    # on the ladder (frame 8 on) each push is spread over its neighbours so the body rises a few px a frame, not in jumps
    w=np.exp(-0.5*(np.arange(-4,5)/1.6)**2); c=b.copy()
    for f in range(8,n):
        idx=np.clip(np.arange(f-4,f+5),0,n-1); ww=w*(idx>=6); c[f]=(b[idx]*ww[:,None]).sum(0)/ww.sum()
    return c
HEAD,WAIST=series('head'),series('waist')
# The drawn ladder is shorter than the film's (its top is at y 51 where the film's runs out of the frame), so every
# reading is scaled about the ladder's foot so that the climb ends on the drawn ladder with the head inside the frame.
BASE=np.array([100.,285.]); K=0.865
def fit(q,k=K): return BASE+(np.array(q,float)-BASE)*k
def kf(f): t=np.clip((f-3)/6,0,1); return 1-(1-K)*t*t*(3-2*t)   # on the ground (frames 0-3) he is not scaled; the scale eases in as he mounts
HEAD=np.array([fit(q,kf(f)) for f,q in enumerate(HEAD)]); WAIST=np.array([fit(q,kf(f)) for f,q in enumerate(WAIST)])
# The drawn ladder (it does not move); its rails and rungs are where his hands and feet go.
LAD=[np.array(q,float) for q in json.load(open(R+'shots/ladder-gwp/shot.json'))['cast']['frames'][0]]
def rail_x(r,y):
    s=LAD[r]
    for (x0,y0),(x1,y1) in zip(s[:-1],s[1:]):
        if min(y0,y1)<=y<=max(y0,y1) and y0!=y1: return x0+(y-y0)/(y1-y0)*(x1-x0)
    return s[0][0] if y<s[0][1] else s[-1][0]
def on(seg,u):
    # a point u of the way along a drawn stroke (0 = its left end)
    s=LAD[seg]; L=np.r_[0,np.cumsum(np.hypot(*np.diff(s,axis=0).T))]; t=u*L[-1]; i=min(np.searchsorted(L,t,side='right')-1,len(s)-2)
    return s[i]+(s[i+1]-s[i])*(t-L[i])/max(L[i+1]-L[i],1e-9)
def target(q):
    # ["rung", i, u]: rung i (0 = bottom) of the drawn ladder, u along it; ["rail", r, u]: rail r (0 left, 1 right); else a frame point (ground)
    if isinstance(q[0],str): return on(q[1]+2 if q[0]=='rung' else q[1],q[2])
    return np.array(q,float)
# On the ladder his waist sits over the left rail (seen from behind his body hangs over the left half of the
# ladder, as in the film where the man is over his own ladder's left rail); the drawn ladder stands about 25 px right
# of the film's, so the waist is moved onto it, easing in from frame 5 (at the foot) to frame 10.
for f in range(n):
    s=np.clip((f-5)/5,0,1); s=s*s*(3-2*s)
    WAIST[f][0]+=s*(rail_x(0,WAIST[f][1])+2-WAIST[f][0])
# One body size every frame: the torso is one line of fixed length. Its lean comes from the film (head over waist),
# kept bent forward toward the ladder on the climb, and bent further over the ladder at the top (frames 30-37).
TORSO=40.0
ang=np.array([math.atan2(HEAD[f][0]-WAIST[f][0],WAIST[f][1]-HEAD[f][1]) for f in range(n)])
for f in range(n):
    on_l=np.clip((f-5)/4,0,1); top=np.clip((f-28)/6,0,1); top=top*top*(3-2*top)
    a=ang[f]*(1-on_l)+max(ang[f],math.radians(30))*on_l
    a=a*(1-top)+math.radians(44)*top
    HEAD[f]=WAIST[f]+TORSO*np.array([math.sin(a),-math.cos(a)])
def contact(f,limb):
    p=target(MK['start'][limb])
    for f0,f1,q in MK['moves'][limb]:
        q=target(q)
        if f>=f1: p=q; continue
        if f>f0:
            t=(f-f0)/(f1-f0); t=t*t*(3-2*t); lift=math.sin(math.pi*t)*4
            return p+(q-p)*t+np.array([-0.4,-1.0])*lift   # the hand or foot comes off the rung a little, out from the ladder, on the way
        break
    return p
PREV={}
def joint(p,q,L,prefer,key=None):
    # the elbow or knee: keeps a slight bend even at full reach, and stays on the side it was on in the previous frame
    d=q-p; D=max(np.hypot(*d),1e-6); D2=min(D,2*L*0.97)
    h=math.sqrt(max(L*L-(D2/2)**2,0)); m=p+d/D*(D2/2); nrm=np.array([-d[1],d[0]])/D
    a,b=m+nrm*h,m-nrm*h
    pick=a if prefer(a)>=prefer(b) else b
    if key in PREV:
        o=PREV[key]; alt=b if pick is a else a
        if np.hypot(*(alt-o))+12<np.hypot(*(pick-o)): pick=alt
    PREV[key]=pick
    return pick
# The doodle's ladder is drawn with a heavy, slightly wobbly line; the man is drawn in the same hand: each line is a few
# points with a small fixed waver (the same waver every frame, so the line does not boil) and traced twice 1 px apart.
WOB=[0,0.9,-0.7,0.5,0]
def hand(pts,wob=True):
    P=np.array(pts,float); out=[]
    if wob and len(P)==2:
        d=P[1]-P[0]; nr=np.array([-d[1],d[0]])/max(np.hypot(*d),1e-6)
        P=np.array([P[0]+d*t+nr*w for t,w in zip(np.linspace(0,1,5),WOB)])
    elif wob:
        Q=[P[0]]
        for a_,b_ in zip(P[:-1],P[1:]):
            d=b_-a_; nr=np.array([-d[1],d[0]])/max(np.hypot(*d),1e-6); Q+=[a_+d*0.5+nr*0.8,b_]
        P=np.array(Q)
    for o in (-0.55,0.55):
        d=P[-1]-P[0]; nr=np.array([-d[1],d[0]])/max(np.hypot(*d),1e-6)
        out.append((P+nr*o).tolist())
    return out
def man(f):
    H,P=HEAD[f],WAIST[f]
    ax=(P-H)/np.hypot(*(P-H)); N=H+ax*8
    st=[]
    st+=hand([(H+np.array([7*math.cos(a),7.5*math.sin(a)])).tolist() for a in np.linspace(-0.4,2*math.pi-0.1,9)],wob=False)   # head: one loop, not quite closed
    st+=hand([N,P])                                                                                                   # body: one line
    S=N+ax*3
    for limb in ('lh','rh'):
        q=contact(f,limb); e=joint(S,q,28,lambda z: z[1]-0.3*z[0],limb); st+=hand([S,e,q])
    for limb,sg in (('lf',1),('rf',-1)):
        q=contact(f,limb); Hp=P-np.array([2.5*sg,0.0])
        D=np.hypot(*(q-Hp))
        if D>74: q=Hp+(q-Hp)*74/D   # never a stretched leg
        k=joint(Hp,q,38,lambda z: z[0]+0.6*z[1],limb); st+=hand([Hp,k,q])
    return [[[round(x-cam[f][0],1),round(y-cam[f][1],1)] for x,y in s] for s in st]
objs=[
 {"id":"trees","plane":"far","qd":"tree","box":[-10,-10,130,170],"skip":1},
 {"id":"fence","plane":"far","qd":"fence","box":[300,-5,390,130],"skip":2},
 {"id":"haystack","plane":"stack","qd":"mountain","box":[0,-40,440,265],"strokes":1,"skip":3},
 {"id":"ground","plane":"ground","class":"ground","why":"no Quick, Draw! category is a ground line; this is the edge of the sand in front of the haystack, sloping down to the right as in the film","strokes":[[[-10,262],[90,258],[200,262],[300,268],[394,262]]]},
]
for f in range(n):
    objs.append({"id":f"man{f:02d}","plane":"char","class":"man","why":"the man who climbs the ladder, the subject of the event; no Quick, Draw! category is a person who can be posed, so he is drawn by agent each frame as a sparse stick figure from head and waist read on every film frame, with each hand and foot held on a rung until the film moves it","strokes":man(f),"visible":[f,f]})
S={"z_ref":2,
 "camera":{"x":[c[0] for c in cam],"y":[c[1] for c in cam],"source":"shots/ladder-sam/camera.json: phase correlation of the footage; the shot is locked off, so this is only the film's frame shake of up to 3 px, checked on the fence and the ground"},
 "planes":[{"id":"far","z":8,"label":"Trees and fence behind the haystack","z_from_depth":"top"},
           {"id":"stack","z":2.7,"label":"Haystack","z_from_depth":"middle"},
           {"id":"char","z":2,"label":"Ladder and the man climbing it"},
           {"id":"ground","z":1.8,"label":"Sand in front","z_from_depth":"bottom"}],
 "objects":objs,
 "notes":{"0":"the ladder leans against the haystack; a man walks in from the left","4":"he reaches the ladder and takes the left rail with his right hand","6":"right foot on the bottom rung","8":"first push: he steps up, left foot on the second rung","16":"halfway up, one rung at a time, hand then foot","26":"a push brings his head level with the top of the ladder","32":"the last push stands him up at the top of the ladder, feet on the top-but-one rung, hands on the top","37":"he stands at the top of the ladder against the haystack, head inside the frame"},
 "no_cel":"the SAM mask covers the man in most frames, so cel paint would erase the man and leave the ladder alone"}
json.dump(S,open(R+'rigs/ladder_scene.json','w'),indent=1)
print(len(objs))
