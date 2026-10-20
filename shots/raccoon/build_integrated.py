"""Source-framed raccoon assembly. Native QuickDraw paths share one keyed topology.
No model training; camera from sequential source optical flow, body/head keys authored against frames.
"""
from pathlib import Path
import json,math,hashlib,subprocess,os,random,shutil,argparse,tempfile
import xml.etree.ElementTree as ET
import cv2,numpy as np,cairosvg
from scipy.interpolate import PchipInterpolator
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=Path('/workspace/scratch/e78c43b4722d/wave2-logs/raccoon.mp4')
START=10.810810811;END=13.580246914;FPS=24;N=math.ceil((END-START)*FPS);KEYS=[0,6,13,22,33,44,55,66]
D=json.loads((ROOT/'design.json').read_text());ST=[list(zip(s[0],s[1])) for s in D['drawing']]
# screen coordinates in decoded 320x240 source frames. Width/height denote approximate observed hulls.
POSES=[
 [201,112,52,64,181,124,34,39,0.0], [200,114,54,62,179,127,36,38,.08],
 [197,115,57,62,171,128,38,36,.22], [184,118,65,61,150,133,40,35,.43],
 [213,118,84,69,167,131,43,41,.70], [243,121,105,70,185,128,42,43,.88],
 [244,122,107,70,185,128,42,43,.98], [244,122,107,70,184,128,42,43,1.0]]
INTERP=PchipInterpolator(KEYS,np.array(POSES),axis=0)
INK='#262820';PAPER='#fffdf6';WATER='#f2f1e3'
def pts(p):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in p)
def line(p,w=1.0,c=INK):return f'<polyline points="{pts(p)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def polygon(p,fill=PAPER):return f'<polygon points="{pts(p)}" fill="{fill}"/>'
# One seeded, held background drawing; camera translates it without changing its strokes.
rng=random.Random(617);BG=[];FG=[]
for i in range(75):
 x=rng.uniform(-100,330);y=rng.uniform(126,150);h=rng.uniform(40,150);lean=rng.uniform(-22,22)
 BG.append([[x,y],[x+lean*.35,y-h*.52],[x+lean,y-h]])
 if i%3==0:BG.append([[x+lean*.35,y-h*.52],[x+lean*.35-12,y-h*.52-8],[x+lean*.35-19,y-h*.52-22]])
for i in range(42):
 x=rng.uniform(-100,330);y=rng.uniform(150,236);r=rng.uniform(3,9)
 FG.append([[x-r,y],[x,y-2],[x+r,y],[x+1,y+1],[x-r,y]])
 if i%3==0:FG.append([[x,y+6],[x+2,y-10],[x+7,y-16]])
for x,y,h in [(62,240,81),(72,239,104),(42,213,45),(99,238,28),(145,181,38),(221,233,52)]:
 FG.append([[x,y],[x+1,y-h*.45],[x-2,y-h]])
 FG.append([[x+1,y-h*.45],[x-7,y-h*.62],[x-13,y-h*.66]])

def geometry(f):
 bx,by,bw,bh,hx,hy,hw,hh,yaw=map(float,INTERP(f))
 def body(s):return [[bx+(x-139.5)*bw/149-24*yaw*(1-y/68),by+(y-34)*bh/68] for x,y in s]
 def head(s,feature=False):
  return [[hx+(x-47.5)*hw/95+(5*(1-yaw) if feature else 0),hy+(y-37)*hh/54] for x,y in s]
 def tail(s):return [[bx+bw*.40+(x-201)*.25,by+bh*.62+(y-15)*.25] for x,y in s]
 parts={0:head(ST[0]),1:body(ST[1])}
 for i in range(2,7):parts[i]=tail(ST[i])
 for i in range(7,11):parts[i]=[[x,y+18] for x,y in body(ST[i])]
 for i in range(11,14):parts[i]=head(ST[i],True)
 return parts,dict(body_center=[bx,by],body_size=[bw,bh],head_center=[hx,hy],head_size=[hw,hh],head_turn=yaw,upper_body_shear=-24*yaw)

def svg_frame(f,cam):
 p,pose=geometry(f);dx,dy=cam;bx,by=pose['body_center'];hw,hh=pose['head_size'];hx,hy=pose['head_center'];yaw=pose['head_turn']
 bg=''.join(line(s,.65,'#85866c') for s in BG)
 fg=''.join(line(s,.8,'#6d735c') for s in FG)
 tail=''.join(line(p[i],1.05) for i in range(2,7));legs=''.join(line(p[i],1.1) for i in range(7,11))
 # Original features turn behind the head; the far eye is clipped progressively, not replaced.
 faceclip=[[hx-hw*.6,hy-hh*.6],[hx+hw*(.55-.67*yaw),hy-hh*.6],[hx+hw*(.55-.67*yaw),hy+hh*(.6-.43*yaw)],[hx-hw*.6,hy+hh*(.6-.43*yaw)]]
 body=polygon(p[1])+line(p[1],1.3);head=polygon(p[0])+line(p[0],1.35)
 features=''.join(line(p[i],1.1) for i in (11,12,13))
 # Water covers hidden feet and the lower tail; no invented stepping contacts are shown.
 wateredge=[[-100,149],[30,149],[70,148],[110,149],[140,147],[170,148],[205,149],[240,150],[300,148],[430,149],[430,260],[-100,260]]
 return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><defs><clipPath id="face">'+polygon(faceclip,'white')+'</clipPath></defs><rect width="320" height="240" fill="'+PAPER+'"/><g transform="translate('+str(dx)+' '+str(dy)+')">'+bg+'</g>'+tail+legs+body+head+'<g clip-path="url(#face)">'+features+'</g>'+polygon(wateredge,WATER)+'<g transform="translate('+str(dx)+' '+str(dy)+')">'+fg+'</g></svg>',pose,p

def camera_track(cap,srcfps):
 first=round(START*srcfps);last=round((START+(N-1)/FPS)*srcfps);cap.set(cv2.CAP_PROP_POS_FRAMES,first);ok,a=cap.read();assert ok;a=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY);track={first:[0.,0.]};counts={first:0};cam=np.zeros(2)
 for ix in range(first+1,last+1):
  ok,b=cap.read();assert ok;b=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY);mask=np.zeros(a.shape,np.uint8);mask[5:70,10:310]=255;mask[70:160,10:135]=255
  p=cv2.goodFeaturesToTrack(a,200,.02,5,mask=mask);q,st,e=cv2.calcOpticalFlowPyrLK(a,b,p,None,winSize=(21,21),maxLevel=3);g=st.ravel().astype(bool)
  delta=(q[g]-p[g]).reshape(-1,2);med=np.median(delta,axis=0);cam+=med;track[ix]=cam.tolist();counts[ix]=int(sum(g));a=b
 return track,counts

def character_export(svg,k):
 tree=ET.fromstring(svg)
 for c in list(tree):
  if c.tag.endswith('g') and 'transform' in c.attrib:tree.remove(c)
  elif c.tag.endswith('polygon') and c.attrib.get('fill')==WATER:c.set('fill',PAPER)
 char=ET.tostring(tree);(OUT/f'character-key-{k:02d}.svg').write_bytes(char);cairosvg.svg2png(bytestring=char,write_to=str(OUT/f'character-key-{k:02d}.png'))

def main():
 global SOURCE
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,default=SOURCE,help='Downloaded source clip matching source.json SHA256');args=parser.parse_args();SOURCE=args.source
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==json.loads((ROOT/'source.json').read_text())['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));srcfps=cap.get(cv2.CAP_PROP_FPS);camera,counts=camera_track(cap,srcfps)
 td=Path(tempfile.mkdtemp(prefix='sm-raccoon-render-'))
 frames=[];xs=[];allparts=[]
 for f in range(N):
  t=START+f/FPS;idx=round(t*srcfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  cam=camera[idx];svg,pose,parts=svg_frame(f,cam);p=td/f'cartoon-{f:03d}.png';cairosvg.svg2png(bytestring=svg.encode(),write_to=str(p));cart=Image.open(p).convert('RGB');source=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  cart.save(td/f'cartoon-{f:03d}.ppm');source.save(td/f'source-{f:03d}.ppm');pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(cart,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill=INK);pen.text((490,6),'ASSEMBLED CARTOON | same source instant',fill=INK);pair.save(td/f'pair-{f:03d}.ppm')
  frames.append(dict(f=f,time=f/FPS,source_time=t,source_frame_index=idx,source_index_time=idx/srcfps,camera_shift=cam,camera_tracked_features=counts[idx],pose=pose));allparts.append({'f':f,'strokes':parts})
  xs.append(dict(f=f,kind='K' if f in KEYS else 'B',note=['Head forward over the water, hindquarters foreshortened.','Muzzle drops toward the surface.','Head leads left; body begins to unfold.','Lowest muzzle during the leftward reach.','Camera catches the crouched turn; hindquarters stay low.','Side-on body settles while the head turns into bank vegetation.','Face partly hidden by the turn and bank.','Low foraging hold; legs and tail remain occluded.'][KEYS.index(f)] if f in KEYS else ''))
  if f in KEYS:
   k=KEYS.index(f)+1;cart.save(OUT/f'key-{k:02d}.png');source.save(OUT/f'source-{k:02d}.jpg',quality=90);(OUT/f'key-{k:02d}.svg').write_text(svg);character_export(svg,k)
  if f==0:cart.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=90)
 cap.release()
 for stem,out in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  temp_video=OUT/(out+'.rendering.mp4')
  subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-preset','slow','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp_video)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(temp_video),'-f','null','-'],check=True)
  os.replace(temp_video,OUT/out)
 shutil.copyfile(ROOT/'design.json',OUT/'design.json');shutil.copyfile(ROOT/'design.png',OUT/'design.png')
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="'+PAPER+'"/>'+''.join(line(s,.65,'#85866c') for s in BG)+'</svg>')
 data=dict(title='Raccoon at the waterline',revision='integrated-v3',status='assembled_candidate_review_pending',W=480,H=360,fps=FPS,frame_count=N,duration=N/FPS,keys=KEYS,source=json.loads((ROOT/'source.json').read_text()),design=D,frames=frames,xsheet=xs,assembly_summary='Eight source-matched crouching poses. One bank drawing follows measured camera translation; water and plants hide the unobserved legs and tail.',planes=[dict(id='bank',source='drawn by agent against source; single held geometry',strokes=BG),dict(id='tail',source_strokes=list(range(2,7))),dict(id='feet',source_strokes=list(range(7,11))),dict(id='body',source_strokes=[1]),dict(id='head',source_strokes=[0,11,12,13]),dict(id='foreground-water-and-reeds',source='drawn by agent for observed occlusion',strokes=FG)],source_registration=dict(method='manually observed screen-space head/body hulls at eight source frames; PCHIP between them',coordinates=[320,240],camera_method='Sequential LK background feature median deltas, excluding animal and water; not SAM or a segmentation measurement',camera_depth='one translational camera estimate, no depth estimate',unknown='hidden feet contacts, full tail shape, head yaw in 3D'),motion_approved=False,training_ran=False,train_eligible=False)
 if (OUT/'review-v3.json').exists():data.update(review_status='source_head_turn_repair_pending',review_note='Source head turn still needs repair; motion unapproved.',status='assembled_candidate_source_pose_repair_pending')
 (OUT/'shot.json').write_text(json.dumps(data,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps(dict(method='one original14-stroke topology; rigid part transforms, visibility by layered occlusion',key_id=D['key_id'],parts=dict(head=[0,11,12,13],body=[1],tail=list(range(2,7)),feet=list(range(7,11))),frames=allparts))+'\n')
 checks=dict(every_frame_rendered=N,source_sha256_verified=True,original_stroke_count=len(ST),all_original_strokes_assigned=True,held_background_geometry=True,integrated_keys=len(KEYS),SAM='not run',recognition='not run',numeric_source_mask_fit='not measured',planted_feet='unobserved behind water; no contact test passed',independent_playback='not run',release_approved=False,training_ran=False)
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(dict(frames=N,keys=len(KEYS),output=str(OUT))))
if __name__=='__main__':main()
