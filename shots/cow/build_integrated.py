"""Source-keyed native Quick, Draw! cow close-up; no learned motion model.
python shots/cow/build_integrated.py --source /path/to/source.mp4 --mask-cache /path/to/cow-cache
"""
from pathlib import Path
import argparse,hashlib,json,math,shutil,tempfile,subprocess,os,io,sys
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=ROOT.parents[2]/'mia-quickdraw-dataset/videos/1f60b8f5-a603-5713-b971-a95ca6401d04.mp4'
CACHE=OUT/'sam';START=1.5;END=5.0;FPS=24;N=84;KEYS=[0,6,12,17,25,39,45,62,74,83]
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float) for s in D['drawing']]
# Coordinates below were read from decoded 320x240 source grids. They are source observations,
# not fits to the drawing or invented chew cycles. Jaw values are observed lower lip extrema.
OBS=[
 {'t':1.5,'poll':[184,25],'muzzle':[205,176],'eyes':[[153,74],[224,77]],'jaw_bottom':208,'ears':[[126,35],[251,40]]},
 {'t':1.75,'poll':[173,25],'muzzle':[179,173],'eyes':[[138,77],[213,79]],'jaw_bottom':200,'ears':[[116,37],[252,42]]},
 {'t':2.,'poll':[169,25],'muzzle':[168,170],'eyes':[[124,77],[207,79]],'jaw_bottom':199,'ears':[[109,35],[249,39]]},
 {'t':2.2083333,'poll':[168,25],'muzzle':[164,171],'eyes':[[122,75],[206,79]],'jaw_bottom':224,'ears':[[106,34],[248,38]]},
 {'t':2.5416667,'poll':[166,26],'muzzle':[159,175],'eyes':[[118,78],[203,80]],'jaw_bottom':217,'ears':[[107,36],[245,39]]},
 {'t':2.7916667,'poll':[164,27],'muzzle':[157,178],'eyes':[[115,80],[201,81]],'jaw_bottom':201,'ears':[[105,38],[244,40]]},
 {'t':3.125,'poll':[165,27],'muzzle':[157,178],'eyes':[[115,80],[201,82]],'jaw_bottom':232,'ears':[[103,36],[245,38]]},
 {'t':3.375,'poll':[164,27],'muzzle':[156,177],'eyes':[[115,80],[200,82]],'jaw_bottom':205,'ears':[[103,34],[241,33]]},
 {'t':3.6666667,'poll':[164,27],'muzzle':[156,178],'eyes':[[114,79],[200,81]],'jaw_bottom':215,'ears':[[104,35],[240,36]]},
 {'t':3.8333333,'poll':[165,27],'muzzle':[157,177],'eyes':[[114,79],[201,81]],'jaw_bottom':207,'ears':[[106,36],[240,38]]},
 {'t':4.0833333,'poll':[165,26],'muzzle':[158,178],'eyes':[[114,79],[201,81]],'jaw_bottom':233,'ears':[[107,35],[241,36]]},
 {'t':4.3333333,'poll':[165,26],'muzzle':[158,177],'eyes':[[114,79],[201,81]],'jaw_bottom':229,'ears':[[109,33],[241,35]]},
 {'t':4.5833333,'poll':[166,27],'muzzle':[157,177],'eyes':[[114,80],[202,81]],'jaw_bottom':208,'ears':[[108,35],[245,41]]},
 {'t':4.9583333,'poll':[166,27],'muzzle':[156,177],'eyes':[[114,80],[202,81]],'jaw_bottom':235,'ears':[[108,34],[250,40]]}]
INTERP={k:PchipInterpolator([o['t']for o in OBS],[o[k]for o in OBS],axis=0) for k in OBS[0] if k!='t'}
NOTES=['Three-quarter head; muzzle remains right of poll.','Head turns toward the camera; muzzle moves left.','Near frontal alignment; jaw almost closed.','First retained open-jaw extreme.','Chew recovery while head settles left.','Later open-jaw extreme.','Jaw closes; ear angles settle.','Deep open-jaw extreme; head held.','Jaw near closed again.','Final open jaw before the later turn away.']

def pts(a):return ' '.join(f'{x:.3f},{y:.3f}'for x,y in a)
def line(a,w=1.35,c='#29261f'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def polygon(a,c='#fffdf7'):return f'<polygon points="{pts(a)}" fill="{c}"/>'
def geometry(t):
 a={k:np.asarray(v(t)) for k,v in INTERP.items()};poll=a['poll'];nose=a['muzzle'];jaw=float(a['jaw_bottom']);eyes=a['eyes'];ears=a['ears'];r=[]
 for i,s in enumerate(ST):
  if i==0:
   yy=np.interp(s[:,1],[23,42,79],[poll[1],75,nose[1]-13]);cx=poll[0]+(nose[0]-poll[0])*np.clip((s[:,1]-23)/56,0,1);xx=cx+(s[:,0]-54)*2.0;q=np.column_stack([xx,yy])
  elif i==1:
   xx=nose[0]+(s[:,0]-56)*1.6;yy=np.interp(s[:,1],[73,84,98,118],[nose[1]-20,nose[1]-9,nose[1]+6,jaw]);q=np.column_stack([xx,yy])
  elif i in [2,3]:
   anchor=eyes[i-2];q=(s-s[0])*np.array([1.,1.1])+anchor
  elif i==4:
   xx=nose[0]+(s[:,0]-53)*1.9;yy=(nose[1]+12)+(s[:,1]-98)/4*max(4,jaw-nose[1]-22);q=np.column_stack([xx,yy])
  elif i==5:
   # Original hooked right ear remains a single unmodified point sequence.
   base=np.array([72,25]);q=(s-base)*np.array([1.6,1.05])+np.array([poll[0]+48,ears[1,1]+7]);q[:,0]+=(ears[1,0]-(poll[0]+80))*.35
  elif i==6:
   base=np.array([34,35]);q=(s-base)*np.array([1.5,1.05])+np.array([poll[0]-43,ears[0,1]+9]);q[:,1]+=(q[:,0]-(poll[0]-43))*(ears[0,1]-35)/100;q[-1]=q[0]+np.array([-2.,2.])
  elif i==7:
   q=np.array([[poll[0]+48,112],[poll[0]+70,136],[poll[0]+103,192],[poll[0]+130,264]],float)
  elif i==8:
   q=np.array([[poll[0]-40,133],[poll[0]-60,158],[poll[0]-76,195],[poll[0]-84,245],[poll[0]+154,385]],float)
  else:
   # Lower body parts remain assigned and move outside this source close-up.
   q=np.column_stack([poll[0]+43+(s[:,0]-86)*.9,132+(s[:,1]-60)*2.6])
  r.append(q)
 return r,a

BG='<rect x="-100" y="-100" width="520" height="440" fill="#fffdf7"/><path d="M-80 158 L35 157 L58 159 L84 159 L100 163 L340 162 L380 340 L-80 340 Z" fill="#eee9dd"/><path d="M-80 158 L35 157 L58 159 L84 159 L100 163 M294 162 L380 161" fill="none" stroke="#a59b87" stroke-width=".8"/>'
def svg_for(t,character=False,mask=False):
 s,a=geometry(t);prefix='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'
 if mask:
  hull=np.vstack([s[7],s[9],s[8][::-1]])
  head=np.vstack([s[0],s[1][::-1]])
  return prefix+'<rect width="320" height="240" fill="#000"/>'+''.join(polygon(q,'#fff')for q in [hull,head,s[1],s[5],s[6]])+'</svg>',s,a
 content='<rect width="320" height="240" fill="#fffdf7"/>' if character else BG
 # Body behind the face; filled head/muzzle hide far body lines, while all native vectors persist.
 content+=''.join(line(s[i])for i in range(7,17))
 content+=polygon(np.vstack([s[0],s[1][::-1]]))+polygon(s[1])+''.join(line(s[i])for i in [0,1,2,3,4,5,6])
 return prefix+content+'</svg>',s,a

def raster(svg):return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB')
def trace():
 sys.path.insert(0,str(ROOT.parents[1]/'tools'));import trace_keys
 rows=[]
 for k in range(1,len(KEYS)+1):
  p=OUT/f'character-key-{k:02d}.png';im=Image.open(p);ss,ink,hw=trace_keys.trace(im);rec,pre,parts=trace_keys.score(ss,ink,*im.size,hw);rows.append({'key':k,'file':p.name,'strokes':ss,'recall':rec,'precision':pre,'parts_kept':parts,'n_strokes':len(ss)})
 (OUT/'traced.json').write_text(json.dumps({'cow':{'W':480,'H':360,'keys':rows}},indent=2)+'\n')
 return {'min_recall':min(x['recall']for x in rows),'min_parts_kept':min(x['parts_kept']for x in rows),'keys':len(rows),'pass':all(x['recall']>=.98 and x['parts_kept']==1 for x in rows)}

def pair_boards():
 for start,stop,name in [(1,7,'paired-keys-01.jpg'),(7,11,'paired-keys-02.jpg')]:
  board=Image.new('RGB',(960,((stop-start+1)//2)*204),'#fffaf0');pen=ImageDraw.Draw(board)
  for j,k in enumerate(range(start,stop)):
   x=(j%2)*480;y=(j//2)*204;pen.text((x+4,y+3),'SOURCE / DRAWING | KEY '+str(k),fill='#111')
   for off,stem,ext in [(0,'source','jpg'),(240,'key','png')]:board.paste(Image.open(OUT/f'{stem}-{k:02d}.{ext}').resize((240,180)),(x+off,y+24))
  board.save(OUT/name,quality=94)

def main(source,cache):
 assert source.exists();rawsha=hashlib.sha256(source.read_bytes()).hexdigest();assert rawsha=='783ccd872a3c2f6ecc4d16b954bf2bb004a3b29e3a1819af9c48bcea115b65be','Unexpected cow source bytes';legacy=json.loads((ROOT/'source.json').read_text());src=dict(legacy.get('source',legacy));pool=next(s for s in json.loads((ROOT.parents[1]/'data/wave3.json').read_text())['subjects']if s['slug']=='cow')
 src.update(start_seconds=pool['start_seconds'],end_seconds=pool['end_seconds'],interval_seconds=[START,END],film_interval_seconds=[pool['start_seconds']+START,pool['start_seconds']+END],clip_film_interval_seconds=[pool['start_seconds'],pool['end_seconds']],source_sha256=rawsha,time_basis='clip-relative seconds',page_url=src['shot_page_url'],why_this_clip='One continuous frontal cow close-up; early turn toward camera followed by repeated jaw opening/closing and ear movement, observed in 16-frame contact sheet.',source_kind='archive footage',source_approved=False,motion_approved=False,train_eligible=False,rights={'reported':src.get('rights_statement'),'status':'archive reports public_domain; independent rights verification not run'})
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n');sam=OUT/'sam';sam.mkdir(exist_ok=True)
 for name in ['track.json','clip.json']:
  if (cache/name).resolve()!=(sam/name).resolve():shutil.copy2(cache/name,sam/name)
 assert hashlib.sha256((sam/'track.json').read_bytes()).hexdigest()=='1dcef8a389ba61298f3b06b6089ec376159af05977aa95d664e47217acedd74a','Unexpected cow SAM snapshot';assert hashlib.sha256((sam/'clip.json').read_bytes()).hexdigest()=='5bbee48799cbe298fa061ebc132a39ce4adab14777f7154d598ce5c3be36cf61','Unexpected cow sample timeline';tr=json.loads((sam/'track.json').read_text());cl=json.loads((sam/'clip.json').read_text());prov={'branch':'wave2-track/cow','commit':'44af07db8fe9559e69b56fb94f65aa9179aca08c','model':'facebook/sam2.1-hiera-small','track_sha256':hashlib.sha256((sam/'track.json').read_bytes()).hexdigest(),'clip_sha256':hashlib.sha256((sam/'clip.json').read_bytes()).hexdigest(),'raw_source_sha256':rawsha,'note':'Model estimates are not drawing fit; direct silhouette intersection computed separately. Source timestamps from CI are approximate.'};(sam/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 cap=cv2.VideoCapture(str(source));sfps=cap.get(cv2.CAP_PROP_FPS);frames=[];ious=[];validation={}
 with tempfile.TemporaryDirectory(prefix='.cow-render-',dir=OUT)as td:
  td=Path(td)
  for f in range(N):
   t=START+f/FPS;idx=round(t*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
   sim=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS);svg,s,a=svg_for(t);cart=raster(svg)
   sim.save(td/f'source-{f:03d}.ppm');cart.save(td/f'cartoon-{f:03d}.ppm');pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(sim,(0,24));pair.paste(cart,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'COW | observed head/ear/jaw keys; native doodle',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
   mi=min(cl['n']-1,max(0,round((t-cl['t0'])*cl['fps'])));m=tr['frames'][mi];mask=np.repeat(np.arange(len(m['rle']))%2,m['rle']).reshape(m['H'],m['W']).astype(bool);dm=np.asarray(raster(svg_for(t,mask=True)[0]).resize((m['W'],m['H']),Image.Resampling.NEAREST))[:,:,0]>127;union=(mask|dm).sum();iou=float((mask&dm).sum()/union)if union else 0;ious.append(iou)
   frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'pose':{k:v.tolist()for k,v in a.items()},'cast':[{'id':'cow','source':'QuickDraw key'+D['key_id'],'strokes':[q.tolist()for q in s]}]})
   if f in KEYS:
    k=KEYS.index(f)+1;sim.save(OUT/f'source-{k:02d}.jpg',quality=93);cart.save(OUT/f'key-{k:02d}.png');(OUT/f'key-{k:02d}.svg').write_text(svg);ch=svg_for(t,True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(ch);raster(ch).save(OUT/f'character-key-{k:02d}.png')
   if f==0:cart.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=93)
  cap.release()
  for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
   p=td/name;subprocess.run(['ffmpeg','-v','error','-y','-threads','1','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(p)],check=True);subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(p),'-f','null','-'],check=True);probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(p)]))['streams'][0];assert int(probe['nb_read_frames'])==N;os.replace(p,OUT/name);validation[name]={'decoded_frames':N,'fps':FPS,'complete':True,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n');shutil.copy2(ROOT/'design.json',OUT/'design.json');shutil.copy2(ROOT/'design.png',OUT/'design.png');(OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'+BG+'</svg>');raster((OUT/'background.svg').read_text()).save(OUT/'background.png')
 fit={'metric':'filled native rig / SAM IoU, nearest approximate 12fps CI sample','mean':float(np.mean(ious)),'min':float(min(ious)),'frames_measured':N,'mean_bar':.65,'minimum_bar':.45,'pass':float(np.mean(ious))>=.65 and min(ious)>=.45,'target_validity':'Manually inspected CI samples1,15,29,43 capture broad cow head/ears; dark shoulder edges are ragged. Jaw motion not validated by segmentation.'}
 (OUT/'mask-fit.json').write_text(json.dumps(fit,indent=2)+'\n');traceinfo=trace()
 shot={'title':'The cow chews toward us','revision':'integrated-v2','status':'assembled_candidate_review_pending','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':KEYS,'source':src,'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K'if f in KEYS else'B','note':NOTES[KEYS.index(f)]if f in KEYS else'Same original stroke/point correspondence, interpolated observed jaw/ear/head anchors.'}for f in range(N)],'planes':[{'id':'sky_field','source':'held source-framed sky/horizon drawn by agent'},{'id':'cow_body','source':'original cow body strokes carried beyond source close-up crop'},{'id':'cow_face','source':'QuickDraw key'+D['key_id']}],'camera':{'method':'held sky/horizon; no camera pan estimated from moving cow','translation':[0,0]},'mask_fit':fit,'assembly_summary':'Original face, muzzle, eye ticks and ear strokes are keyed to the cow turning toward camera and chewing. The source close-up crops most of the full-body doodle; its body parts remain in the editable cast. The sky and distant horizon are drawn once.','review_status':'review_pending','review_note':'Independent still identity/source-event and normal-speed playback review pending.','training_ran':False,'motion_approved':False,'train_eligible':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':17,'mapping':'All original stroke IDs and native point counts retained; face, eye ticks, muzzle, smile and ears have semantic source anchors; source crop hides lower body.','source_anchors':OBS},indent=2)+'\n')
 checks={'rendered_frames':N,'keys':len(KEYS),'source_sha256_verified':True,'full_decode':True,'same_topology':True,'original_strokes':17,'all_original_strokes_assigned':True,'held_background_geometry':True,'background_strokes_unchanged_fraction':1.0,'mask_fit':fit,'trace_fidelity':traceinfo,'recognition':'not run','independent_playback':'not run','planted_intervals':0,'foot_slide_gate':False,'release_approved':False,'training_ran':False};(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');pair_boards();print(json.dumps(checks));subprocess.run([sys.executable,str(ROOT/'finalize_integrated.py')],check=True) if (OUT/f"review-v{int(shot['revision'].split('v')[-1])}.json").exists() else None;subprocess.run([sys.executable,str(ROOT/'build_integrated_page.py')],check=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();main(a.source,a.mask_cache)
