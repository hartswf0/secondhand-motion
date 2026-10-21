"""Native Quick, Draw! spider, source-keyed across the web.
python shots/spider/build_integrated.py --source /path/to/archive.mp4 --mask-cache /path/to/snapshot
"""
from pathlib import Path
import argparse,hashlib,json,math,io,os,shutil,subprocess,tempfile,sys
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1];OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=REPO.parent/'mia-quickdraw-dataset/videos/a975d12c-ffcb-58f5-9c3f-4abf577b102e.mp4';CACHE=OUT/'sam'
START=6.;END=9.;FPS=24;N=73;KEYS=[0,10,18,26,34,45,58,72]
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float)for s in D['drawing']]
# Manual source-pixel observations on exact decoded keyframes (320x240 coordinates).
# Leg correspondence is fixed. The eighth, partly obscured short reach is constrained,
# not claimed to be a tracked material contact.
OBS=[
 {'f':0,'body':[133,145],'angle':78,'scale':[.215,.24],'tips':[[105,116],[119,164],[121,196],[146,209],[155,111],[198,151],[198,182],[159,129]]},
 {'f':10,'body':[134,146],'angle':84,'scale':[.22,.25],'tips':[[100,127],[106,177],[120,194],[148,218],[150,108],[201,146],[202,178],[157,130]]},
 {'f':18,'body':[135,145],'angle':92,'scale':[.22,.25],'tips':[[113,133],[95,169],[112,178],[146,211],[149,102],[205,135],[188,157],[163,222]]},
 {'f':26,'body':[133,135],'angle':97,'scale':[.22,.25],'tips':[[111,123],[92,163],[115,173],[141,194],[145,93],[202,122],[188,147],[157,193]]},
 {'f':34,'body':[134,123],'angle':99,'scale':[.22,.25],'tips':[[111,102],[83,156],[87,180],[149,210],[143,81],[203,109],[187,140],[157,162]]},
 {'f':45,'body':[128,119],'angle':104,'scale':[.22,.25],'tips':[[98,77],[68,164],[83,153],[146,201],[143,71],[201,97],[183,132],[137,174]]},
 {'f':58,'body':[120,118],'angle':100,'scale':[.22,.25],'tips':[[82,67],[66,173],[85,155],[145,203],[140,72],[194,99],[183,132],[132,170]]},
 {'f':72,'body':[138,128],'angle':92,'scale':[.22,.25],'tips':[[85,77],[85,163],[130,197],[167,194],[157,73],[205,119],[188,136],[147,173]]},
]
CAM=json.loads((OUT/'camera.json').read_text());CROWS=CAM['observations'];CI=PchipInterpolator([x['t'] for x in CROWS],[x['camera'] for x in CROWS],axis=0)
I={k:PchipInterpolator([o['f']for o in OBS],[o[k]for o in OBS],axis=0)for k in ['body','angle','scale','tips']}
INK='#29261f';PAPER='#fffdf7'
def pts(a):return ' '.join(f'{x:.3f},{y:.3f}'for x,y in a)
def line(a,w=1.4,c=INK):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,c):return f'<polygon points="{pts(a)}" fill="{c}"/>'
def geometry(f):
 body=np.asarray(I['body'](f));angle=float(I['angle'](f));sc=np.asarray(I['scale'](f));tips=np.asarray(I['tips'](f));a=math.radians(angle);M=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])@np.diag(sc)
 result=[(ST[0]-[128,103])@M.T+body]
 for j,s in enumerate(ST[1:]):
  r=(s[0]-[128,103])@M.T+body;target=tips[j];v=s[-1]-s[0];u=target-r;norm=float(v@v);A=np.array([[u@v,-(v[0]*u[1]-v[1]*u[0])],[(v[0]*u[1]-v[1]*u[0]),u@v]])/norm
  result.append((s-s[0])@A.T+r)
 return result,dict(body=body.tolist(),body_axis_degrees=angle,scale=sc.tolist(),leg_endpoints=tips.tolist(),camera=CI(START+f/FPS).tolist())
# Held macro background: broad out-of-focus stems and leaves observed in first frame.
LEAVES=[([[-50,80],[18,76],[60,100],[34,108],[-50,95]],'#dfd6c4'),([[170,-80],[188,-80],[181,330],[164,330]],'#e4d5c0'),([[276,-80],[291,-80],[292,330],[276,330]],'#ded1bc'),([[-70,-80],[75,-80],[102,10],[74,29],[12,28],[-35,9]],'#eee8dc'),([[99,270],[130,218],[153,217],[149,243],[185,264]],'#e1d9c8'),([[-20,236],[22,220],[49,243],[62,290],[-10,290]],'#e9dfce')]
WEB=[[[-30,23],[89,60]],[[7,59],[20,130],[40,255]],[[138,164],[280,120]],[[142,160],[165,225]],[[103,116],[105,95]]]
def background(cam):
 return '<rect x="-150" y="-150" width="620" height="540" fill="'+PAPER+'"/>'+'<g transform="translate('+str(cam[0]*.5)+' '+str(cam[1]*.5)+')">'+''.join(poly(a,c)for a,c in LEAVES)+'</g>'+'<g transform="translate('+str(cam[0])+' '+str(cam[1])+')">'+''.join(line(a,.6,'#aaa18d')for a in WEB)+'</g>'
def svg_for(f,character=False,mask=False):
 S,A=geometry(f);head='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'
 if mask:return head+'<rect width="320" height="240" fill="#000"/>'+poly(S[0],'#fff')+''.join(line(s,2.0,'#fff')for s in S[1:])+'</svg>',S,A
 if character:return head+'<rect width="320" height="240" fill="'+PAPER+'"/>'+''.join(line(s)for s in S)+'</svg>',S,A
 return head+background(A['camera'])+poly(S[0],PAPER)+''.join(line(s)for s in S)+'</svg>',S,A

def trace():
 sys.path.insert(0,str(REPO/'tools'));import trace_keys
 rows=[]
 for k in range(1,len(KEYS)+1):
  p=OUT/f'character-key-{k:02d}.png';im=Image.open(p);st,ink,hw=trace_keys.trace(im);r,pres,parts=trace_keys.score(st,ink,*im.size,hw);rows.append(dict(key=k,file=p.name,strokes=st,recall=r,precision=pres,parts_kept=parts,n_strokes=len(st)))
 (OUT/'traced.json').write_text(json.dumps({'spider':{'W':480,'H':360,'keys':rows}},indent=2)+'\n')
 return {'min_recall':min(r['recall']for r in rows),'min_parts_kept':min(r['parts_kept']for r in rows),'pass':all(r['recall']>=.98 and r['parts_kept']==1 for r in rows),'keys':len(rows)}

def main():
 sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest();assert sha=='8bc74e02624e810634b906c5fd18e79383f6a32aa8e631cefb5c2e2db310904d','Source bytes differ from reviewed clip';src=json.loads((ROOT/'source.json').read_text());src=src.get('source',src)
 src.update(interval_seconds=[START,END],time_basis='clip_relative_seconds',source_sha256=sha,source_kind='archive macro footage',source_approved=False,motion_approved=False,train_eligible=False)
 # Retain source's original film positions if known; wrapper start/end were provisional clip times.
 src['archive_film_clip_interval_seconds']=[32.733,54.454];src['archive_film_retained_interval_seconds']=[32.733+START,32.733+END]
 src['why_this_interval']='Sixteen source samples show one continuous turn and reach on the web. Camera rises while the spider descends relative to its background. No cut visible in retained samples; normal-speed review unrun.'
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n')
 sam=OUT/'sam';sam.mkdir(exist_ok=True)
 for n in ['track.json','clip.json']:
  if (CACHE/n).resolve()!=(sam/n).resolve():shutil.copy2(CACHE/n,sam/n)
 prov={'branch':'wave2-track/spider','commit':'d9578e140af9ce94fd8ff6942b0702e6892d94b7','model':'facebook/sam2.1-hiera-small','track_sha256':hashlib.sha256((sam/'track.json').read_bytes()).hexdigest(),'source_sha256':sha,'valid_for_object_fit':'partial_subject','audit':'../sam-audit.jpg','limitations':'Four overlay samples visually capture body and most visible legs; thin distal parts are partial, and some web streaks join the mask. Model IoU estimate is not measured drawing fit.'};(sam/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 track=json.loads((sam/'track.json').read_text())['frames'];clip=json.loads((sam/'clip.json').read_text());cap=cv2.VideoCapture(str(SOURCE));sfps=cap.get(cv2.CAP_PROP_FPS);frames=[];fit=[];validation={}
 with tempfile.TemporaryDirectory(prefix='secondhand-motion-spider-')as td:
  tmp=Path(td)
  for f in range(N):
   t=START+f/FPS;idx=round(t*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
   photo=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS);svg,S,A=svg_for(f);cartoon=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB');cartoon.save(tmp/f'cartoon-{f:03d}.ppm');photo.save(tmp/f'source-{f:03d}.ppm')
   pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(photo,(0,24));pair.paste(cartoon,(480,24));pd=ImageDraw.Draw(pair);pd.text((10,6),f'ARCHIVE | {t:.3f}s',fill=INK);pd.text((490,6),'NATIVE DOODLE | source-keyed reaches',fill=INK);pair.save(tmp/f'pair-{f:03d}.ppm')
   frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'anchors':A,'strokes':[s.round(4).tolist()for s in S]})
   if f in KEYS:
    k=KEYS.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');photo.save(OUT/f'source-{k:02d}.jpg',quality=93);(OUT/f'key-{k:02d}.svg').write_text(svg);ch=svg_for(f,character=True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(ch);cairosvg.svg2png(bytestring=ch.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
   if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=93)
   j=max(0,min(len(track)-1,round((t-clip['t0'])*clip['fps'])));q=track[j];m=np.repeat(np.arange(len(q['rle']))%2,q['rle']).reshape(q['H'],q['W']).astype(bool);ms=svg_for(f,mask=True)[0];own=np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=ms.encode(),output_width=q['W'],output_height=q['H']))).convert('L'))>127;u=(m|own).sum();fit.append({'frame':f,'sam_frame':j,'iou':float((m&own).sum()/u) if u else 0})
  cap.release()
  for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
   target=tmp/name;subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(tmp/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True);subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(target),'-f','null','-'],check=True);p=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(target)]))['streams'][0];assert int(p['nb_read_frames'])==N;os.replace(target,OUT/name);validation[name]={'decoded_frames':N,'fps':FPS,'complete':True,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
 tr=trace();metric={'method':'filled native body +2px legs vs nearest SAM12fps sample, approximate time pairing','mean_iou':float(np.mean([r['iou']for r in fit])),'min_iou':min(r['iou']for r in fit),'pass':bool(np.mean([r['iou']for r in fit])>=.65 and min(r['iou']for r in fit)>=.45),'frames':fit,'limitations':prov['limitations']};(OUT/'mask-fit.json').write_text(json.dumps(metric,indent=2)+'\n');(OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 for n in ['design.json','design.png']:shutil.copy2(ROOT/n,OUT/n)
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'+background([0,0])+'</svg>')
 notes=['The compact spider hangs below the diagonal strand; lower legs extend.','Right legs stretch while left legs begin a lateral sweep.','Body descends relative to web; lower right reach is longest.','Body starts to rise within frame under the upward camera.','Lower-left legs fan outward as the right legs lift.','Upper-left limb reaches toward a strand; long lower limb releases.','Upper-left limb is extended along web; body is lowest relative to background.','Body moves right in screen space; upper-left reach remains extended.']
 shot={'title':'Spider across its web','revision':'integrated-v1','status':'assembled_candidate_review_pending','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':KEYS,'source':src,'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K'if f in KEYS else 'B','note':notes[KEYS.index(f)]if f in KEYS else 'Interpolate same original body/leg point correspondence between observed reaches.'}for f in range(N)],'planes':[{'id':'soft_stems','source':'held source-observed background drawn by agent','camera_factor':.5},{'id':'web','source':'held source-observed web strands drawn by agent','camera_factor':1},{'id':'spider','source':'Quick, Draw! key5924220649340928, all nine original strokes'}],'camera':CAM,'assembly_summary':'The original nine-stroke spider changes body attitude and eight leg reaches over one held macro background and web. Source body and endpoint keys are manually observed; background-only optical flow supplies camera movement. The partly hidden eighth reach is constrained rather than tracked.','review_status':'review_pending','review_note':'Independent still identity and source-pose review pending. Normal-speed motion approval and classifier are unrun.','mask_fit':{k:v for k,v in metric.items()if k!='frames'},'training_ran':False,'motion_approved':False,'train_eligible':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':9,'part_mapping':{'0':'body outline','1':'left upper reach','2':'left middle reach','3':'left lower reach','4':'right lower reach','5':'upper right reach','6':'right upper side reach','7':'right lower side reach','8':'partly obscured short reach'},'method':'body retains original points under source keyed affine attitude; every leg keeps original points under its endpoint similarity transform','keys':OBS,'contact_intervals':[],'occlusion_note':'Eight visible-drawing legs do not establish eight verified material contact identities. No four planted intervals were observed.'},indent=2)+'\n')
 checks={'rendered_frames':N,'keys':len(KEYS),'source_sha256_verified':True,'original_strokes_assigned':9,'same_topology':True,'held_background_geometry':True,'mask_fit':{k:v for k,v in metric.items()if k!='frames'},'trace_fidelity':tr,'recognition':'not run','independent_playback':'not run','planted_intervals':0,'foot_slide_gate':False,'release_approved':False,'training_ran':False};(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();SOURCE=a.source;CACHE=a.mask_cache;main()
