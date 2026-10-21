"""Source-keyed native crouched tiger. No learned motion model.
python shots/tiger/build_integrated.py --source /path/to/clip.mp4 --mask-cache /path/to/cache
"""
from pathlib import Path
import argparse,hashlib,json,shutil,tempfile,subprocess,os,io,sys
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'integrated'
SOURCE=ROOT.parents[2]/'mia-quickdraw-dataset/videos/21f72c0b-0951-50f9-8016-8dbbc3669858.mp4'
START=3.25; END=6.; FPS=24; N=67; KEYS=[0,18,23,27,32,48,66]
D=json.loads((OUT/'design.json').read_text()); ST=[np.array(list(zip(*s)),float)for s in D['drawing']]
OBS=[{'t':3.25,'nose':[272,156],'eyes':[[225,88],[304,91]]},
     {'t':4.,'nose':[271,156],'eyes':[[225,87],[303,90]]},
     {'t':4.2083333,'nose':[266,155],'eyes':[[222,85],[300,90]]},
     {'t':4.375,'nose':[255,154],'eyes':[[213,83],[294,89]]},
     {'t':4.5833333,'nose':[249,154],'eyes':[[207,82],[289,88]]},
     {'t':5.25,'nose':[248,153],'eyes':[[207,82],[288,88]]},
     {'t':6.,'nose':[248,153],'eyes':[[207,82],[287,88]]}]
IP={k:PchipInterpolator([o['t']for o in OBS],[o[k]for o in OBS],axis=0)for k in ['nose','eyes']}
NOTES=['Three-quarter head held above resting forelegs.','Last held pose before the turn becomes visible.','Head begins moving left toward a frontal view.','Mid-turn; both eye anchors move left.','Turn settles into the frontal pose.','Frontal pose held; no invented mouth cycle.','Final frontal hold before the retained interval ends.']
# One source-authored correspondence for the native body contour; every original vertex survives.
BODY=np.array([[260,205],[326,259],[365,265],[409,359],[382,310],[330,316],[307,330],[321,344],[294,356],[249,359],[261,336],[139,328],[90,334],[-22,321],[-33,225],[-25,198],[-40,185],[-170,174],[-155,166],[-100,160],[-15,165],[192,135]],float)
BG='<rect width="480" height="360" fill="#fffdf7"/><path d="M0 0H480V272L420 265L376 249L355 213L338 178L180 165L120 166L58 158L0 165Z" fill="#eee9dd"/><g fill="none" stroke="#a89c89" stroke-width="1"><path d="M0 48L50 38L96 43L116 72L174 61L205 31M0 94L69 80L99 111L153 98L187 108M322 5L362 40L417 29L480 42M355 96L388 74L438 85L480 78M349 143L390 126L427 143L480 120M0 150L71 134L113 153M400 209L450 190L480 201M395 272L422 259L480 270M415 319L453 310L480 327"/></g>'
def pts(a):return ' '.join(f'{x:.3f},{y:.3f}'for x,y in a)
def line(a,w=2.,c='#29261f'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
def poly(a,c='#fffdf7'):return f'<polygon points="{pts(a)}" fill="{c}"/>'
def geometry(t):
 a={k:np.asarray(v(t))for k,v in IP.items()}; nose=a['nose'];result=[]
 for i,s in enumerate(ST):
  if i in [0,1]:
   x=np.interp(s[:,0],[171,189,202,227,244,255],[nose[0]-112,nose[0]-93,nose[0]-64,nose[0],nose[0]+49,nose[0]+87])
   y=np.interp(s[:,1],[1,9,20,30,44],[39,60,106,nose[1]+5,205])
   q=np.column_stack([x,y])
  elif i==2:q=(s-np.array([227,30]))*np.array([2.,1.5])+nose
  elif i in [3,4]:q=(s-np.array([229,35]))*np.array([1.9,2.5])+nose+np.array([0,13])
  elif i==5:q=(s-np.array([201,20]))*2.+a['eyes'][0]
  elif i==6:q=(s-np.array([237,17]))*2.+a['eyes'][1]
  elif i==7:q=BODY.copy()
  else:
   q=np.column_stack([np.interp(s[:,0],[0,66,120,174],[ -170,-15,115,192]),np.interp(s[:,1],[2,10,27,40,49],[160,170,225,286,323])])
  assert q.shape==s.shape
  result.append(q)
 return result,a
def svg_for(t,character=False,mask=False):
 s,a=geometry(t);head=np.vstack([s[0],s[1][::-1]])
 prefix='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">'
 if mask:return prefix+'<rect width="480" height="360" fill="#000"/>'+poly(s[7],'#fff')+poly(head,'#fff')+'</svg>',s,a
 content='<rect width="480" height="360" fill="#fffdf7"/>'if character else BG
 content+=poly(s[7])+line(s[7])+''.join(line(s[i])for i in [8,9,10])+poly(head)+''.join(line(s[i])for i in range(7))
 return prefix+content+'</svg>',s,a
def raster(svg):return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB')
def trace():
 sys.path.insert(0,str(ROOT.parents[1]/'tools'));import trace_keys
 rows=[]
 for k in range(1,len(KEYS)+1):
  p=OUT/f'character-key-{k:02d}.png';im=Image.open(p);ss,ink,hw=trace_keys.trace(im);rec,pre,parts=trace_keys.score(ss,ink,*im.size,hw);rows.append({'key':k,'file':p.name,'strokes':ss,'recall':rec,'precision':pre,'parts_kept':parts})
 (OUT/'traced.json').write_text(json.dumps({'tiger':{'W':480,'H':360,'keys':rows}},indent=2)+'\n')
 return {'min_recall':min(r['recall']for r in rows),'min_parts_kept':min(r['parts_kept']for r in rows),'keys':len(rows),'pass':all(r['recall']>=.98 and r['parts_kept']==1 for r in rows)}
def boards():
 for block,start in enumerate(range(0,len(KEYS),4),1):
  stop=min(start+4,len(KEYS));im=Image.new('RGB',(960,((stop-start+1)//2)*204),'#fffaf0');pen=ImageDraw.Draw(im)
  for j,k in enumerate(range(start+1,stop+1)):
   x=j%2*480;y=j//2*204;pen.text((x+4,y+3),f'SOURCE / DRAWING | KEY{k}',fill='#111')
   for dx,stem,ext in [(0,'source','jpg'),(240,'key','png')]:im.paste(Image.open(OUT/f'{stem}-{k:02d}.{ext}').resize((240,180)),(x+dx,y+24))
  im.save(OUT/f'paired-keys-{block:02d}.jpg',quality=94)
def main(source,cache):
 OUT.mkdir(exist_ok=True);rawsha=hashlib.sha256(source.read_bytes()).hexdigest();assert rawsha=='cafbd01e4e428dcc820d068d8bc3c3e7154c76a7685f0815ade52a4c2347bbfa'
 legacy=json.loads((ROOT/'source.json').read_text());src=dict(legacy.get('source',legacy));pool=next(x for x in json.loads((ROOT.parents[1]/'data/wave3.json').read_text())['subjects']if x['slug']=='tiger')
 src.update(interval_seconds=[START,END],film_interval_seconds=[pool['start_seconds']+START,pool['start_seconds']+END],clip_film_interval_seconds=[pool['start_seconds'],pool['end_seconds']],source_sha256=rawsha,time_basis='clip-relative seconds',page_url=src['shot_page_url'],source_kind='archive footage',why_this_clip='Retained lying-tiger shot after the cut near3s; head turns from three-quarter to frontal around4.2–4.6s, body and paws held.',rights={'reported':src.get('rights_statement'),'status':'Archive reports public_domain; independent rights verification not run'},source_approved=False,motion_approved=False,train_eligible=False)
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n');sam=OUT/'sam';sam.mkdir(exist_ok=True)
 for name in ['track.json','clip.json']:
  if (cache/name).resolve()!=(sam/name).resolve():shutil.copy2(cache/name,sam/name)
 th=hashlib.sha256((sam/'track.json').read_bytes()).hexdigest();ch=hashlib.sha256((sam/'clip.json').read_bytes()).hexdigest();assert th=='fd18ca5c0a30fe12b1d6c8b00ec0c8f3304a89a576c57cb7f7793bdf8738ff5e';assert ch=='57226be0999817bed23df6ce04ec509edeb3d0c26da030e44216a6e867374b99';tr=json.loads((sam/'track.json').read_text());cl=json.loads((sam/'clip.json').read_text())
 (sam/'provenance.json').write_text(json.dumps({'branch':'wave2-track/tiger','commit':'cc1236ca4ca3a7f43e24e501ff0774fe2626dd2a','model':'facebook/sam2.1-hiera-small','track_sha256':th,'clip_sha256':ch,'raw_source_sha256':rawsha,'note':'Whole visible tiger target, not a head-only mask. CI video hash/source PTS unavailable; resampled times approximate. Model IoU estimates are not drawing fit.'},indent=2)+'\n')
 cap=cv2.VideoCapture(str(source));sfps=cap.get(cv2.CAP_PROP_FPS);frames=[];ious=[];validation={}
 contact=Image.new('RGB',(960,4*204),'#fffaf0');pen=ImageDraw.Draw(contact)
 for i,t in enumerate(np.linspace(START,END,16)):
  cap.set(cv2.CAP_PROP_POS_FRAMES,round(t*sfps));ok,bgr=cap.read();assert ok;im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((240,180));x=i%4*240;y=i//4*204;contact.paste(im,(x,y+24));pen.text((x+4,y+5),f'{t:.3f}s',fill='#111')
 contact.save(OUT/'source-contact-sheet.jpg',quality=94)
 with tempfile.TemporaryDirectory(prefix='.tiger-render-',dir=OUT)as td:
  td=Path(td)
  for f in range(N):
   t=START+f/FPS;idx=round(t*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
   sim=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS);svg,s,a=svg_for(t);cart=raster(svg);sim.save(td/f'source-{f:03d}.ppm');cart.save(td/f'cartoon-{f:03d}.ppm')
   pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(sim,(0,24));pair.paste(cart,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f}s',fill='#171512');pen.text((490,6),'TIGER | native crouched drawing, observed head turn',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
   mi=min(cl['n']-1,max(0,round((t-cl['t0'])*cl['fps'])));m=tr['frames'][mi];mask=np.repeat(np.arange(len(m['rle']))%2,m['rle']).reshape(m['H'],m['W']).astype(bool);dm=np.asarray(raster(svg_for(t,mask=True)[0]).resize((m['W'],m['H']),Image.Resampling.NEAREST))[:,:,0]>127;un=(mask|dm).sum();ious.append(float((mask&dm).sum()/un)if un else 0.)
   frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'pose':{k:v.tolist()for k,v in a.items()},'cast':[{'id':'tiger','source':'QuickDraw key'+D['key_id'],'strokes':[q.tolist()for q in s]}]})
   if f in KEYS:
    k=KEYS.index(f)+1;sim.save(OUT/f'source-{k:02d}.jpg',quality=93);cart.save(OUT/f'key-{k:02d}.png');(OUT/f'key-{k:02d}.svg').write_text(svg);csvg=svg_for(t,True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(csvg);raster(csvg).save(OUT/f'character-key-{k:02d}.png')
   if f==0:cart.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=94)
  cap.release()
  for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
   p=td/name;subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(p)],check=True);subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(p),'-f','null','-'],check=True);probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(p)]))['streams'][0];assert int(probe['nb_read_frames'])==N;os.replace(p,OUT/name);validation[name]={'decoded_frames':N,'fps':FPS,'complete':True,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n');(OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">'+BG+'</svg>');raster((OUT/'background.svg').read_text()).save(OUT/'background.png')
 fit={'metric':'filled native whole tiger head/body vs nearest approximate SAM12fps sample','mean':float(np.mean(ious)),'min':float(min(ious)),'frames_measured':N,'mean_bar':.65,'minimum_bar':.45,'pass':float(np.mean(ious))>=.65 and min(ious)>=.45,'target_validity':'Root inspected4samples: whole visible lying tiger selected, with small gaps/soft boundaries. Not a head-only mask.'};(OUT/'mask-fit.json').write_text(json.dumps(fit,indent=2)+'\n');traceinfo=trace()
 shot={'title':'The resting tiger turns its head','revision':'integrated-v2','status':'assembled_candidate_review_pending','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':KEYS,'source':src,'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K'if f in KEYS else'B','note':NOTES[KEYS.index(f)]if f in KEYS else'Same native point correspondence; interpolation of observed head/eye anchors, held body.'}for f in range(N)],'planes':[{'id':'rock_plate','source':'Source-framed rocks drawn once by agent'},{'id':'tiger_body','source':'Native crouched tiger body/tail/folded legs/stripe strokes7–10, held from source pose'},{'id':'tiger_head','source':'Native angular head, eyes, muzzle strokes0–6 keyed to source landmarks'}],'camera':{'method':'Held rock plate; no source camera pan observed in retained contact sheet. No quantitative camera estimate claimed.'},'mask_fit':fit,'assembly_summary':'Original11-stroke crouched tiger selected jointly with the lying source before keys. Native head and eye marks follow the observed three-quarter-to-frontal turn; native striped body and folded paws hold. Hidden tail is cropped rather than invented.','review_status':'review_pending','review_note':'Independent source-pose and identity still review pending. Normal-speed playback and classifier remain unrun.','motion_approved':False,'train_eligible':False,'training_ran':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':11,'point_counts':[len(s)for s in ST],'source_anchors':OBS,'held_native_body_vertices':BODY.tolist(),'mapping':'Native semantic head/face parts source-keyed; own native crouched body/folded legs/stripes held. All original point counts survive.'},indent=2)+'\n');checks={'rendered_frames':N,'keys':len(KEYS),'source_sha256_verified':True,'full_decode':True,'same_topology':True,'original_strokes':11,'all_original_strokes_assigned':True,'held_background_geometry':True,'background_strokes_unchanged_fraction':1.,'mask_fit':fit,'trace_fidelity':traceinfo,'recognition':'not run','independent_playback':'not run','planted_intervals':0,'foot_slide_gate':False,'release_approved':False,'training_ran':False};(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');boards();print(json.dumps(checks))
 if (ROOT/'build_integrated_page.py').exists():subprocess.run([sys.executable,str(ROOT/'build_integrated_page.py')],check=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=OUT/'sam');a=p.parse_args();main(a.source,a.mask_cache)
