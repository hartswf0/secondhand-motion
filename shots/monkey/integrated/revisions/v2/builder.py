"""Native Quick, Draw! monkey, observed head lowering/return; no trained motion model."""
from pathlib import Path
import argparse,hashlib,json,math,shutil,tempfile,subprocess,os,io,sys
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=ROOT.parents[2]/'mia-quickdraw-dataset/videos/0c93c28c-6d9b-53c2-8cc7-905df20ec940.mp4'
CACHE=OUT/'sam';START=1/3;END=3.5;FPS=24;N=77;KEYS=[0,10,16,22,27,36,46,56,63,69,76]
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float) for s in D['drawing']]
OBS=[
 dict(t=START,crown=[148,27],angle=13,width=.76,eyes=[[119,69],[150,69]],mouth=[132,117],ears=[[84,76],[201,51]]),
 dict(t=.75,crown=[136,25],angle=15,width=.74,eyes=[[95,73],[125,75]],mouth=[105,124],ears=[[69,77],[177,44]]),
 dict(t=1,crown=[120,26],angle=17,width=.71,eyes=[[76,75],[102,85]],mouth=[84,132],ears=[[49,83],[157,32]]),
 dict(t=1.25,crown=[101,29],angle=18,width=.69,eyes=[[56,78],[81,90]],mouth=[66,136],ears=[[36,84],[143,31]]),
 dict(t=1.458333333,crown=[99,27],angle=18,width=.69,eyes=[[54,77],[81,88]],mouth=[65,134],ears=[[34,80],[140,27]]),
 dict(t=1.833333333,crown=[97,24],angle=18,width=.69,eyes=[[53,76],[78,87]],mouth=[63,133],ears=[[31,81],[141,26]]),
 dict(t=2.25,crown=[97,25],angle=18,width=.69,eyes=[[54,78],[78,89]],mouth=[66,135],ears=[[30,82],[145,29]]),
 dict(t=2.666666667,crown=[99,26],angle=18,width=.70,eyes=[[55,78],[82,88]],mouth=[67,134],ears=[[33,82],[145,30]]),
 dict(t=2.958333333,crown=[120,24],angle=15,width=.73,eyes=[[82,78],[110,86]],mouth=[91,134],ears=[[55,79],[167,33]]),
 dict(t=3.208333333,crown=[136,23],angle=10,width=.76,eyes=[[110,75],[140,79]],mouth=[121,132],ears=[[75,80],[183,39]]),
 dict(t=3.5,crown=[151,26],angle=8,width=.78,eyes=[[120,72],[152,73]],mouth=[133,128],ears=[[84,82],[205,35]])]
I={k:PchipInterpolator([o['t']for o in OBS],[o[k]for o in OBS],axis=0)for k in OBS[0]if k!='t'}
NOTES=['Clean three-quarter head after the opening dissolve.','Eyes/head turn down-left; ear asymmetry grows.','Lowering continues; nose points left/down.','Low head position reached.','Head settles into the downward hold.','Low held pose; face remains down-left.','Small settling movement during the hold.','End of the low hold before the return.','Head begins lifting and rotating back.','Return toward the camera; eyes rise.','Head higher and nearer frontal before later action.']
EYE_NATIVE=[ST[1].mean(axis=0),ST[2].mean(axis=0)];MOUTH_NATIVE=ST[3].mean(axis=0)

def pts(a):return ' '.join(f'{x:.3f},{y:.3f}'for x,y in a)
def line(a,w=1.35,c='#29261f'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,c='#fffdf7'):return f'<polygon points="{pts(a)}" fill="{c}"/>'
def geometry(t):
 a={k:np.asarray(v(t))for k,v in I.items()};ang=math.radians(float(a['angle']));rot=np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang),math.cos(ang)]]);crown=a['crown'];ears=a['ears'];r=[]
 # All native facial construction shares the head-local transform after the blind v1 repair.
 bodycx=84+.45*(crown[0]-145)
 for i,s in enumerate(ST):
  if i in [0,1,2,3,4,6,7]:q=((s-[95,9])*[float(a['width']),.72])@rot.T+crown
  elif i in [5,8]:q=((s+[-25,46]-[95,9])*[float(a['width']),.72])@rot.T+crown
  elif i in [9,11]:
   xx=bodycx+(s[:,0]-95)*1.25-np.maximum(0,95-s[:,0])*.45;yy=220+(s[:,1]-210)*1.5;q=np.column_stack([xx,yy])
  elif i==10:
   # Tail belongs to the original drawing, but the actual source close-up does not show it.
   q=(s-[196,156])*[.8,.8]+[bodycx-80,310]
  r.append(q)
 return r,a
BG='<rect x="-80" y="-80" width="480" height="400" fill="#fffdf7"/><path d="M242 -20 L340 -20 L340 270 L261 270 L235 170 Z" fill="#f4f0e7"/><path d="M1 -20 L1 270" stroke="#c8bfad" stroke-width=".7"/>'
def svg_for(t,character=False,mask=False):
 s,a=geometry(t);prefix='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'
 if mask:return prefix+'<rect width="320" height="240" fill="#000"/>'+''.join(poly(s[i],'#fff')for i in [9,5,6,4])+'</svg>',s,a
 content='<rect width="320" height="240" fill="#fffdf7"/>'if character else BG
 content+=poly(s[9])+line(s[9])+line(s[11])+line(s[10])
 content+=poly(s[5])+poly(s[6])+''.join(line(s[i])for i in [5,6,7,8])
 content+=poly(s[4])+line(s[4])+''.join(line(s[i])for i in [0,1,2,3])
 return prefix+content+'</svg>',s,a
def raster(svg):return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB')
def trace():
 sys.path.insert(0,str(ROOT.parents[1]/'tools'));import trace_keys
 rows=[]
 for k in range(1,len(KEYS)+1):
  p=OUT/f'character-key-{k:02d}.png';im=Image.open(p);ss,ink,hw=trace_keys.trace(im);rec,pre,parts=trace_keys.score(ss,ink,*im.size,hw);rows.append(dict(key=k,file=p.name,strokes=ss,recall=rec,precision=pre,parts_kept=parts,n_strokes=len(ss)))
 (OUT/'traced.json').write_text(json.dumps({'monkey':{'W':480,'H':360,'keys':rows}},indent=2)+'\n')
 return dict(min_recall=min(x['recall']for x in rows),min_parts_kept=min(x['parts_kept']for x in rows),keys=len(rows),pass_=all(x['recall']>=.98 and x['parts_kept']==1 for x in rows))
def pair_boards():
 for start in range(1,len(KEYS)+1,6):
  stop=min(start+6,len(KEYS)+1);board=Image.new('RGB',(960,math.ceil((stop-start)/2)*204),'#fffaf0');pen=ImageDraw.Draw(board)
  for j,k in enumerate(range(start,stop)):
   x=(j%2)*480;y=(j//2)*204;pen.text((x+4,y+3),'SOURCE / DRAWING | KEY '+str(k),fill='#111')
   for off,stem,ext in [(0,'source','jpg'),(240,'key','png')]:board.paste(Image.open(OUT/f'{stem}-{k:02d}.{ext}').resize((240,180)),(x+off,y+24))
  board.save(OUT/f'paired-keys-{1+(start-1)//6:02d}.jpg',quality=94)
def main(source,cache):
 rawsha=hashlib.sha256(source.read_bytes()).hexdigest();assert rawsha=='1231a7529dd237adaddd08503c9495584aadfa0c2cce96ee4d8452a4870cf127','wrong raw source';legacy=json.loads((ROOT/'source.json').read_text());src=dict(legacy.get('source',legacy));pool=next(s for s in json.loads((ROOT.parents[1]/'data/wave3.json').read_text())['subjects']if s['slug']=='monkey')
 src.update(start_seconds=pool['start_seconds'],end_seconds=pool['end_seconds'],interval_seconds=[START,END],film_interval_seconds=[pool['start_seconds']+START,pool['start_seconds']+END],clip_film_interval_seconds=[pool['start_seconds'],pool['end_seconds']],source_sha256=rawsha,time_basis='clip-relative seconds',page_url=src['shot_page_url'],why_this_clip='Retained clean interval excludes opening dissolve; head lowers down-left, holds low, then lifts/returns toward camera, observed on16source frames.',source_kind='archive footage',source_approved=False,motion_approved=False,train_eligible=False,rights={'reported':src.get('rights_statement'),'status':'archive reports public_domain; independent rights verification not run'})
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n');sam=OUT/'sam';sam.mkdir(exist_ok=True)
 for name in ['track.json','clip.json']:
  if(cache/name).resolve()!=(sam/name).resolve():shutil.copy2(cache/name,sam/name)
 assert hashlib.sha256((sam/'track.json').read_bytes()).hexdigest()=='b922523a586a6110e2e2f752361cad0f7a2f456ba8bf84777df93d7fe2d88378','wrong pinned track';assert hashlib.sha256((sam/'clip.json').read_bytes()).hexdigest()=='e6020c657bb1b66180276172826ad9a2673276fec9b4a3b5b3769c79f9fe1c1e','wrong pinned clip';tr=json.loads((sam/'track.json').read_text());cl=json.loads((sam/'clip.json').read_text());prov={'branch':'wave2-track/monkey','commit':'31309970a5babf0e1929f8ff58fb55ab25ec59a5','model':'facebook/sam2.1-hiera-small','track_sha256':hashlib.sha256((sam/'track.json').read_bytes()).hexdigest(),'clip_sha256':hashlib.sha256((sam/'clip.json').read_bytes()).hexdigest(),'raw_source_sha256':rawsha,'note':'CI nominal times are not decoded source PTS; f0 is clean while literal raw0 is dissolving. Mask scores are model estimates, not drawing fit.'};(sam/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 cap=cv2.VideoCapture(str(source));sfps=cap.get(cv2.CAP_PROP_FPS);raw=[]
 while True:
  ok,bgr=cap.read()
  if not ok:break
  raw.append(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
 cap.release();frames=[];ious=[];validation={}
 with tempfile.TemporaryDirectory(prefix='.monkey-render-',dir=OUT)as td:
  td=Path(td)
  for f in range(N):
   t=START+f/FPS;idx=round(t*sfps);sim=Image.fromarray(raw[idx]).resize((480,360),Image.Resampling.LANCZOS);svg,s,a=svg_for(t);cart=raster(svg)
   sim.save(td/f'source-{f:03d}.ppm');cart.save(td/f'cartoon-{f:03d}.ppm');pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(sim,(0,24));pair.paste(cart,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'MONKEY | observed head turn/lower/return; native doodle',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
   mi=min(cl['n']-1,max(0,round((t-cl['t0'])*cl['fps'])));m=tr['frames'][mi];mask=np.repeat(np.arange(len(m['rle']))%2,m['rle']).reshape(m['H'],m['W']).astype(bool);dm=np.asarray(raster(svg_for(t,mask=True)[0]).resize((m['W'],m['H']),Image.Resampling.NEAREST))[:,:,0]>127;u=(mask|dm).sum();ious.append(float((mask&dm).sum()/u)if u else 0)
   frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'pose':{k:v.tolist()for k,v in a.items()},'cast':[{'id':'monkey','source':'QuickDraw key'+D['key_id'],'strokes':[q.tolist()for q in s]}]})
   if f in KEYS:
    k=KEYS.index(f)+1;sim.save(OUT/f'source-{k:02d}.jpg',quality=93);cart.save(OUT/f'key-{k:02d}.png');(OUT/f'key-{k:02d}.svg').write_text(svg);ch=svg_for(t,True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(ch);raster(ch).save(OUT/f'character-key-{k:02d}.png')
   if f==0:cart.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=93)
  for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
   p=td/name;subprocess.run(['ffmpeg','-v','error','-y','-threads','1','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(p)],check=True);subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(p),'-f','null','-'],check=True);probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(p)]))['streams'][0];assert int(probe['nb_read_frames'])==N;os.replace(p,OUT/name);validation[name]={'decoded_frames':N,'fps':FPS,'complete':True,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n');shutil.copy2(ROOT/'design.json',OUT/'design.json');shutil.copy2(ROOT/'design.png',OUT/'design.png');(OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'+BG+'</svg>');raster((OUT/'background.svg').read_text()).save(OUT/'background.png')
 fit={'metric':'filled native body/head/ear regions vs nearest approximate12fps SAM sample','mean':float(np.mean(ious)),'min':float(min(ious)),'frames_measured':N,'mean_bar':.65,'minimum_bar':.45,'pass':float(np.mean(ious))>=.65 and min(ious)>=.45,'target_validity':'Root manually inspected4CI samples: broad head/body plausible, soft fur edges approximate. Source raw0dissolves, CI0nominal clean: source PTS not retained by CI.'}
 (OUT/'mask-fit.json').write_text(json.dumps(fit,indent=2)+'\n');traceinfo=trace();traceinfo['pass']=traceinfo.pop('pass_')
 shot={'title':'The monkey lowers its head and returns','revision':'integrated-v2','status':'assembled_candidate_review_pending','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':KEYS,'source':src,'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K'if f in KEYS else'B','note':NOTES[KEYS.index(f)]if f in KEYS else'Same native stroke/point correspondence, interpolated observed head/eye/mouth/ear anchors.'}for f in range(N)],'planes':[{'id':'wall','source':'held source-framed plain wall drawn by agent'},{'id':'monkey_body','source':'nativebody/cheststrokes, lowerbody/tail cropped'},{'id':'monkey_face','source':'QuickDraw key'+D['key_id']}],'camera':{'method':'held static source wall; no camera movement assigned from moving animal','translation':[0,0]},'mask_fit':fit,'assembly_summary':'The original twelve-stroke drawing follows the observed head lowering, low hold and return. The native head, mask, eye marks, mouth U and near ear share one head-local transform; the far ear stays attached at the observed side plane; native body/chest remains below, and the unobserved tail stays beyond the close-up crop. The plain wall is drawn once.','review_status':'review_pending','review_note':'Independent source-pose, native identity and normal-speed motion review pending.','training_ran':False,'motion_approved':False,'train_eligible':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':12,'point_counts':[len(s)for s in ST],'mapping':{'0':'native face mask','1':'left eye','2':'right eye','3':'mouth U','4':'head outline','5':'left outer ear','6':'right outer ear','7':'right inner ear','8':'left inner ear','9':'body outline','10':'tail outside frame','11':'chest mark'},'source_anchors':OBS,'binding':'Observed eyes/mouth/ears remain reference landmarks; native face proportions are protected under the shared crown/turn transform; far ear is inserted at the observed side plane.'},indent=2)+'\n')
 checks={'rendered_frames':N,'keys':len(KEYS),'source_sha256_verified':True,'full_decode':True,'same_topology':True,'original_strokes':12,'all_original_strokes_assigned':True,'held_background_geometry':True,'background_strokes_unchanged_fraction':1.0,'mask_fit':fit,'trace_fidelity':traceinfo,'recognition':'not run','independent_playback':'not run','planted_intervals':0,'foot_slide_gate':False,'release_approved':False,'training_ran':False};(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');pair_boards()
 # Retained source contact sheet, sampled directly from the raw clip, not nominal CI times.
 sheet=Image.new('RGB',(960,4*206),'#fffdf7');pen=ImageDraw.Draw(sheet)
 for j,t in enumerate(np.linspace(START,END,16)):
  im=Image.fromarray(raw[round(float(t)*sfps)]).resize((240,180));x=(j%4)*240;y=(j//4)*206;sheet.paste(im,(x,y+25));pen.text((x+4,y+4),f'{t:.3f} s raw source',fill='#171512')
 sheet.save(OUT/'source-contact-sheet.jpg',quality=94)
 (OUT/'compatibility.json').write_text(json.dumps({'selected_key_id':D['key_id'],'visible_source_parts':['head','two visible ears','eyes','muzzle/mouth','upper torso'],'native_parts':{'head_and_face':'all original facial strokes1:1 under one shared head-local transform; original face-mask containment and proportions protected','ears':'all four original outer/inner ear strokes retained','upper_torso':'same native body/chest strokes adapted to source crop','tail':'original tailstroke retained outside viewport; source tail is not visible, placement unobserved'},'selection':'Existing selected drawing retained; source head/ears/face are represented without adding or deleting major parts. Full lowerbody and tail are outside the source framing.','interval_refinement':'Exclude raw0–.333s opening transition; CI f0 is not raw source0 and is not continuity evidence.','limits':['Real fur is simplified by native angular contour.','Native tail placement outside crop is authored, not source-measured.','Frontal native face must foreshorten to the observed down-left pose; fresh identity review required.']},indent=2)+'\n')
 print(json.dumps(checks))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();main(a.source,a.mask_cache)
