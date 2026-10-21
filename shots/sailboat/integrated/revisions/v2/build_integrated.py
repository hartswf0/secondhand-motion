"""Source-matched four-stroke sailboat. Rebuild: --source clip.mp4 --mask-cache snapshot/.
No policy training, guessed sail flutter, or independently approved playback is implied.
"""
from pathlib import Path
import argparse,os,sys,io,json,math,hashlib,shutil,tempfile,subprocess
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=ROOT.parents[2]/'mia-quickdraw-dataset/videos/4c3c2e00-a804-5f5a-a743-66e58774123a.mp4'
CACHE=OUT/'sam';W,H=480,360;FPS=24;START,END=3.,9.;N=145;KEYS=[0,24,48,60,72,84,108,120,144]
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float) for s in D['drawing']]
# Pixel observations on exact 480x360 source keys. The fixed far-vessel pattern is a
# screen-space camera proxy; distant vessels are not asserted to be stationary in world space.
OBS=[]
VALUES=[
(3, [294,60],[264,195],[390,207],[333,42],[338,229],[273,221],[389,225],255,0,[266,237],21),
(3.5,[292,49],[263,195],[396,204],[332,34],[338,229],[275,222],[393,223],256,-12,[266,238],21),
(4,[289,40],[257,194],[402,205],[329,20],[335,229],[266,218],[398,222],257,-26,[255,242],23),
(4.5,[280,29],[244,194],[406,205],[323,7],[329,230],[257,218],[401,223],259,-47,[244,244],24),
(5,[273,18],[232,194],[406,206],[315,-9],[321,233],[246,221],[400,225],263,-72,[231,245],23),
(5.5,[257,5],[214,194],[403,205],[305,-26],[310,235],[225,221],[390,228],267,-112,[215,248],23),
(6,[234,-12],[187,193],[399,205],[292,-44],[294,238],[201,221],[379,230],270,-154,[196,252],25),
(6.5,[211,-32],[166,191],[397,204],[277,-72],[278,239],[182,220],[372,233],273,-191,[181,253],27),
(7,[210,-63],[150,191],[393,207],[278,-104],[279,242],[165,221],[367,235],276,-225,[162,253],29),
(7.5,[223,-96],[150,191],[434,208],[309,-156],[307,246],[167,221],[400,239],280,-237,[148,255],30),
(8,[237,-130],[158,191],[486,210],[349,-210],[346,253],[179,224],[452,247],284,-244,[137,257],32),
(8.5,[260,-180],[174,188],[544,216],[390,-276],[385,259],[195,226],[511,251],291,-246,[127,261],36),
(9,[281,-230],[195,191],[600,224],[447,-340],[438,267],[214,231],[570,255],298,-249,[119,266],43)]
for t,peak,left,right,masttop,mastbase,hullleft,hullright,keel,camx,dinghy,dw in VALUES:
 OBS.append(dict(t=t,sail_peak=peak,sail_left=left,sail_right=right,mast_top=masttop,mast_base=mastbase,hull_left=hullleft,hull_right=hullright,keel=keel,camera_x=camx,dinghy=dinghy,dinghy_width=dw))
INTERP={k:PchipInterpolator([o['t'] for o in OBS],[o[k] for o in OBS],axis=0) for k in OBS[0] if k!='t'}
NOTES=['Whole barge approaches with mast and gaff below the top edge.','Approach enlarges the sail and raises its peak.','Mast has crossed the upper crop; hull remains in view.','Camera begins its faster rightward follow; far vessels slide left.','Gaff sail head enters the upper crop; left foot continues left.','Top crop deepens while the near hull grows.','Camera follow settles; the near bow turns farther right.','The sail and bow reach the right crop.','Final retained moment: sail and bow cropped, trailing dinghy still visible.']
def points(a):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in a)
def line(a,w=1.7,color='#28251e',opacity=1):return f'<polyline points="{points(a)}" fill="none" stroke="{color}" stroke-width="{w}" opacity="{opacity}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,c='#fffdf7',opacity=1):return f'<polygon points="{points(a)}" fill="{c}" opacity="{opacity}"/>'
def hull_map(s,A):
 x=s[:,0];base=np.interp(x,[0,60,140,224,255],[132,128,137,102,97]);u=x/255
 left=A['hull_left'];right=A['hull_right'];top=left[1]+u*(right[1]-left[1]);bottom=A['keel']-2*(u-.5)**2
 v=(s[:,1]-base)/(193-base)
 return np.column_stack([left[0]+u*(right[0]-left[0]),top+v*(bottom-top)])
def geometry(t):
 A={k:np.asarray(v(t)) for k,v in INTERP.items()};M=cv2.getAffineTransform(np.float32([[116,2],[5,103],[123,118]]),np.float32([A['sail_peak'],A['sail_left'],A['sail_right']]))
 sail=np.c_[ST[2],np.ones(len(ST[2]))]@M.T
 # Bounded identity repair: the original doubled mast travels with the sail's
 # trailing edge, rather than cutting through the native sail. Its exact original
 # irregular x/y points share the same affine cage as the sail.
 pole=np.c_[ST[3],np.ones(len(ST[3]))]@M.T
 return [hull_map(ST[0],A),hull_map(ST[1],A),sail,pole],A
# One held distant-vessel plate. Each source-derived shape is drawn once and receives
# only the measured far-vessel translation. The native boat occludes this plate.
FAR=[[[44,219],[49,207],[59,207],[65,220],[44,219]],[[53,209],[53,194],[49,193]],[[97,216],[106,209],[131,209],[143,215],[97,216]],[[112,209],[112,194]],[[124,209],[124,189]],[[148,213],[154,208],[167,208],[169,213],[148,213]],[[159,208],[159,201]],[[281,211],[291,208],[309,209],[306,213],[281,211]],[[286,208],[298,180],[300,208]],[[328,212],[341,207],[362,208],[360,214],[328,212]],[[333,207],[348,173],[352,207]]]
WATER=[[[x,y],[x+10,y-1],[x+26,y],[x+40,y-1]]for y in [235,253,280,304,335,353]for x in range(-280,760,90)]
def dinghy(A):
 x,y=A['dinghy'];w=float(A['dinghy_width']);boat=np.array([[x-w*.5,y-5],[x-w*.35,y+4],[x+w*.35,y+5],[x+w*.5,y-4],[x+w*.2,y-2],[x-w*.5,y-5]])
 tow=[[x+w*.5,y-2],[x+w*.9,y-3],[float(A['hull_left'][0])-3,float(A['hull_left'][1])+8]]
 return poly(boat,'#e8e1d1')+line(boat,1.,'#6d685c')+line(tow,.8,'#8d8779')
def svg_for(t,character=False,mask=False):
 S,A=geometry(t);prefix=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
 if mask:return prefix+'<rect width="480" height="360" fill="#000"/>'+poly(S[2],'#fff')+poly(S[1],'#fff')+'</svg>',S,A
 if character:return prefix+'<rect width="480" height="360" fill="white"/>'+''.join(line(s)for s in S)+'</svg>',S,A
 scene='<rect x="-1000" y="-600" width="2400" height="1600" fill="#fffdf7"/>'
 scene+='<g transform="translate('+str(float(A['camera_x']))+' 0)">'+''.join(line(s,.85,'#aaa393')for s in WATER)+''.join(line(s,.95,'#938c7c')for s in FAR)+'</g>'
 # A reflected impression uses the same native strokes under held horizontal water gaps.
 reflection=[];water=float(A['keel'])
 for s in S[:3]:
  r=s.copy();r[:,1]=water+(water-r[:,1])*.34;reflection.append(line(r,.85,'#b2a892',.45))
 scene+='<defs><clipPath id="reflection">'+''.join(f'<rect x="0" y="{y}" width="480" height="2"/>'for y in range(round(water)+3,361,9))+'</clipPath></defs><g clip-path="url(#reflection)">'+''.join(reflection)+'</g>'
 scene+=dinghy(A)+poly(S[1],'#fffdf7')+poly(S[2],'#fffdf7')+''.join(line(s)for s in S)
 return prefix+scene+'</svg>',S,A

def trace_keys():
 sys.path.insert(0,str(ROOT.parents[1]/'tools'));import trace_keys as tracer
 keys=[]
 for k in range(1,len(KEYS)+1):
  p=OUT/f'character-key-{k:02d}.png';im=Image.open(p);st,ink,hw=tracer.trace(im);r,precision,parts=tracer.score(st,ink,*im.size,hw);keys.append(dict(key=k,file=p.name,strokes=st,recall=r,precision=precision,parts_kept=parts))
 (OUT/'traced.json').write_text(json.dumps({'sailboat':{'W':W,'H':H,'keys':keys}},indent=2)+'\n')
 return dict(min_recall=min(k['recall']for k in keys),min_parts_kept=min(k['parts_kept']for k in keys),keys=len(keys),pass_gate=all(k['recall']>=.98 and k['parts_kept']==1 for k in keys))
def main():
 assert SOURCE.is_file();src=json.loads((ROOT/'source.json').read_text()).get('source',{});sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest();src.update(interval_seconds=[START,END],time_basis='clip_relative_seconds',source_sha256=sha,source_kind='archive footage, sailing barge',sampled_continuity='The 16-frame retained sheet is one continuous approach; the source title and later cut are outside the retained 3–9 s interval.',motion_approved=False,train_eligible=False)
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n');cache=OUT/'sam';cache.mkdir(exist_ok=True)
 for name in ['track.json','clip.json']:
  if (CACHE/name).resolve()!=(cache/name).resolve():shutil.copy2(CACHE/name,cache/name)
 clip=json.loads((cache/'clip.json').read_text());track=json.loads((cache/'track.json').read_text())['frames']
 provenance=dict(branch='wave2-track/sailboat',commit='e9dd70601b9540492132b8e7906343bfba65070a',model='facebook/sam2.1-hiera-small',track_sha256=hashlib.sha256((cache/'track.json').read_bytes()).hexdigest(),source_sha256=sha,target_audit='Main sail and hull broadly selected in sampled frames1,24,48; sample72 omits left hull. Model estimates are separate from measured filled-rig intersection-over-union.',valid_for_object_fit='partial target; numeric fit is against observed SAM, not ground truth')
 (cache/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 if (OUT/'sam-audit.jpg').exists():shutil.copy2(OUT/'sam-audit.jpg',cache/'audit.jpg')
 cap=cv2.VideoCapture(str(SOURCE));sfps=cap.get(cv2.CAP_PROP_FPS);rawsize=[int(cap.get(3)),int(cap.get(4))];frames=[];fit=[];validation={}
 # Decode the retained interval once in source order; random seeking 4K footage for every render is unnecessary.
 source_images={};first_index=round(START*sfps);last_index=round(END*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,first_index)
 for source_index in range(first_index,last_index+1):
  ok,bgr=cap.read();assert ok;source_images[source_index]=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((W,H),Image.Resampling.LANCZOS)
 cap.release()
 with tempfile.TemporaryDirectory(prefix='secondhand-sailboat-')as td:
  temp=Path(td)
  for f in range(N):
   t=START+f/FPS;idx=round(t*sfps);sourceim=source_images[idx]
   svg,S,A=svg_for(t);cartoon=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB');sourceim.save(temp/f'source-{f:03d}.ppm');cartoon.save(temp/f'cartoon-{f:03d}.ppm')
   pair=Image.new('RGB',(W*2,H+24),'#f5f1e8');pair.paste(sourceim,(0,24));pair.paste(cartoon,(W,24));p=ImageDraw.Draw(pair);p.text((8,6),f'ARCHIVE | {t:.3f} s',fill='#171512');p.text((W+8,6),'NATIVE DOODLE | observed approach and crop',fill='#171512');pair.save(temp/f'pair-{f:03d}.ppm')
   ci=min(len(track)-1,max(0,round((t-clip['t0'])*clip['fps'])));q=track[ci];mask=np.repeat(np.arange(len(q['rle']))%2,q['rle']).reshape(q['H'],q['W']).astype(bool)
   sm=np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg_for(t,mask=True)[0].encode()))).convert('L').resize((q['W'],q['H']),Image.Resampling.NEAREST))>127
   union=(sm|mask).sum();fit.append(float((sm&mask).sum()/union)if union else 0.)
   frames.append(dict(f=f,time=f/FPS,source_time=t,source_frame_index=idx,source_index_time=idx/sfps,camera_x=float(A['camera_x']),anchors={k:v.tolist()for k,v in A.items()},cast=[dict(id='sailboat',source='QuickDraw key'+D['key_id'],strokes=[s.tolist()for s in S])]))
   if f in KEYS:
    k=KEYS.index(f)+1;sourceim.save(OUT/f'source-{k:02d}.jpg',quality=92);cartoon.save(OUT/f'key-{k:02d}.png');(OUT/f'key-{k:02d}.svg').write_text(svg);ch=svg_for(t,character=True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(ch);cairosvg.svg2png(bytestring=ch.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
   if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=92)
  cap.release()
  for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
   dst=temp/name;subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(temp/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(dst)],check=True)
   subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(dst),'-f','null','-'],check=True);probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(dst)]))['streams'][0];assert int(probe['nb_read_frames'])==N;os.replace(dst,OUT/name);validation[name]=dict(decoded_frames=N,fps=FPS,sha256=hashlib.sha256((OUT/name).read_bytes()).hexdigest())
 (OUT/'movie-validation.json').write_text(json.dumps(validation,indent=2)+'\n');shutil.copy2(ROOT/'design.json',OUT/'design.json');shutil.copy2(ROOT/'design.png',OUT/'design.png')
 (OUT/'background.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect x="-1000" y="-600" width="2400" height="1600" fill="#fffdf7"/>'+''.join(line(s,.85,'#aaa393')for s in WATER)+''.join(line(s,.95,'#938c7c')for s in FAR)+'</svg>')
 trace=trace_keys();fitrec=dict(method='Filled native sail and hull compared against the nearest 12 fps SAM sample at 145 rendered frames; excludes drawn dinghy/reflection/background.',mean=float(np.mean(fit)),minimum=float(min(fit)),mean_bar=.65,min_bar=.45,pass_gate=bool(np.mean(fit)>=.65 and min(fit)>=.45),frames=fit,target_caveat=provenance['target_audit'])
 (OUT/'mask-fit.json').write_text(json.dumps(fitrec,indent=2)+'\n');summary='One real four-stroke sailboat approaches under source-keyed sail, mast and hull anchors. A single distant-vessel plate follows measured screen drift; trailing dinghy is drawn by agent. No invented sail flutter.'
 shot=dict(title='Sailboat coming alongside',revision='integrated-v2',status='assembled_candidate_review_pending',W=W,H=H,fps=FPS,frame_count=N,duration=N/FPS,keys=KEYS,source=src,design=D,source_anchors=OBS,frames=frames,xsheet=[dict(f=f,kind='K'if f in KEYS else'B',note=NOTES[KEYS.index(f)]if f in KEYS else'PCHIP source anchors; same four native stroke/point correspondences.')for f in range(N)],planes=[dict(id='water_far_vessels',source='drawn once by agent from source, far-vessel translation proxy'),dict(id='main_sailboat',source='QuickDraw key'+D['key_id']),dict(id='dinghy',source='drawn by agent from source positions'),dict(id='reflection',source='same native strokes reflected through held water gaps; approximation')],camera=dict(method='Manually observed far-vessel screen drift, source-pose coordinates480×360. Does not disentangle moving distant ships from camera.',translation_x=[dict(t=o['t'],x=o['camera_x'])for o in OBS],overscan=True),mask_fit={k:v for k,v in fitrec.items()if k!='frames'},assembly_summary=summary,review_status='review_pending',review_note='Independent pose, doodle identity and normal-speed motion review pending.',training_ran=False,motion_approved=False,train_eligible=False)
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps(dict(original_strokes=4,original_point_counts=[len(s)for s in ST],mapping='Gunwale/hull use source hull cage, one native sail uses observed peak/foot affine cage, mast shares the native sail affine cage, retaining its trailing-edge attachment; no point or stroke is replaced.',source_anchors=OBS),indent=2)+'\n')
 checks=dict(rendered_frames=N,keys=len(KEYS),source_sha256=sha,raw_source_size=rawsize,raw_source_fps=sfps,original_strokes=4,same_topology=True,held_background_geometry=True,trace_fidelity=trace,mask_fit={k:v for k,v in fitrec.items()if k!='frames'},recognition='not run',normal_speed_playback='not run',independently_observed_planted_intervals=0,foot_slide_gate=False,release_approved=False,training_ran=False)
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(dict(frames=N,keys=len(KEYS),trace=trace,mask_fit=checks['mask_fit'])),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();SOURCE=a.source;CACHE=a.mask_cache;main()
