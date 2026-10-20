"""Measure the dragon shot: the camera's settle (similarity of the still body vs frame 10) and the head's
turn about the neck (similarity of the head region vs frame 10). Writes shots/dragon/work/measure.json."""
import cv2, numpy as np, math, json
D='shots/dragon-sam/frames/f%03d.jpg'
ref=cv2.imread(D%10,0); bf=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True)
def fit(maskbox, inv=False):
    m=np.zeros_like(ref)
    if inv: m[:]=255; m[40:210,40:180]=0
    else: x0,y0,x1,y1=maskbox; m[y0:y1,x0:x1]=255
    orb=cv2.ORB_create(3000,scaleFactor=1.1,edgeThreshold=8,patchSize=15); kr,dr=orb.detectAndCompute(ref,m); out=[]
    for f in range(32):
        im=cv2.imread(D%f,0); k,d=orb.detectAndCompute(im,None); mm=bf.match(dr,d)
        a=np.float32([kr[x.queryIdx].pt for x in mm]); b=np.float32([k[x.trainIdx].pt for x in mm])
        M,_=cv2.estimateAffinePartial2D(a,b,ransacReprojThreshold=2); out.append(M.tolist())
    return out
body=fit(None,inv=True); head=fit((50,50,170,200))
res=[]
for f in range(32):
    B=np.array(body[f]); H=np.array(head[f])
    # head turn relative to the body: H = B o Hrel  ->  Hrel = B^-1 H
    B3=np.vstack([B,[0,0,1]]); H3=np.vstack([H,[0,0,1]]); Rl=np.linalg.inv(B3)@H3
    res.append({'f':f,'cam':body[f],'head_deg':math.degrees(math.atan2(Rl[1,0],Rl[0,0])),'head_t':Rl[:2,2].tolist()})
json.dump(res,open('shots/dragon/work/measure.json','w'),indent=0)
for r in res: print(r['f'],np.round(np.array(r['cam']),3).tolist(),round(r['head_deg'],1),np.round(r['head_t'],1))
