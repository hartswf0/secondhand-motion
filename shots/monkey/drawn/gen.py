import json, numpy as np, sys
M='/tmp/claude-0/-home-claude/20a96084-4ba3-520f-93b2-71a1fe6da80a/scratchpad/monkey'
D='/home/claude/cartoon-archive/shots/monkey/drawn/'
B=[np.array(s,float) for s in json.load(open(M+'/base.json'))['strokes']]
P=np.array([170.,185.])          # neck pivot
FC=np.array([160.,105.])         # face centre
K=json.load(open(M+'/keys.json'))
def rot(p,th,c):
    a=np.radians(th); R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]]); return (p-c)@R.T+c
def pose(sx,sy,th,t,d,g,bx=None,by=None,ear=None):
    S=[s.copy() for s in B]
    for i in (0,1,2,3):   # face mask, eyes, mouth slide to the near side and down
        S[i]=FC+(S[i]-FC)*[1-0.22*t,1-0.08*d]+[-24*t,20*d]
    for i in (1,2):
        ec=S[i].mean(0); S[i]=ec+(S[i]-ec)*[1,1-0.3*d]+[-g,4*d]
    S[3]=S[3]+[0,5*d]
    # head outline narrows a little in the turn
    c=S[4].mean(0); S[4]=c+(S[4]-c)*[1-0.06*t,1]
    # far ear (viewer's left) slides in behind the head and flattens
    e=ear if ear is not None else t
    lc=np.r_[S[5],S[8]].mean(0)
    for i in (5,8): S[i]=lc+(S[i]-lc)*[1-0.65*e,1-0.3*e]+[34*e,6*e]
    ic=S[8].mean(0); S[8]=ic+(S[8]-ic)*(1-0.55*e)+[-4*e,-3*e]
    # near ear (viewer's right) swings back a little
    for i in (6,7): S[i]=S[i]+[-14*t,4*t]
    for i in range(9): S[i]=rot(S[i],th,P)+[sx,sy]
    bx=0.4*sx if bx is None else bx; by=0.3*sy if by is None else by
    for i in (9,10,11): S[i]=S[i]+[bx,by]
    return S
for f,k in K.items():
    S=pose(*k['p'])
    out={'why':k['why'],'strokes':[[[round(x,1),round(y,1)] for x,y in s] for s in S],'extra':{}}
    json.dump(out,open(D+'k%03d.json'%int(f),'w'))
    # rig pose: crown and chin of the head carried by the same transform
    sx,sy,th,t=k['p'][:4]
    cr=rot(np.array([180.,34.]),th,P)+[sx,sy]; ch=rot(np.array([185.,171.]),th,P)+[sx,sy]
    k['rig']={'crown':cr.round(1).tolist(),'chin':ch.round(1).tolist(),'yaw':round(-0.8*t,2)}
json.dump({f:K[f]['rig'] for f in K},open('/home/claude/cartoon-archive/shots/monkey-sam/pose_agent_v4.json','w'),indent=1)
print('ok',sorted(map(int,K)))
