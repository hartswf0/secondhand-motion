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
    if q[0]=='at': return rail_at(q[1],q[2])
    if isinstance(q[0],str): return on(q[1]+2 if q[0]=='rung' else q[1],q[2])
    return np.array(q,float)
# On the ladder his waist sits over the left rail (seen from behind his body hangs over the left half of the
# ladder, as in the film where the man is over his own ladder's left rail); the drawn ladder stands about 25 px right
# of the film's, so the waist is moved onto it, easing in from frame 5 (at the foot) to frame 10.
# Ladder coordinates: a along the ladder from its foot (up), c across it (0 on the left rail, positive to the right).
LO=np.array([93.,284.]); LU=np.array([139.,-233.]); LU/=np.hypot(*LU); LV=np.array([-LU[1],LU[0]])
def lc(p): p=np.asarray(p,float)-LO; return np.array([p@LU,p@LV])
def pt(a,c): return LO+a*LU+c*LV
_RA=[lc(q) for q in LAD[1]][::-1]; _LA=[lc(q) for q in LAD[0]][::-1]
def cR(a): return float(np.interp(a,[q[0] for q in _RA],[q[1] for q in _RA]))   # the right rail's c at height a
def cL(a): return float(np.interp(a,[q[0] for q in _LA],[q[1] for q in _LA]))
def rail_at(r,a):
    # ["at", r, a]: the point on rail r at height a up the ladder (a hand gripping the rail between rungs)
    P=[lc(q) for q in LAD[r]][::-1]; c=float(np.interp(a,[q[0] for q in P],[q[1] for q in P])); return pt(a,c)
WAIST_ACROSS=0.5   # seen from behind his body hangs over the middle-left of the ladder, so both legs stand between the rails
for f in range(n):
    s=np.clip((f-1)/8,0,1)   # spread evenly over frames 1-9 so no frame carries a large sideways step
    tgt=WAIST[f].copy()
    for _ in range(6):   # moved sideways only (the film's height is kept): x where c is WAIST_ACROSS of the way across
        a,c=lc(tgt); tgt[0]+=(cL(a)+WAIST_ACROSS*(cR(a)-cL(a))-c)/LV[0]
    dx=s*(tgt[0]-WAIST[f][0]); WAIST[f][0]+=dx; HEAD[f][0]+=dx   # the head goes with the waist, so the lean read from the film is kept
# walking in (frames 0-9) the waist goes the same distance each frame, as the film man walks at an even pace
for f in range(1,9): x=WAIST[0][0]+(WAIST[9][0]-WAIST[0][0])*f/9; HEAD[f][0]+=x-WAIST[f][0]; WAIST[f][0]=x
# One body size every frame: the torso is one line of fixed length. Its lean comes from the film (head over waist),
# kept bent forward toward the ladder on the climb, and bent further over the ladder at the top (frames 30-37).
TORSO=40.0
LEG=42.0   # one leg bone; the leg is two
# Near the top the film man recedes from the camera and looks a little smaller, so from frame 24 the whole figure
# (torso, head, neck, reach) shrinks by up to 7 %, a fraction of a percent per frame.
def SC(f): t=np.clip((f-24)/13,0,1); return 1-0.07*t*t*(3-2*t)
ang=np.array([math.atan2(HEAD[f][0]-WAIST[f][0],WAIST[f][1]-HEAD[f][1]) for f in range(n)])
for f in range(n):
    on_l=np.clip((f-3)/6,0,1); on_l=on_l*on_l*(3-2*on_l); top=np.clip((f-28)/6,0,1); top=top*top*(3-2*top)
    a=ang[f]*(1-on_l)+max(ang[f],math.radians(30))*on_l
    a=a*(1-top)+math.radians(40)*top
    HEAD[f]=WAIST[f]+TORSO*SC(f)*np.array([math.sin(a),-math.cos(a)])
def contact(f,limb):
    p=target(MK['start'][limb])
    for f0,f1,q in MK['moves'][limb]:
        q=target(q)
        if f>=f1: p=q; continue
        if f>f0:
            t=(f-f0)/(f1-f0); t=t*t*(3-2*t); lift=math.sin(math.pi*t)
            if f0>=5: out={'lf':LU*3-LV*3,'rf':LU*3+LV*3,'lh':-LV*12,'rh':LV*12}[limb]   # on the ladder a foot comes up off its rung and a hand swings out to its own side
            else: out=np.array({'lf':(-1.6,-4.0),'rf':(-1.6,-4.0),'lh':(-5.0,-3.0),'rh':(6.0,-2.0)}[limb])
            return p+(q-p)*t+out*lift
        break
    return p
PREV={}
def joint(p,q,L,prefer,key=None,fore=False):
    # the elbow or knee: keeps a slight bend even at full reach, and stays on the side it was on in the previous frame
    d=q-p; D=max(np.hypot(*d),1e-6); D2=min(D,2*L*0.97)
    h=math.sqrt(max(L*L-(D2/2)**2,0)); m=p+d/D*(D2/2); nrm=np.array([-d[1],d[0]])/D
    if fore: h=min(h,0.45*D+4)   # an arm whose hand is close to the shoulder is reaching into the ladder (toward the haystack), so it is foreshortened, not folded out sideways
    a,b=m+nrm*h,m-nrm*h
    pick=a if prefer(a)>=prefer(b) else b
    if key is not None and key in PREV:
        o=PREV[key]; alt=b if pick is a else a
        if np.hypot(*(alt-o))+12<np.hypot(*(pick-o)): pick=alt
    if key is not None: PREV[key]=pick
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
PREVB={}
def limb_back(root,q,L,side,cos_out,lo_c=None,hi_c=None,key=None):
    # an elbow or knee for a figure seen from behind on the ladder: a two-bone limb of fixed length L per bone, bent in a
    # plane that leans out of the picture into the ladder, so only cos_out of the bend shows, out to the limb's own side
    # (side -1 left, +1 right). The drawn bones change length smoothly with the reach, never folding to a stub.
    A,B=lc(root),lc(q); d=B-A; D=max(np.hypot(*d),1e-6); h=math.sqrt(max(L*L-(D/2)**2,0))*cos_out
    nr=np.array([-d[1],d[0]])/D
    if nr[1]*side-0.6*nr[0]<0: nr=-nr   # the bend goes out to the limb's own side and, when the reach is across, downward (an elbow hangs below a hand held at shoulder height)
    if key in PREVB and nr@PREVB[key]<0 and abs(nr[1])<0.5: nr=-nr   # near the flip point the bend keeps the side it had last frame
    if key is not None: PREVB[key]=nr
    m=(A+B)/2+nr*h
    if lo_c is not None: m[1]=min(max(m[1],lo_c(m[0])+2),hi_c(m[0])-2)
    return pt(*m)
def skeleton(f):
    H,P=HEAD[f],WAIST[f]
    ax=(P-H)/np.hypot(*(P-H)); N=H+ax*8*SC(f); S=N+ax*3*SC(f)
    # on the ground (to frame 5) the old side-view joints; from frame 8 the back view on the ladder; blended between
    bl=np.clip((f-5)/3,0,1); bl=bl*bl*(3-2*bl)
    J={'H':H,'N':N,'P':P,'S':S}
    for limb,sg in (('lh',-1),('rh',1)):
        q=contact(f,limb); sgo=-1 if limb=='lh' else 1
        e0=joint(S,q,30,lambda z,sg=sgo: z[1]+sg*0.3*z[0],limb,fore=True)
        Sh=S+LV*sg*3
        e1=limb_back(Sh,q,30*SC(f),sg,0.5,key=limb)
        J[limb]=(Sh*bl+S*(1-bl),e0*(1-bl)+e1*bl,q)
    for limb,sg in (('lf',-1),('rf',1)):
        q=contact(f,limb); Hp0=P-np.array([2.5*(-sg),0.0]); Hp1=P+LV*sg*3-LU*5*SC(f); Hp=Hp0*(1-bl)+Hp1*bl   # on the ladder the hips sit 5 px below the waist line
        D=np.hypot(*(q-Hp))
        k0=joint(Hp0,q,39,lambda z: z[0]+0.6*z[1],limb)
        k1=limb_back(Hp1,q,LEG*SC(f),sg,0.75,cL,cR,key=limb)
        J[limb]=(Hp,k0*(1-bl)+k1*bl,q)
    return J
def _x(p1,p2,p3,p4):
    # proper crossing of segments p1p2 and p3p4
    d=lambda a,b,c:(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    d1,d2,d3,d4=d(p3,p4,p1),d(p3,p4,p2),d(p1,p2,p3),d(p1,p2,p4)
    return d1*d2<-1e-6 and d3*d4<-1e-6
RUNG_A=[lc(on(i,0.5))[0] for i in range(2,8)]
def check(f,J):
    # per-frame rejection: limbs that overlap or cross each other, an arm folded on itself or over the head, legs crossing the rails
    bad=[]
    segs={k:[(J[k][0],J[k][1]),(J[k][1],J[k][2])] for k in ('lh','rh','lf','rf')}
    ks=list(segs)
    for i in range(4 if f>=6 else 0):   # on the ground (walking in profile, to frame 5) an arm swinging past a leg is normal
        for j in range(i+1,4):
            for s1 in segs[ks[i]]:
                for s2 in segs[ks[j]]:
                    if _x(*s1,*s2): bad.append(f'{ks[i]} crosses {ks[j]}')
    for k in ('lh','rh'):
        r,e,q=J[k]; u,v=r-e,q-e; ang=math.degrees(math.acos(np.clip(u@v/max(np.hypot(*u)*np.hypot(*v),1e-6),-1,1)))
        if ang<60: bad.append(f'{k} folded ({ang:.0f} deg)')
        if f>=8:
            sg=-1 if k=='lh' else 1
            if lc(q)[0]>lc(J['S'])[0] and lc(e)[0]>lc(q)[0]+0.5: bad.append(f'{k} elbow above hand')
            if sg*(lc(e)[1]-lc(J['S'])[1])<3: bad.append(f'{k} elbow inside the shoulder line')
    for k in ('lf','rf'):
        r,kn,q=J[k]; u,v=r-kn,q-kn; ang=math.degrees(math.acos(np.clip(u@v/max(np.hypot(*u)*np.hypot(*v),1e-6),-1,1)))
        if ang<60: bad.append(f'{k} folded ({ang:.0f} deg)')
        if f>=7 and not (f<9 and k in stepping(f)):   # once both hips are over the ladder (to frame 8 the left foot is still stepping in onto the rung from the left)
            for s1 in segs[k]:
                for rail in (0,1):
                    for a_,b_ in zip(LAD[rail][:-1],LAD[rail][1:]):
                        if _x(*s1,a_,b_): bad.append(f'{k} crosses rail {rail}')
            if lc(kn)[1]<cL(lc(kn)[0]) or lc(kn)[1]>cR(lc(kn)[0]): bad.append(f'{k} knee outside the rails')
    if 9<=f<=27:   # from frame 28 his head clears the top of the rails, as the film man's does, so the hands are below it
        ha=lc(J['H'])[0]
        if max(lc(J['lh'][2])[0],lc(J['rh'][2])[0])<ha-6: bad.append('no hand at or above the head')
        if min(lc(J['lf'][2])[0],lc(J['rf'][2])[0])>lc(J['P'])[0]-8: bad.append('no foot on a rung below the waist')
    return bad
def stepping(f):
    # the hands and feet whose contact point moves between frame f-1 and frame f
    return {k for k,mv in MK['moves'].items() for f0,f1,q in mv if f0<=f<=f1}   # from the frame the limb unloads to the frame it is put down
def cont(f,J0,J1):
    # frame-to-frame check: the torso and the limb segments change length by at most a few % per frame, and every joint
    # moves at most ~8 px per frame, except the hand or foot that is stepping (and its elbow or knee, up to 14 px)
    bad=[]; st=stepping(f)
    LIM=9 if f>=10 else 25   # walking in and stepping onto the ladder (to frame 9) the film man moves 12-18 px a frame
    for k in ('H','N','P','S'):
        d=np.hypot(*(J1[k]-J0[k]))
        if d>LIM: bad.append(f'{k} moves {d:.1f}px')
    t0,t1=np.hypot(*(J0['N']-J0['P'])),np.hypot(*(J1['N']-J1['P']))
    if abs(t1/t0-1)>0.04: bad.append(f'torso length {t0:.1f}->{t1:.1f}')
    for k in ('lh','rh','lf','rf'):
        for i,nm in enumerate(('root','mid','end')):
            d=np.hypot(*(J1[k][i]-J0[k][i])); lim=(LIM if f>=10 else 2*LIM) if k not in st else (LIM,LIM+6+0.6*np.hypot(*(J1[k][2]-J0[k][2])),99)[i]
            if d>lim: bad.append(f'{k} {nm} moves {d:.1f}px')
        for i in (0,1):
            a,b=np.hypot(*(J0[k][i]-J0[k][i+1])),np.hypot(*(J1[k][i]-J1[k][i+1]))
            # a bone is fixed in length; drawn foreshortened, it may lengthen or shorten only as much as the limb's
            # reach (shoulder or hip to hand or foot) changes in that frame, plus a few %
            dD=abs(np.hypot(*(J1[k][2]-J1[k][0]))-np.hypot(*(J0[k][2]-J0[k][0])))
            lim=0.05*a+0.6*dD if k not in st else 0.4*a+0.6*dD
            if abs(b-a)>lim: bad.append(f'{k} segment {i} {a:.1f}->{b:.1f}')
    return bad
def man(f):
    J=SKEL[f]; H=J['H']
    st=[]
    st+=hand([(H+SC(f)*np.array([7*math.cos(a),7.5*math.sin(a)])).tolist() for a in np.linspace(-0.4,2*math.pi-0.1,9)],wob=False)   # head: one loop, not quite closed
    st+=hand([J['N'],(J['lf'][0]+J['rf'][0])/2])   # body: one line, from the neck down to between the hips                                                                                         # body: one line
    for limb in ('lh','rh','lf','rf'): st+=hand(list(J[limb]))
    return [[[round(x-cam[f][0],1),round(y-cam[f][1],1)] for x,y in s] for s in st]
SKEL=[skeleton(f) for f in range(n)]   # once per frame, in order (the ground-phase joints remember their side)
BAD={f:check(f,SKEL[f])+(cont(f,SKEL[f-1],SKEL[f]) if f else []) for f in range(n)}
BAD={f:b for f,b in BAD.items() if b}
if BAD:
    for f,b in BAD.items(): print('frame',f,'; '.join(sorted(set(b))))
    if '--force' not in sys.argv: sys.exit('limb check failed; scene not written')
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
 "notes":{"0":"the ladder leans against the haystack; a man walks in from the left","4":"he reaches the ladder and takes the left rail with his right hand","6":"right foot on the bottom rung","8":"first push: he steps up, left foot on the second rung","16":"halfway up, one rung at a time, hand then foot","26":"a push brings his head level with the top of the ladder","32":"the last push brings him to the top of the ladder, feet on the top-but-one rung, hands on the tops of the rails","37":"he stays bent forward over the top of the ladder against the haystack, head inside the frame"},
 "no_cel":"the SAM mask covers the man in most frames, so cel paint would erase the man and leave the ladder alone"}
json.dump(S,open(R+'rigs/ladder_scene.json','w'),indent=1)
print(len(objs))
