"""Assemble the archived storm surge, not a rotating cyclone.

python shots/hurricane/build_integrated.py --source /path/to/hurricane.mp4
The source movie hash is verified. --mask-cache supplies the pinned upstream SAM audit.
"""
from pathlib import Path
import argparse, hashlib, json, math, os, shutil, subprocess, tempfile
import cv2, numpy as np, cairosvg
from PIL import Image, ImageDraw
from scipy.interpolate import PchipInterpolator
from scipy.signal import savgol_filter

cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'integrated'
SOURCE=Path(os.environ.get('SECONDHAND_MOTION_SOURCE',str(ROOT.parents[2]/'wave2-logs/hurricane.mp4')))
CACHE=ROOT.parents[2]/'wave2-track-cache/hurricane'
START=31.1311311311; END=34.2008675342; FPS=24; N=math.ceil((END-START)*FPS)
D=json.loads((ROOT/'design.json').read_text()); ST=[np.array(list(zip(*s)),dtype=float) for s in D['drawing']]
TIMES=np.array([31.131131,31.365,31.899,32.399,32.9,33.1665,33.7,34.200868])
X=np.array([0,40,80,120,160,200,240,280,320],float)
# Visible upper foam edge, authored against eight decoded source samples (320x240).
CRESTS=np.array([[160,151,126,144,156,157,165,169,173],
 [164,156,140,154,164,161,165,169,171],
 [169,166,163,165,164,165,166,170,170],
 [171,170,166,169,167,170,169,171,172],
 [172,169,168,166,168,170,171,171,173],
 [173,171,168,168,169,171,170,173,173],
 [174,169,171,168,172,173,174,174,174],
 [174,172,172,170,172,173,174,174,175]],float)
CREST=PchipInterpolator(TIMES,CRESTS,axis=0)
ROOF=[[-100,88],[261,77],[278,95],[354,111],[354,120],[-100,121]]
WALL=[[74,119],[280,116],[280,170],[74,162],[74,119]]
SIDE=[[280,116],[314,123],[314,174],[280,170],[280,116]]
BG=[[[75,120],[75,163]],[[111,119],[111,154],[135,155],[135,119]],
 [[177,118],[177,155],[201,156],[201,117]],[[236,117],[236,157],[258,158],[258,117]],
 [[115,150],[133,151]],[[181,151],[199,151]],[[240,152],[256,153]],
 [[0,125],[74,122]],[[0,145],[74,146]],[[9,132],[30,132]],[[43,136],[65,136]],
 [[284,125],[308,130]],[[284,155],[309,160]],[[261,78],[279,113]],
 [[-100,115],[75,113],[280,111],[350,119]]]
KEYS=[0,6,18,30,42,49,62,N-1]
NOTES=['Early foam crest strikes the left/front wall.', 'Left impact collapses and spreads lower.',
 'Broad low foreground ridge; doors reappear.', 'Water drops to a flatter band against the building.',
 'Quieter foam exposes the fixed door bottoms.', 'Low wash continues with shallow foreground folds.',
 'Water washes across the lower right facade.', 'Low receding wash; no cyclone rotation is visible.']

def pts(a): return ' '.join(f'{float(x):.3f},{float(y):.3f}' for x,y in a)
def line(a,w=1.1,color='#25211c'):return f'<polyline points="{pts(a)}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
def polygon(a,fill):return f'<polygon points="{pts(a)}" fill="{fill}"/>'
def geometry(t,texture,camera=(0,0)):
 crest=CREST(t)
 local=X-camera[0];front=(local>=74)&(local<=314)
 base=np.interp(local,[74,280,314],[162,170,174])+camera[1]-1.5
 crest[front]=np.minimum(crest[front],base[front])
 glyph=[]
 for s in ST:
  x=s[:,0]/255*320
  # A limited source-derived foam-texture drift. This is not particle identity.
  x=x+texture[0]*(s[:,1]/80)
  front=np.interp(x,X,crest)
  y=front+(s[:,1]/80)**1.08*(237-front)+texture[1]*(s[:,1]/80)*.22
  glyph.append(np.column_stack([x,y]))
 return crest,glyph

def svg_for(t,camera=(0,0),texture=(0,0),character=False):
 crest,glyph=geometry(t,texture,camera)
 prefix='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'
 if character:return prefix+'<rect width="320" height="240" fill="#fffdf7"/>'+''.join(line(s,1.12) for s in glyph)+'</svg>',glyph
 bg=polygon(WALL,'#e7e2d7')+polygon(SIDE,'#d8d2c5')+polygon(ROOF,'#d4cec1')+line(ROOF,.9)+''.join(line(s,.8,'#696257') for s in BG)
 edge=np.column_stack([X,crest]);water=np.vstack([edge,[[320,260],[-20,260],[-20,crest[0]]]])
 # One source-keyed water boundary supplies the occluding near plane.
 return prefix+'<rect width="320" height="240" fill="#f1ede3"/>'+f'<g transform="translate({camera[0]:.4f} {camera[1]:.4f})">'+bg+'</g>'+polygon(water,'#fffdf7')+line(edge,.8,'#6b655b')+''.join(line(s,1.12) for s in glyph)+'</svg>',glyph

def render():
 OUT.mkdir(exist_ok=True)
 src=json.loads((ROOT/'source.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==src['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));srcfps=cap.get(cv2.CAP_PROP_FPS);raw=[];indices=[]
 for f in range(N):
  idx=round((START+f/FPS)*srcfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  raw.append(bgr);indices.append(idx)
 cap.release()
 grayref=cv2.cvtColor(raw[0],cv2.COLOR_BGR2GRAY);valid=np.zeros(grayref.shape,np.uint8);valid[75:141,74:316]=255
 features=cv2.goodFeaturesToTrack(grayref,maxCorners=120,qualityLevel=.012,minDistance=6,mask=valid)
 roof_template=grayref[70:130,15:285]
 cams=[];camera_samples=[];flow=[];acc=np.zeros(2)
 for i,bgr in enumerate(raw):
  gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY);q,ok,err=cv2.calcOpticalFlowPyrLK(grayref,gray,features,None)
  back,backok,_=cv2.calcOpticalFlowPyrLK(gray,grayref,q,None);keep=ok.ravel().astype(bool)&backok.ravel().astype(bool)&(np.linalg.norm(back-features,axis=2).ravel()<1.5)&(err.ravel()<25)
  lk=np.median((q-features).reshape(-1,2)[keep],axis=0) if keep.sum()>=5 else np.zeros(2)
  match=cv2.matchTemplate(gray[55:145,:],roof_template,cv2.TM_CCOEFF_NORMED);_,ncc,_,position=cv2.minMaxLoc(match)
  shift=np.array(position)-[15,15] if ncc>.8 else lk
  cams.append(shift);camera_samples.append(dict(f=i,tracked_points=int(keep.sum()),lk_translation=lk.tolist(),roof_template_ncc=float(ncc),raw_translation=np.asarray(shift).tolist(),method='roof template' if ncc>.8 else 'LK fallback'))
  if i:
   prev=cv2.cvtColor(raw[i-1],cv2.COLOR_BGR2GRAY);v=cv2.calcOpticalFlowFarneback(prev,gray,None,.5,3,15,3,5,1.2,0)
   delta=np.median(v[181:233,5:315].reshape(-1,2),axis=0);acc+=delta
  flow.append(acc.copy())
 cams=savgol_filter(np.array(cams),7,2,axis=0);flow=np.clip(np.array(flow)-cams,[-5,-5],[5,5])
 td=Path(tempfile.mkdtemp(prefix='secondhand-motion-hurricane-'));frames=[]
 for f,bgr in enumerate(raw):
  t=START+f/FPS;svg,glyph=svg_for(t,cams[f],flow[f]);cairosvg.svg2png(bytestring=svg.encode(),write_to=str(td/'frame.png'))
  cartoon=Image.open(td/'frame.png').convert('RGB');source=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  cartoon.save(td/f'cartoon-{f:03d}.ppm');source.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | storm surge, not a cyclone',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
  frames.append(dict(f=f,time=f/FPS,source_time=t,source_frame_index=indices[f],source_index_time=indices[f]/srcfps,camera_translation=cams[f].tolist(),foam_texture_drift=flow[f].tolist(),cast=[dict(id='foam_glyph',plane='near_water',strokes=[v.tolist() for v in glyph])]))
  if f in KEYS:
   k=KEYS.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');source.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg)
   charsvg,_=svg_for(t,cams[f],flow[f],True);(OUT/f'character-key-{k:02d}.svg').write_text(charsvg);cairosvg.svg2png(bytestring=charsvg.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
  if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 validation={}
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  temp=OUT/(name+'.tmp.mp4');subprocess.run(['ffmpeg','-v','error','-y','-threads','1','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(temp),'-f','null','-'],check=True);temp.replace(OUT/name);validation[name]=dict(decoded_frames=N,fps=FPS,complete=True)
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 for name in ['design.json','design.png']:shutil.copy(ROOT/name,OUT/name)
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240">'+polygon(WALL,'#e7e2d7')+polygon(SIDE,'#d8d2c5')+polygon(ROOF,'#d4cec1')+line(ROOF,.9)+''.join(line(s,.8,'#696257') for s in BG)+'</svg>')
 sm=OUT/'sam';sm.mkdir(exist_ok=True)
 for name in ['clip.json','track.json']:shutil.copy(CACHE/name,sm/name)
 prov=dict(model='facebook/sam2.1-hiera-small',detector='IDEA-Research/grounding-dino-tiny',branch='wave2-track/hurricane',commit='2dc19de1e1d56b643cb8f0c5c4d7ac9823e4bcb8',track_sha256=hashlib.sha256((sm/'track.json').read_bytes()).hexdigest(),assessment='Invalid temporal water instance: final mask switches to building. No single-object mask-fit claim.')
 (sm/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 (OUT/'camera.json').write_text(json.dumps(dict(method='roof/eave template NCC translation per source frame; LK cross-check; seven-sample Savitzky-Golay smoothing',features=len(features),roof_reference=[15,70,285,130],roof_search=[0,55,320,145],samples=camera_samples,smoothed=cams.tolist()),indent=2)+'\n')
 (OUT/'correspondence.json').write_text(json.dumps(dict(original_stroke_count=7,original_strokes=list(range(7)),crest_times=TIMES.tolist(),crest_x=X.tolist(),crest_y=CRESTS.tolist(),mapping='native y proportion maps into observed upper-foam-to-foreground envelope; original point/stroke order retained',texture_drift='bounded cumulative median Farneback flow in lower water, camera-subtracted; not physical particle correspondence'),indent=2)+'\n')
 shot=dict(title='Storm surge at the building',category='hurricane',visible_event='storm surf/flooding; no visible cyclone rotation',status='assembled_candidate_review_pending',revision='integrated-v3',W=480,H=360,fps=FPS,frame_count=N,duration=N/FPS,keys=KEYS,source=src,design=D,frames=frames,viewbox=dict(W=320,H=240),xsheet=[dict(f=f,kind='K' if f in KEYS else 'I',note=NOTES[KEYS.index(f)] if f in KEYS else 'Source-timed PCHIP water envelope; roof-derived camera translation.') for f in range(N)],planes=[dict(id='building',source='drawn once by agent against source frame',strokes=BG,roof=ROOF,wall=WALL,side=SIDE),dict(id='near_water',source='agent-authored occluding water edge from source samples; late edge maintains contact with building base'),dict(id='foam_glyph',source='QuickDraw4791481996935168, all seven original strokes')],camera=dict(method='roof/eave template NCC translation; LK cross-check',scope='global image translation only, not recovered3D'),source_segmentation=prov,assembly_summary='Early surf strikes the fixed building, collapses, and settles into a low wash. Seven original hurricane-doodle strokes form the water abstraction; the archive shows storm surge, not a visible rotating cyclone.',review_note='Independent source-event, identity and normal-speed playback review pending.',training_ran=False,motion_approved=False,train_eligible=False)
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n')
 checks=dict(rendered_frames=N,keys=len(KEYS),source_sha256_verified=True,original_strokes_assigned=7,same_topology=True,held_building_geometry=True,camera_track_min_points=min(s['tracked_points'] for s in camera_samples),SAM='ran upstream; target switches to building, invalid as persistent water instance',mask_fit='not measured: diffuse water and invalid target switching',recognition='not run',planted_contacts_observed=0,foot_slide_gate=False,independent_playback='not run',release_approved=False,training_ran=False)
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(dict(out=str(OUT),frames=N,keys=len(KEYS),camera_min_points=checks['camera_track_min_points'])))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();SOURCE=a.source;CACHE=a.mask_cache;render()
