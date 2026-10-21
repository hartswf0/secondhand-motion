"""Two source-keyed instances of one native Quick, Draw! ant.
python shots/ant/build_integrated.py --source /path/archive.mp4 --mask-cache /path/ant/cache
"""
from pathlib import Path
import argparse,hashlib,json,math,io,os,shutil,subprocess,tempfile,sys
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1];OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=REPO.parent/'mia-quickdraw-dataset/videos/17c403a7-1f5c-5a7d-9bc5-aa1bac026b73.mp4';CACHE=OUT/'sam'
START=.2;END=2.2;FPS=24;N=49;KEYS=[0,6,12,18,24,30,37,48]
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float)for s in D['drawing']]
# Source screen-pixel observations in 320x240 units. Names identify instances, not tracked feet.
# Five leg strokes per native drawing are kept, not anatomically rewritten into six.
LEFT=[
 [[140,148],[118,142],[94,139]],[[140,145],[119,139],[95,138]],[[147,131],[126,136],[106,144]],[[147,135],[125,141],[103,145]],[[150,141],[130,141],[109,141]],[[149,136],[126,140],[99,157]],[[154,143],[133,140],[107,149]],[[161,151],[140,159],[111,178]]]
RIGHT=[
 [[168,150],[189,159],[212,167]],[[169,151],[190,159],[213,167]],[[171,150],[195,159],[219,167]],[[173,153],[196,160],[219,170]],[[175,160],[197,164],[219,170]],[[178,149],[200,160],[225,168]],[[181,145],[206,159],[231,162]],[[189,143],[211,153],[235,168]]]
LTIPS=[[[136,178],[120,185],[103,177],[79,163],[66,154]],[[133,176],[117,184],[105,176],[84,167],[70,156]],[[144,161],[127,177],[111,174],[94,170],[81,155]],[[149,164],[123,178],[108,173],[93,168],[77,155]],[[154,170],[131,180],[116,176],[98,171],[84,157]],[[154,171],[131,183],[110,181],[92,178],[80,169]],[[158,165],[138,181],[123,176],[105,180],[90,168]],[[165,177],[146,191],[131,190],[110,199],[98,189]]]
RTIPS=[[[155,177],[179,189],[203,184],[220,186],[236,174]],[[155,178],[179,189],[205,185],[221,185],[237,174]],[[159,179],[183,191],[209,188],[225,185],[240,175]],[[161,181],[185,191],[210,190],[225,188],[241,177]],[[162,183],[185,194],[211,191],[229,187],[241,179]],[[165,179],[187,192],[213,188],[232,189],[245,178]],[[167,177],[193,187],[220,189],[237,182],[249,174]],[[174,176],[201,190],[225,194],[241,185],[252,180]]]
LANT=[[[153,125],[163,145]],[[151,123],[163,143]],[[155,116],[169,130]],[[158,120],[167,137]],[[161,126],[170,142]],[[160,119],[174,139]],[[165,127],[178,144]],[[176,133],[183,147]]]
RANT=[[[153,123],[149,145]],[[154,126],[150,146]],[[157,127],[153,142]],[[157,129],[154,146]],[[160,134],[154,153]],[[162,129],[158,146]],[[165,126],[161,140]],[[173,124],[169,139]]]
I={name:{field:PchipInterpolator(KEYS,val,axis=0)for field,val in [('parts',parts),('tips',tips),('antennae',ants)]}for name,parts,tips,ants in [('left',LEFT,LTIPS,LANT),('right',RIGHT,RTIPS,RANT)]}
INK='#29261f';PAPER='#fffdf7';REVISION=3

def pts(a):return ' '.join(f'{x:.3f},{y:.3f}'for x,y in a)
def line(a,w=1.05,c=INK):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,c):return f'<polygon points="{pts(a)}" fill="{c}"/>'
def similarity(s,r,target):
 v=s[-1]-s[0];u=target-r;den=v@v;cross=v[0]*u[1]-v[1]*u[0];M=np.array([[u@v,-cross],[cross,u@v]])/den
 return (s-s[0])@M.T+r

def geometry(f):
 result=[];anchors={}
 for name in ['left','right']:
  p=np.asarray(I[name]['parts'](f));tips=np.asarray(I[name]['tips'](f));ant=np.asarray(I[name]['antennae'](f));axis=p[2]-p[0];axis/=np.linalg.norm(axis);down=np.array([-axis[1],axis[0]])*(1 if axis[0]>=0 else -1)
  M=[np.column_stack([axis*(10/35),down*(10/35)]),np.column_stack([axis*(28/98),down*(28/98)]),np.column_stack([axis*(21/74),down*(21/74)])];centers=[np.array([33,65]),np.array([110,65]),np.array([213,65])]
  def aff(s,part):return (s-centers[part])@M[part].T+p[part]
  def appendage(s,r,target):
   local=s.copy()
   if name=='left':local[:,0]*=-1
   return similarity(local,r,target)
  q=[None]*11;q[0]=aff(ST[0],0);q[3]=aff(ST[3],1);q[5]=aff(ST[5],2)
  for j in [1,2]:q[j]=appendage(ST[j],aff(ST[j][:1],0)[0],ant[j-1])
  q[4]=np.array([aff(ST[4][:1],1)[0],aff(ST[4][-1:],2)[0]])
  for j in range(6,11):q[j]=appendage(ST[j],aff(ST[j][:1],1 if j<9 else 2)[0],tips[j-6])
  result.append(q);anchors[name]={'parts':p.tolist(),'leg_endpoints':tips.tolist(),'antennae_endpoints':ant.tolist(),'horizontal_reflection':bool(axis[0]<0)}
 return result,anchors

# The two rock banks, bright crystal patches, and water opening are drawn once from the source.
ROCKS=[([[-80,-80],[400,-80],[400,119],[289,112],[263,111],[248,119],[221,114],[206,104],[185,106],[170,99],[152,101],[131,91],[119,98],[97,87],[84,97],[67,90],[52,108],[28,111],[-20,105]],'#d4ccbc'),([[-80,160],[-5,161],[14,158],[30,169],[40,182],[55,177],[64,192],[88,182],[109,195],[129,181],[149,194],[174,183],[192,193],[204,176],[219,182],[242,174],[254,183],[271,175],[300,180],[400,170],[400,320],[-80,320]],'#e1d9ca'),([[-30,119],[11,116],[20,128],[36,126],[42,142],[31,151],[13,145],[-10,153]],'#dbd2c0')]
EDGES=[[[0,112],[25,117],[44,128],[57,126],[68,137]],[[0,159],[24,163],[43,179],[57,177],[72,190],[94,182],[117,195],[142,182],[159,192],[181,182],[201,192],[218,178],[240,180],[265,174],[292,183],[320,177]],[[55,227],[80,209],[96,217],[116,204]],[[175,214],[194,210],[218,224],[242,211],[261,218]],[[94,89],[112,101],[128,96],[148,110]],[[216,105],[235,117],[257,112],[275,125]]]
CHIPS=[[[15,132],[21,125],[28,134],[25,143],[19,142]],[[59,179],[66,169],[76,177],[73,187],[65,190]],[[198,181],[205,171],[217,173],[222,184],[211,192],[201,189]],[[247,176],[256,164],[270,170],[272,180],[263,185]],[[100,109],[106,105],[109,110],[105,113]],[[171,94],[179,91],[183,97],[176,100]]]

def background(camera):return '<rect x="-100" y="-100" width="520" height="440" fill="'+PAPER+'"/><g transform="translate('+str(camera[0])+' '+str(camera[1])+')">'+''.join(poly(a,c)for a,c in ROCKS)+''.join(line(a,.65,'#aaa08d')for a in EDGES)+''.join(poly(a,PAPER)+line(a,.65,'#b3a78e')for a in CHIPS)+'</g>'
def svg_for(f,cam,character=False):
 instances,A=geometry(f);head='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">';content='<rect width="320" height="240" fill="'+PAPER+'"/>'if character else background(cam)
 for q in instances:content+=''.join(poly(q[j],PAPER)for j in [0,3,5])+''.join(line(s)for s in q)
 return head+content+'</svg>',instances,A

def trace():
 sys.path.insert(0,str(REPO/'tools'));import trace_keys
 rows=[]
 for k in range(1,len(KEYS)+1):
  im=Image.open(OUT/f'character-key-{k:02d}.png');st,ink,hw=trace_keys.trace(im);r,pr,parts=trace_keys.score(st,ink,*im.size,hw);rows.append(dict(key=k,strokes=st,recall=r,precision=pr,parts_kept=parts))
 (OUT/'traced.json').write_text(json.dumps({'ant':{'W':480,'H':360,'keys':rows}},indent=2)+'\n');return {'min_recall':min(x['recall']for x in rows),'min_parts_kept':min(x['parts_kept']for x in rows),'keys':len(rows),'pass':all(x['recall']>=.98 and x['parts_kept']==1 for x in rows)}

def main():
 sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest();assert sha=='6c4cd2387f20f7bc910613008d3aa94b44b752f3f2638e462ce3e75cdd995d8d';cap=cv2.VideoCapture(str(SOURCE));sfps=cap.get(cv2.CAP_PROP_FPS);raw=[]
 while True:
  ok,bgr=cap.read()
  if not ok:break
  raw.append(cv2.resize(bgr,(480,360),interpolation=cv2.INTER_AREA))
 cap.release();assert raw
 src=json.loads((ROOT/'source.json').read_text())['source'];src['original_plan_why_this_clip']=src.pop('why_this_clip',None);src.update(start_seconds=START,end_seconds=END,why_this_clip='Two ants face one another and alter antenna reach at a rock gap. The retained interval excludes the initial cut; the original one-ant description is rejected.',interval_seconds=[START,END],time_basis='clip_relative_seconds',source_sha256=sha,source_kind='archive macro footage',source_approved=False,motion_approved=False,train_eligible=False,original_plan_interval_seconds=[0,2.25],plan_correction='The first raw frame is another shot. Two ants, not one, are visible throughout the retained interval. Both are represented. No claim that a second ant enters only at2.25s is retained as observation.',why_this_interval='Eighteen preflight samples locate a cut before0.04s and show two ants facing and moving their antennae from0.2 to2.2s. The retained interval is continuous in sampled frames; actual normal-speed approval is unrun.')
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n')
 # Three fixed rock templates isolate source camera drift from either ant's travel.
 first=raw[round(START*sfps)];g0=cv2.GaussianBlur(cv2.cvtColor(first,cv2.COLOR_BGR2GRAY),(3,3),.6);camobs=[]
 patches=[(20,40,100,100),(200,35,290,100),(365,120,440,180)]
 for f in KEYS:
  target=cv2.GaussianBlur(cv2.cvtColor(raw[round((START+f/FPS)*sfps)],cv2.COLOR_BGR2GRAY),(3,3),.6);observed=[]
  for x1,y1,x2,y2 in patches:
   result=cv2.matchTemplate(target[y1-12:y2+12,x1-12:x2+12],g0[y1:y2,x1:x2],cv2.TM_CCOEFF_NORMED);_,score,_,loc=cv2.minMaxLoc(result);observed.append({'xy':[(loc[0]-12)/1.5,(loc[1]-12)/1.5],'ncc':score})
  assert min(p['ncc']for p in observed)>.95
  camobs.append({'f':f,'time':START+f/FPS,'camera':np.median([p['xy']for p in observed],axis=0).tolist(),'patches':observed})
 camI=PchipInterpolator(KEYS,[x['camera']for x in camobs],axis=0);CAM={'method':'median translation of three fixed rock templates, local NCC search +/-12 image pixels','patches_xyxy_480x360':patches,'observations':camobs,'note':'Rock registration only; ants retain independent screen observations. Subpixel film jitter is below template integer-pixel precision. Rejected sparse LK draft retained in revisions/technical-camera-v0.'};(OUT/'camera.json').write_text(json.dumps(CAM,indent=2)+'\n')
 compat={'status':'compatible_with_explicit_simplifications','doodle_key_id':D['key_id'],'native_strokes':11,'instances':2,'inventory':{'body_sections':3,'antennae_strokes':2,'drawn_leg_strokes':5},'observed_source':'Two ants face each other, alter antenna reach and body orientation above the same gap between rocks.','differences':['The native ant has five drawn leg strokes, not six anatomical legs; no sixth is added.','Native legs originate from thorax and abdomen; that construction is preserved rather than anatomically rewritten.','Antenna and foot endpoint observations are keyed pose estimates, not verified material contact tracks.'],'mapping':{'0':'head','1,2':'antennae','3':'thorax outline and native short neck connector','4':'waist connector','5':'abdomen','6,7,8':'three native thorax leg strokes','9,10':'two native abdomen leg strokes'},'source_leg_visibility':'Six anatomical legs are expected per source ant, but overlap, body occlusion and archive softness prevent all material legs being verified at every sampled frame. Five native leg strokes are pose correspondences, not asserted anatomical identities.','facing':'Left instance reflects horizontal native body ordering, right instance keeps it. Both keep every original stroke and original point count.','source_plan_correction':'Original one-ant assumption rejected before keying. Source cut excluded; two instances explicitly represented.'};(OUT/'compatibility.json').write_text(json.dumps(compat,indent=2)+'\n')
 sam=OUT/'sam';sam.mkdir(exist_ok=True)
 for n in ['clip.json','track.json']:
  if (CACHE/n).resolve()!=(sam/n).resolve():shutil.copy2(CACHE/n,sam/n)
 clip=json.loads((sam/'clip.json').read_text());track=json.loads((sam/'track.json').read_text());last=clip['t0']+(clip['n']-1)/clip['fps'];covered=sum(START+f/FPS<=last for f in range(N));samprov={'branch':'wave2-track/ant','commit':'88e190d113066292caa735e5f0c86265deb89002','model':'facebook/sam2.1-hiera-small','track_sha256':hashlib.sha256((sam/'track.json').read_bytes()).hexdigest(),'validity':'invalid for whole-shot two-instance fit','limitations':'Audited masks switch from one ant to a merged two-ant target and back. Last nominal sample is2.0s; final0.2s of assembly has no independent cached mask. No final mask is clamped forward.','sampled_coverage_frames':covered,'assembly_frames':N,'sampled_coverage_fraction':covered/N,'last_nominal_source_time':last};(sam/'provenance.json').write_text(json.dumps(samprov,indent=2)+'\n')
 frames=[];validation={}
 with tempfile.TemporaryDirectory(prefix='secondhand-motion-ant-')as td:
  tmp=Path(td)
  for f in range(N):
   t=START+f/FPS;idx=round(t*sfps);photo=Image.fromarray(cv2.cvtColor(raw[idx],cv2.COLOR_BGR2RGB));cam=camI(f);svg,inst,A=svg_for(f,cam);cart=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB');cart.save(tmp/f'cartoon-{f:03d}.ppm');photo.save(tmp/f'source-{f:03d}.ppm');pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(photo,(0,24));pair.paste(cart,(480,24));dr=ImageDraw.Draw(pair);dr.text((10,6),f'ARCHIVE | {t:.3f}s',fill=INK);dr.text((490,6),'NATIVE DOODLE | two ant instances',fill=INK);pair.save(tmp/f'pair-{f:03d}.ppm')
   frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'camera':cam.tolist(),'objects':[{'id':name,'source_key_id':D['key_id'],'anchors':A[name.replace('_ant','')],'strokes':[s.round(4).tolist()for s in q]}for name,q in zip(['left_ant','right_ant'],inst)]})
   if f in KEYS:
    k=KEYS.index(f)+1;photo.save(OUT/f'source-{k:02d}.jpg',quality=93);cart.save(OUT/f'key-{k:02d}.png');(OUT/f'key-{k:02d}.svg').write_text(svg);ch=svg_for(f,cam,True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(ch);cairosvg.svg2png(bytestring=ch.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
   if f==0:cart.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=93)
  for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
   target=tmp/name;subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(tmp/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True);subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(target),'-f','null','-'],check=True);pr=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(target)]))['streams'][0];assert int(pr['nb_read_frames'])==N;os.replace(target,OUT/name);validation[name]={'decoded_frames':N,'fps':FPS,'complete':True,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
 tr=trace();(OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 for n in ['design.json','design.png']:shutil.copy2(ROOT/n,OUT/n)
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'+background([0,0])+'</svg>');cairosvg.svg2png(url=str(OUT/'background.svg'),write_to=str(OUT/'background.png'))
 notes=['Two ants face one another across the gap; the left abdomen is almost level with its thorax.','Antennae change reach while both body chains remain near their starting placement.','Left head rises and abdomen swings below it; right ant keeps a lower diagonal body.','Left head settles; unequal lower leg reaches change over the same rock edge.','Near antennae draw closer as right head dips.','Left abdomen drops while the heads remain near the shared center.','Left abdomen lifts again; right ant reaches farther right.','Left abdomen drops toward the lower bank as both heads shift right; retain both ants.']
 shot={'title':'Two ants at the rock edge','revision':f'integrated-v{REVISION}','status':'assembled_candidate_review_pending','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':KEYS,'source':src,'design':D,'frames':frames,'xsheet':[{'f':f,'kind':'K'if f in KEYS else'B','note':notes[KEYS.index(f)]if f in KEYS else'Interpolate the same eleven-stroke correspondence for each named instance; no procedural gait.'}for f in range(N)],'camera':CAM,'planes':[{'id':'rocks','source':'held source-observed rocks drawn by agent','camera_factor':1},{'id':'ants','source':'Quick, Draw! key5421013154136064, two instances of all eleven original strokes'}],'assembly_summary':'Two copies of the same eleven-stroke ant follow observed three-part body positions and unequal antenna/leg reaches. The five-legged simplification is preserved; no material contact identity or touching event is asserted from a mask. One held rock plate follows background-only registration.','review_status':'review_pending','review_note':'Independent identity and source-pose review pending. Cached SAM changes target identity and misses the last0.2s; whole-shot mask fit is not valid. Classifier and normal-speed playback remain unrun.','training_ran':False,'motion_approved':False,'train_eligible':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'native_strokes_per_instance':11,'instances':2,'original_point_counts':[len(s)for s in ST],'mapping':compat['mapping'],'keys':[{'f':f,'source_time':START+f/FPS,'left':{'parts':LEFT[k],'tips':LTIPS[k],'antennae':LANT[k]},'right':{'parts':RIGHT[k],'tips':RTIPS[k],'antennae':RANT[k]}}for k,f in enumerate(KEYS)],'verified_contact_intervals':[]},indent=2)+'\n')
 checks={'rendered_frames':N,'keys':len(KEYS),'instances':2,'source_sha256_verified':True,'original_strokes_per_instance':11,'same_topology':True,'held_background_geometry':True,'trace_fidelity':tr,'mask_fit':{'status':'not valid','pass':False,'mean_iou':None,'min_iou':None,'reason':samprov['limitations'],'sampled_coverage_fraction':covered/N},'recognition':'not run','independent_playback':'not run','verified_planted_intervals':0,'foot_slide_gate':False,'release_approved':False,'training_ran':False};(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 # All reference boards are created after writers and tracer finish.
 sheet=Image.new('RGB',(960,4*204),'#f5f1e8');dr=ImageDraw.Draw(sheet)
 for i,f in enumerate(KEYS):
  k=i+1;x=i%2*480;y=i//2*204;im=Image.open(OUT/f'source-{k:02d}.jpg').resize((240,180));ki=Image.open(OUT/f'key-{k:02d}.png').resize((240,180));sheet.paste(im,(x,y+24));sheet.paste(ki,(x+240,y+24));dr.text((x+5,y+5),f'KEY {k} | {START+f/FPS:.3f}s',fill=INK)
 sheet.save(OUT/'paired-keys.jpg',quality=93)
 sheet=Image.new('RGB',(960,4*204),'#f5f1e8');dr=ImageDraw.Draw(sheet)
 for i,t in enumerate(np.linspace(START,END,16)):
  im=Image.fromarray(cv2.cvtColor(raw[round(t*sfps)],cv2.COLOR_BGR2RGB)).resize((240,180));x=i%4*240;y=i//4*204;sheet.paste(im,(x,y+24));dr.text((x+5,y+5),f'{t:.3f}s',fill=INK)
 sheet.save(OUT/'source-contact-sheet.jpg',quality=93);print(json.dumps(checks))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();SOURCE=a.source;CACHE=a.mask_cache;main()
