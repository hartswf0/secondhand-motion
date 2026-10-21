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
    return b
HEAD,WAIST=series('head'),series('waist')
LAD=[np.array(q,float) for q in json.load(open(R+'shots/ladder-gwp/shot.json'))['cast']['frames'][0]]   # the ladder doodle as placed (it does not move)
def snap(q,lim=9):
    # a hand or foot put on the ladder lands on the nearest drawn rail or rung, if one is close
    best,bd=q,lim
    for s in LAD:
        for a,b in zip(s[:-1],s[1:]):
            d=b-a; t=np.clip(np.dot(q-a,d)/max(np.dot(d,d),1e-9),0,1); c=a+d*t; dd=np.hypot(*(q-c))
            if dd<bd: best,bd=c,dd
    return best
def contact(f,limb):
    p=np.array(MK['start'][limb],float)
    for f0,f1,q in MK['moves'][limb]:
        q=snap(np.array(q,float))
        if f>=f1: p=q; continue
        if f>f0:
            t=(f-f0)/(f1-f0); t=t*t*(3-2*t); lift=math.sin(math.pi*t)*5
            d=q-p; nd=np.array([d[1],-d[0]])/max(np.hypot(*d),1e-6)   # the limb swings out from the ladder a little on the way
            return p+d*t+nd*lift*(1 if nd[0]<0 else -1)
        break
    return p
def joint(p,q,L,prefer):
    d=q-p; D=np.hypot(*d)
    if D>=2*L-0.5: return (p+q)/2
    h=math.sqrt(L*L-(D/2)**2); m=(p+q)/2; nrm=np.array([-d[1],d[0]])/D
    a,b=m+nrm*h,m-nrm*h
    return a if prefer(a)>=prefer(b) else b
def man(f):
    H,P=HEAD[f],WAIST[f]
    ax=(P-H)/np.hypot(*(P-H)); N=H+ax*9; pr=np.array([-ax[1],ax[0]])
    st=[]
    st.append([(H+np.array([7*math.cos(a),7.5*math.sin(a)])).tolist() for a in np.linspace(-0.4,2*math.pi-0.1,9)])   # head: one loop, not quite closed
    st.append([N.tolist(),P.tolist()])                                                                                    # body
    S=N+ax*3; arms=[]; legs=[]
    for limb in ('lh','rh'):
        q=contact(f,limb); e=joint(S,q,24,lambda z: z[1]); arms.append([S.tolist(),e.tolist(),q.tolist()])
    for limb in ('lf','rf'):
        q=contact(f,limb); k=joint(P,q,44,lambda z: z[0]); legs.append([P.tolist(),k.tolist(),q.tolist()])
    th=np.mean([np.array(l[1])-P for l in legs],0); th/=max(np.hypot(*th),1e-6)   # the wrap hangs over the thighs, sagging behind
    dn=0.55*th+0.45*np.array([-0.25,1.0]); dn/=np.hypot(*dn); side=np.array([-dn[1],dn[0]])
    st.append([(P+side*5).tolist(),(P+side*15+dn*30).tolist(),(P-side*14+dn*30).tolist(),(P-side*5).tolist(),(P+side*5).tolist()])        # the white wrap, closed
    st+=arms+legs
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
 "notes":{"0":"the ladder leans against the haystack; a man walks in from the left","4":"he reaches the ladder and takes the left rail with his right hand","6":"right foot on the bottom rung","8":"first push: he steps up, left foot on the second rung","16":"halfway up, one rung at a time, hand then foot","26":"a push brings his head level with the top of the ladder","32":"the last push lifts him over the top of the ladder onto the haystack","37":"he is on the haystack above the ladder"},
 "no_cel":"the SAM mask covers the man in most frames, so cel paint would erase the man and leave the ladder alone"}
json.dump(S,open(R+'rigs/ladder_scene.json','w'),indent=1)
print(len(objs))
