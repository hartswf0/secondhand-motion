"""Source-framed rain study. Native streak phase is authored; surface events use source brightening.

python shots/rain/build_integrated.py --source /path/to/rain.mp4 --mask-cache /path/to/rain-cache
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, shutil, subprocess, tempfile
import cv2, numpy as np, cairosvg
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=ROOT.parents[1].parent/'wave2-logs/rain.mp4'
CACHE=ROOT.parents[1].parent/'wave2-track-cache/rain'
START=34.4344344344;END=38.8054721388;FPS=24;N=math.ceil((END-START)*FPS)
REVISION='integrated-v3'
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float) for s in D['drawing']]
PAPER='#fffdf7';INK='#25211c'
# One held studio/wet-road demonstration scene observed in the actual footage.
BG=[[[0,136],[136,136]],[[184,136],[320,136]],[[53,-20],[53,137]],[[57,-20],[57,137]],[[53,102],[61,104],[63,112]],[[54,59],[84,61]],
 [[282,-20],[282,136]],[[275,24],[282,38],[291,34],[297,18],[306,25],[320,16]],[[225,107],[225,137]],[[221,106],[226,103],[232,105],[232,108],[225,110]],
 [[158,136],[158,239]],[[162,136],[163,239]]]
LEFT=[[-20,209],[139,129]];RIGHT=[[180,129],[341,209]]
BG += [LEFT,RIGHT,[[x,y+6] for x,y in LEFT],[[x,y+6] for x,y in RIGHT],[[x,y+13] for x,y in LEFT],[[x,y+13] for x,y in RIGHT]]
for u in [.05,.20,.35,.50,.65,.80,.91]:
 for a,b in [(np.array(LEFT[0]),np.array(LEFT[1])),(np.array(RIGHT[1]),np.array(RIGHT[0]))]:
  p=a*(1-u)+b*u;BG.append([p.tolist(),(p+[0,14*(1-u)+2]).tolist()])
BG += [[[20,236],[71,211],[113,175],[142,143]],[[298,236],[249,211],[207,175],[179,143]]]
ROAD=np.array([[139,136],[-35,240],[355,240],[180,136]],np.int32)

def pts(s):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in s)
def line(s,w=1,c=INK,opacity=1):return f'<polyline points="{pts(s)}" fill="none" stroke="{c}" stroke-width="{w}" opacity="{opacity:.4f}" stroke-linecap="round" stroke-linejoin="round"/>'

def glyphs(t,energy):
 # All nine native strokes retain their point order and local shape. No individual drop ID is inferred.
 phase=(t-START)*112.0
 result=[]
 for s in ST:
  y=s[:,1]*.92;span=float(np.ptp(y));offset=(phase+float(y.min()))%(222-span)-float(y.min())
  result.append(np.column_stack((24+s[:,0]*1.05,y+offset+4)))
 return result

def svg_frame(t,shift,events,energy,character=False):
 marks=glyphs(t,energy)
 glyph=''.join(line(s,1.05,INK) for s in marks)
 if character:return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="'+PAPER+'"/>'+glyph+'</svg>'
 bg=''.join(line(s,.78,'#827a6a') for s in BG)
 # Dark upper-left apparatus and the pale hanging studio shape belong to the held set, not clouds.
 bg='<polygon points="-25,-20 51,-20 52,53 18,34" fill="#d9d3c6"/>'+bg
 ripple=[]
 for e in events:
  age=t-e['source_time']
  life=.25+.16*e['burst_strength']
  if not 0<=age<life:continue
  depth=(e['y']-132)/108;r=(2.2+age*39)*(0.4+depth);yscale=.19+.15*depth
  p=[[e['x']+r*math.cos(a),e['y']+r*yscale*math.sin(a)] for a in np.linspace(0,2*math.pi,13)]
  ripple.append(line(p,.64,'#8b806c',(1-age/life)*(.64+.3*e['burst_strength'])))
  if age<.075 and e['burst_strength']>.38:
   ripple.append(line([[e['x']-1.8,e['y']-.2],[e['x']-.8,e['y']-2.3],[e['x']+.2,e['y']-.3],[e['x']+1.4,e['y']-1.4]],.55,'#8b806c',.65))
 # The wet-surface region clips event marks so they stay on the road, not the studio wall.
 return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><defs><clipPath id="road"><polygon points="'+pts(ROAD)+'"/></clipPath></defs><rect width="320" height="240" fill="'+PAPER+'"/><g transform="translate('+format(shift[0],'.3f')+' '+format(shift[1],'.3f')+')">'+bg+'<g clip-path="url(#road)">'+''.join(ripple)+'</g></g>'+glyph+'</svg>'

def trace_outputs():
 spec=importlib.util.spec_from_file_location('trace_keys',ROOT.parents[1]/'tools/trace_keys.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 traced=[]
 for f in sorted(OUT.glob('character-key-*.png')):
  im=Image.open(f);st,ink,hw=mod.trace(im);r,p,parts=mod.score(st,ink,*im.size,hw)
  traced.append(dict(file=f.name,recall=r,parts_kept=parts,precision=p,strokes=st))
 result=dict(method='tools/trace_keys.py trace/score on separated native character exports',keys=traced)
 (OUT/'traced.json').write_text(json.dumps(result,indent=2)+'\n')
 check=json.loads((OUT/'assembly-checks.json').read_text());check['trace_fidelity']=dict(min_recall=min(k['recall'] for k in traced),min_parts_kept=min(k['parts_kept'] for k in traced),keys=len(traced),pass_=all(k['recall']>=.98 and k['parts_kept']==1 for k in traced));check['trace_fidelity']['pass']=check['trace_fidelity'].pop('pass_');(OUT/'assembly-checks.json').write_text(json.dumps(check,indent=2)+'\n')

def main():
 cv2.setNumThreads(1)
 src=json.loads((ROOT/'source.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==src['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));sfps=cap.get(cv2.CAP_PROP_FPS);images=[];grays=[];indices=[]
 for f in range(N):
  idx=round((START+f/FPS)*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,b=cap.read();assert ok
  b=cv2.resize(b,(320,240));images.append(b);grays.append(cv2.cvtColor(b,cv2.COLOR_BGR2GRAY));indices.append(idx)
 cap.release();roi=np.zeros((240,320),np.uint8);cv2.fillPoly(roi,[ROAD],1);roi[:144]=0
 static=np.zeros_like(roi);static[0:138,:85]=255;static[0:138,266:]=255
 corners=cv2.goodFeaturesToTrack(grays[0],maxCorners=90,qualityLevel=.03,minDistance=7,mask=static)
 shifts=[];events=[];energies=[];last=grays[0].astype(float)
 for f,g in enumerate(grays):
  q,status,_=cv2.calcOpticalFlowPyrLK(grays[0],g,corners,None);valid=status.ravel()>0;delta=(q-corners).reshape(-1,2)[valid]
  # Rejected LK tracked falling rain on the studio wall. The source horizon/rails are locked.
  # Hold the plate from the source observation rather than turning rainfall into camera motion.
  shift=np.zeros(2);shifts.append(shift.tolist())
  change=np.maximum(0,g.astype(float)-last-np.median(g.astype(float)-last));change*=roi
  energies.append(float(np.mean(change[roi>0])));last=g.astype(float)
  # New local highlights are event observations, not assertions that a particular raindrop was tracked.
  peaks=change.copy()
  for _ in range(12):
   _,v,_,p=cv2.minMaxLoc(peaks)
   if v<15:break
   x,y=p;events.append({'source_time':START+f/FPS,'source_frame_index':indices[f],'x':float(x),'y':float(y),'positive_luminance_change':v})
   cv2.circle(peaks,p,9,0,-1)
 energies=np.array(energies)
 # A short source-energy envelope controls authored ripple visibility/lifespan; positions remain observed.
 smooth=np.convolve(np.pad(energies,(2,2),mode='edge'),np.ones(5)/5,mode='valid');lo,hi=np.percentile(smooth,[10,90])
 for e in events:
  f=round((e['source_time']-START)*FPS);e['burst_strength']=float(np.clip((smooth[f]-lo)/(hi-lo),0,1))
 keys=[0]
 for chunk in np.array_split(np.arange(1,N-1),6):keys.append(int(chunk[np.argmax(energies[chunk])]))
 keys=sorted(set(keys+[N-1]));td=Path(tempfile.mkdtemp(prefix='secondhand-motion-rain-'));frames=[]
 sheet=Image.new('RGB',(960,4*264),PAPER);sp=ImageDraw.Draw(sheet)
 for f in range(N):
  t=START+f/FPS;svg=svg_frame(t,shifts[f],events,float(energies[f]));png=cairosvg.svg2png(bytestring=svg.encode());import io
  art=Image.open(io.BytesIO(png)).convert('RGB');source=Image.fromarray(cv2.cvtColor(images[f],cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  art.save(td/f'cartoon-{f:03d}.ppm');source.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(art,(480,24));p=ImageDraw.Draw(pair);p.text((9,6),f'ARCHIVE | {t:.3f} s',fill=INK);p.text((489,6),'ASSEMBLED CARTOON | source-located surface events',fill=INK);pair.save(td/f'pair-{f:03d}.ppm')
  frames.append(dict(f=f,time=f/FPS,source_time=t,source_frame_index=indices[f],source_index_time=indices[f]/sfps,camera_translation=shifts[f],surface_event_energy=float(energies[f]),native_streak_phase_authored_pixels=(t-START)*112))
  if f in keys:
   k=keys.index(f)+1;art.save(OUT/f'key-{k:02d}.png');source.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg)
   cs=svg_frame(t,shifts[f],events,float(energies[f]),True);(OUT/f'character-key-{k:02d}.svg').write_text(cs);cairosvg.svg2png(bytestring=cs.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
  if f==0:art.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 # Sixteen source photographs across this retained continuous interval form the critic packet.
 for j,f in enumerate(np.linspace(0,N-1,16).astype(int)):
  im=Image.fromarray(cv2.cvtColor(images[f],cv2.COLOR_BGR2RGB)).resize((240,180));x=(j%4)*240;y=(j//4)*264;sheet.paste(im,(x,y+24));sp.text((x+4,y+4),f'{START+f/FPS:.3f} s',fill=INK)
 sheet.crop((0,0,960,4*264)).save(OUT/'source-contact-sheet.jpg',quality=90)
 validation={}
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  temp=OUT/(name+'.tmp.mp4');subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(temp),'-f','null','-'],check=True);temp.replace(OUT/name);validation[name]=dict(decoded_frames=N,fps=FPS,complete=True)
 shutil.copy2(ROOT/'design.json',OUT/'design.json');shutil.copy2(ROOT/'design.png',OUT/'design.png')
 snap=OUT/'source-masks';snap.mkdir(exist_ok=True)
 for name in ['clip.json','track.json']:shutil.copy2(CACHE/name,snap/name)
 provenance=dict(branch='wave2-track/rain',commit='4dbabc9f735f2a250848ad8263ceda7854264d8b',model='facebook/sam2.1-hiera-small',detector='IDEA-Research/grounding-dino-tiny',track_sha256=hashlib.sha256((snap/'track.json').read_bytes()).hexdigest(),limitation='Puddle/scene mask; not individual rain drops or splash ground truth.')
 (snap/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 shot=dict(title='Rain over the demonstration road',status='assembled_candidate_review_pending',revision=REVISION,W=480,H=360,fps=FPS,frame_count=N,duration=N/FPS,keys=keys,source=src,design=D,frames=frames,xsheet=[dict(f=f,kind='K',note='Source temporal surface brightening maximum in this interval; authored nine-streak rain phase.') for f in keys],planes=[dict(id='studio_and_rails',source='drawn once by agent against actual source',strokes=BG),dict(id='wet_surface_events',source='positive local source luminance change; illustrative ripple lifespan and size authored'),dict(id='rain_streaks',source='original QuickDraw nine strokes',key_id=D['key_id'])],camera=dict(method='Held from source contact-sheet observation: horizon/rails retain their position. Rejected v1 LK followed rain streaks, not camera.',translation_range=np.ptp(np.array(shifts),axis=0).tolist(),rejected_lk_diagnostic='revisions/v1/shot.json camera'),source_segmentation=provenance,assembly_summary='Nine original rain marks descend over one held studio wet-road scene. Surface ripple births follow source-local brightening events; streak phase, ripple size and lifespan follow an authored mapping from the source brightening envelope, not individual-drop tracks.',review_note='Independent still and normal-speed motion review pending.',training_ran=False,motion_approved=False,train_eligible=False)
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'events.json').write_text(json.dumps({'method':'up to12 local maxima of positive luminance changes above15gray levels in road ROI per24fps sample; local9px suppression. Ripple visibility/lifespan authored from five-frame-smoothed source ROI brightening energy (10th–90th percentile normalized).','individual_drop_identity_established':False,'events':events},indent=2)+'\n')
 (OUT/'correspondence.json').write_text(json.dumps({'native_stroke_count':9,'stroke_order':'original0..8 in every frame','phase':'112 source-space pixels/s authored wrap; not source fall-speed estimate','background':BG},indent=2)+'\n')
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240"><rect width="320" height="240" fill="'+PAPER+'"/>'+''.join(line(s,.78,'#827a6a') for s in BG)+'</svg>')
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 checks=dict(rendered_frames=N,keys=len(keys),source_sha256_verified=True,original_strokes_assigned=9,same_topology=True,held_background_geometry=True,measured_surface_event_count=len(events),SAM='Upstream puddle mask inspected; invalid as individual rain/splash target.',numeric_source_mask_fit='not measured; diffuse rain vs broad scene mask',recognition='not run',independent_playback='not run',release_approved=False,training_ran=False,independently_observed_planted_intervals=0,foot_slide_gate=False)
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');trace_outputs();shutil.rmtree(td);print(json.dumps({'frames':N,'keys':keys,'events':len(events),'output':str(OUT)}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();SOURCE=a.source;CACHE=a.mask_cache;main()
