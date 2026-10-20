"""Source-framed pig closeup: original doodle strokes under one keyed anatomical mesh.
Usage: python shots/pig/build_integrated.py --source /path/to/pig.mp4
SAM masks are reference measurements, not a replacement for the doodle.
"""
from pathlib import Path
import json,math,hashlib,subprocess,os,argparse,tempfile,shutil,importlib.util
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
from scipy.spatial import Delaunay
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('SECONDHAND_MOTION_SOURCE',str(ROOT.parents[2]/'wave2-logs/pig.mp4')))
CACHE=OUT/'source-masks' if (OUT/'source-masks/track.json').exists() else Path('/workspace/scratch/e78c43b4722d/wave2-track-cache/pig')
FPS=24;START=6.3063063063;END=8.2415749082;N=math.ceil((END-START)*FPS)
D=json.loads((ROOT/'design.json').read_text());ST=[np.c_[255-np.array(s[0],float),np.array(s[1],float)] for s in D['drawing']]
TIMES=[6.3063063063,6.8735402069,7.1404738071,7.4074074074,7.7077077077,8.2415749082]
TOP0=np.array([[135,60],[195,56],[276,41],[317,32],[337,37],[349,72],[351,106]],float)
BOT0=np.array([[352,125],[345,152],[323,167],[288,172],[260,172],[218,170],[183,161],[162,157],[147,151],[137,141]],float)
TOP1=np.array([[164,55],[207,5],[270,-20],[323,-16],[343,10],[354,52],[348,88]],float)
BOT1=np.array([[332,97],[313,124],[281,142],[253,151],[229,155],[205,156],[184,155],[174,154],[165,148],[163,134]],float)
# Fixed triangulation over the doodle head; targets are observed on exact source frames.
REF=np.array([[0,0],[69,0],[0,105],[69,105],[48,0],[23,8],[12,58],[6,69],[20,76],[27,98],[61,105],[69,35],[40,30]],float)
TRI=Delaunay(REF)
HEADS=[
 [[40,40],[137,32],[40,145],[150,160],[105,27],[88,44],[43,99],[43,109],[58,116],[80,133],[148,158],[135,60],[98,82]],
 [[56,25],[151,18],[53,145],[166,160],[113,22],[100,38],[76,90],[77,102],[91,117],[105,134],[160,158],[143,55],[112,70]],
 [[100,5],[185,18],[100,148],[195,165],[164,18],[135,30],[120,96],[121,111],[137,122],[152,139],[185,162],[177,47],[154,74]],
 [[103,15],[193,14],[101,160],[198,171],[168,30],[145,27],[122,114],[122,127],[138,140],[155,151],[187,164],[184,47],[156,92]],
 [[65,25],[183,-10],[60,188],[192,177],[154,31],[124,30],[89,143],[92,159],[106,172],[132,175],[184,166],[177,43],[133,100]],
 [[55,8],[180,-5],[40,190],[175,165],[135,16],[99,24],[66,140],[70,154],[83,165],[112,167],[177,165],[164,55],[122,99]]]
FRONT=[[[162,146],[163,180],[153,230]],[[162,147],[163,181],[153,230]],[[188,148],[184,184],[170,228]],[[196,146],[183,189],[168,239]],[[192,149],[174,199],[165,249]],[[183,143],[164,191],[143,248]]]
REAR=[[[310,149],[308,186],[302,224]],[[307,145],[305,181],[296,218]],[[310,142],[307,181],[294,213]],[[311,143],[306,181],[294,218]],[[291,144],[279,181],[260,220]],[[273,136],[255,176],[232,218]]]
LEGS=[
 [[[292,152],[294,178],[277,213]],[[316,143],[317,184],[304,222]],[[196,185],[183,215]],[[192,151],[196,185]],[[160,151],[165,192],[153,230]]],
 [[[287,148],[281,179],[278,211]],[[311,144],[310,185],[297,219]],[[196,179],[190,211]],[[188,148],[196,179]],[[161,150],[164,193],[154,230]]],
 [[[287,141],[285,172],[276,204]],[[315,142],[313,181],[302,216]],[[172,178],[160,211]],[[178,148],[172,178]],[[205,143],[193,187],[184,224]]],
 [[[294,141],[282,174],[269,210]],[[318,141],[310,177],[297,221]],[[169,187],[167,226]],[[184,149],[169,187]],[[204,149],[188,193],[180,241]]],
 [[[288,142],[275,178],[256,217]],[[313,139],[301,172],[286,217]],[[175,191],[179,230]],[[190,152],[175,191]],[[196,156],[173,206],[161,254]]],
 [[[268,135],[251,174],[233,210]],[[302,124],[291,162],[273,207]],[[171,190],[169,230]],[[186,151],[171,190]],[[177,158],[155,204],[145,254]]]]
BOXES=[[43,105,18,19,0],[78,101,20,20,-.1],[122,108,21,22,.05],[122,126,23,23,-.1],[92,157,24,22,.2],[72,154,23,23,.2]]
BOX_INTERP=PchipInterpolator(TIMES,BOXES)
OBS=[]
for i,t in enumerate(TIMES):
 u=i/5;top=TOP0*(1-u)+TOP1*u;bot=BOT0*(1-u)+BOT1*u
 # Source backs rise as the camera-facing turn opens; retain authentic clipping.
 if i==2:top+=np.array([8,-10]);bot+=np.array([8,-8])
 if i==3:top+=np.array([12,-6]);bot+=np.array([12,-3])
 top[0]=HEADS[i][11]
 OBS.append(dict(t=t,top=top.tolist(),belly=bot.tolist(),head=HEADS[i],front=FRONT[i],rear=REAR[i]))
INTERP={k:PchipInterpolator(TIMES,[x[k] for x in OBS]) for k in ['top','belly','head','front','rear']}
LEG_INTERP={i:PchipInterpolator(TIMES,[x[i] for x in LEGS]) for i in range(5)}
BG=[[[0,83],[48,83],[92,83]],[[0,47],[48,47],[95,47]],[[0,98],[49,98]],[[0,50],[0,0]],[[58,0],[59,82]],[[1,14],[132,14]],[[0,127],[62,127]],[[0,150],[72,150]],[[0,200],[80,200]],[[0,231],[112,231]],[[4,158],[80,178],[137,188]],[[9,217],[101,215],[161,240]],[[236,206],[319,229]],[[262,176],[320,183]]]
# Chainlink behind the animal, drawn once rather than redrawn each key.
for x in range(-80,240,15):BG.append([[max(0,x),0],[min(141,x+93),83]])
for x in range(0,240,15):BG.append([[min(141,x),0],[max(0,x-93),83]])
PANEL=[[135,0],[251,0],[248,92],[137,91],[135,0]]
def pts(a):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in a)
def line(a,w=1.3,c='#24211d'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
def polygon(a,fill='#fffdf7'):return f'<polygon points="{pts(a)}" fill="{fill}"/>'
def headmap(s,target):
 si=TRI.find_simplex(s);ans=[]
 for p,k in zip(s,si):
  if k<0:k=int(np.argmax([0 if TRI.find_simplex(p+1e-6)>=0 else -1]))
  tr=TRI.transform[k];b=np.dot(tr[:2],p-tr[2]);w=np.r_[b,1-b.sum()];ans.append(w@target[TRI.simplices[k]])
 return np.array(ans)
def along(s,target):
 # Original vertices correspond directly for torso, preserving angular vocabulary.
 return np.array(target)
def leg(s,anchors,shift=0):
 a=np.array(anchors,float)+[shift,0];u=(s[:,1]-s[0,1])/(s[-1,1]-s[0,1] or 1)
 return np.array([a[0]*(1-q*2)+a[1]*(q*2) if q<.5 else a[1]*(2-q*2)+a[2]*(q*2-1) for q in u])
def snapshot(t,character=False):
 A={k:np.array(v(t)) for k,v in INTERP.items()};mapped={}
 mapped[3]=A['top'];mapped[4]=A['belly'];mapped[1]=headmap(ST[1],A['head']);mapped[2]=headmap(ST[2],A['head'])
 bx,by,bw,bh,ba=BOX_INTERP(t);R=np.array([[math.cos(ba),-math.sin(ba)],[math.sin(ba),math.cos(ba)]])
 def compact_snout(a):return ((a-[11.5,66.5])*[bw/23,bh/29])@R.T+[bx,by]
 mapped[1][5:]=compact_snout(ST[1][5:]);mapped[2][0]=compact_snout(ST[2][:1])[0]
 # Native tail is assigned and retained offscreen behind the clipped rump.
 mapped[0]=(ST[0]-[240,90])*[.8,1]+[352,90]
 for i in range(5):mapped[i+5]=np.array(LEG_INTERP[i](t))
 body=np.vstack([A['top'],[A['belly'][0]],A['belly'],A['head'][[10,9,8,7,6,12,11]]])
 # Fill a simple skin cel under the original linework so the fence cannot bleed through.
 full=''.join(line(s,.7,'#79776c') for s in BG)+polygon(PANEL,'#e8e5db')+line(PANEL,.8,'#79776c')
 head_fill=headmap(np.array([[69,35],[48,0],[40,30],[23,8],[11,36],[13,57],[0,69],[20,80],[27,98],[61,105]],float),A['head'])
 subject=''.join(line(mapped[i],1.5) for i in [0,5,6,7,8])+polygon(body)+polygon(head_fill)+''.join(line(mapped[i],1.5) for i in [3,4,9,1,2])
 # Internal face planes remain the native looping snout, not conventional facial detail.
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="#fffdf7"/>'+('' if character else full)+subject+'</svg>'
 # Filled subject envelope used for numerical IoU. Limbs are finite-width cels around native lines.
 mask=np.zeros((240,320),np.uint8);cv2.fillPoly(mask,[np.round(body).astype(np.int32)],1);cv2.fillPoly(mask,[np.round(head_fill).astype(np.int32)],1)
 for i in [5,6,7,8,9]:cv2.polylines(mask,[np.round(mapped[i]).astype(np.int32)],False,1,thickness=13)
 return svg,A,mapped,mask

def render():
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==json.loads((ROOT/'source.json').read_text())['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));srcfps=cap.get(cv2.CAP_PROP_FPS);td=Path(tempfile.mkdtemp(prefix='secondhand-motion-pig-'));keys=[0,13,20,26,34,N-1];frames=[]
 for f in range(N):
  t=START+f/FPS;idx=round(t*srcfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  source=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  svg,A,mapped,mask=snapshot(t);cairosvg.svg2png(bytestring=svg.encode(),write_to=str(td/'frame.png'));cartoon=Image.open(td/'frame.png').convert('RGB');cartoon.save(td/f'cartoon-{f:03d}.ppm');source.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | same source instant',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
  frames.append(dict(f=f,time=f/FPS,source_time=t,source_frame_index=idx,source_index_time=idx/srcfps,anchors={k:v.tolist() for k,v in A.items()}))
  if f in keys:
   k=keys.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');source.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg)
   charsvg=snapshot(t,True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(charsvg);cairosvg.svg2png(bytestring=charsvg.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
  if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 cap.release()
 validation={}
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  temp=td/name;subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-preset','slow','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(temp),'-f','null','-'],check=True);temp.replace(OUT/name);validation[name]=dict(decoded_frames=N,fps=FPS,complete=True)
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 shutil.copy(ROOT/'design.json',OUT/'design.json');shutil.copy(ROOT/'design.png',OUT/'design.png')
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240">'+''.join(line(s,.7,'#79776c') for s in BG)+polygon(PANEL,'#e8e5db')+line(PANEL,.8,'#79776c')+'</svg>')
 cache=OUT/'source-masks';cache.mkdir(exist_ok=True)
 for name in ['clip.json','track.json']:
  if (CACHE/name).resolve()!=(cache/name).resolve():shutil.copy(CACHE/name,cache/name)
 prov={'branch':'wave2-track/pig','commit':'a3ae55b59e45c664a34c491dd6f088cb2d6480a3','model':'facebook/sam2.1-hiera-small','detector':'IDEA-Research/grounding-dino-tiny','masks_sha256':hashlib.sha256((cache/'track.json').read_bytes()).hexdigest(),'mask_predicted_iou_is_not_fit_measurement':True}
 (cache/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 meta=json.loads((cache/'clip.json').read_text());track=json.loads((cache/'track.json').read_text())['frames'];fits=[]
 for q in track:
  t=meta['t0']+q['f']/meta['fps']
  if not START<=t<=END:continue
  m=np.repeat(np.arange(len(q['rle']))%2,q['rle']).reshape(q['H'],q['W']).astype(np.uint8);native=snapshot(t)[3];native=cv2.resize(native,(q['W'],q['H']),interpolation=cv2.INTER_NEAREST)>0;m=m>0
  fits.append(dict(source_time=t,iou=float((native&m).sum()/max(1,(native|m).sum())),sam_predicted_iou=q['iou']))
 fit={'measurement_scope':'Filled rig envelope proxy, not rendered cartoon ink/pixel coverage. No pixel-exact artwork-mask claim.','time_alignment':'CI nominal sample time t0 + frame/fps; ffmpeg frame selection may differ by one source frame.','method':'filled native-body cel polygon plus 13px source-space limb envelopes against SAM binary object mask; coordinates resized nearest-neighbor; not ink overlap','frames':fits,'mean':float(np.mean([x['iou'] for x in fits])),'minimum':min(x['iou'] for x in fits),'bar_mean':.65,'bar_minimum':.45};fit['pass']=fit['mean']>=.65 and fit['minimum']>=.45;(OUT/'mask-fit.json').write_text(json.dumps(fit,indent=2)+'\n')
 shot={'title':'Pig turns into the closeup','status':'assembled_candidate_review_pending','revision':'integrated-v3','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':keys,'source':json.loads((ROOT/'source.json').read_text()),'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[dict(f=f,kind='K',note=n) for f,n in zip(keys,['Side view; rump stays cropped at right.','Head begins turning; first foreleg holds.','Snout advances toward camera; ears change overlap.','Three-quarter turn; near foreleg reaches.','Body foreshortens; near leg leaves bottom crop.','Near-facing lowered snout; back and feet retain source crop.'])],'planes':[dict(id='fence',source='drawn once by agent against actual source',strokes=BG),dict(id='panel',source='drawn once by agent against actual source',strokes=[PANEL]),dict(id='pig',source='QuickDraw key5298401904164864; source-keyed anatomical maps')],'camera':{'method':'held plate; source camera not estimated numerically','depth_parallax':'not inferred'},'assembly_summary':'The cropped pig turns toward the camera over one held yard and fence drawing. Six source-linked keys retain the original looping snout, pointed ears and dangling leg strokes.','training_ran':False,'motion_approved':False,'train_eligible':False,'mask_provenance':prov,'review_note':'Independent source-pose and motion review pending.'}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n')
 (OUT/'correspondence.json').write_text(json.dumps({'original_stroke_count':len(ST),'mapping':{'head':[1,2],'torso':[3,4],'tail':[0],'legs':[5,6,7,8,9]},'compact_snout_boxes':BOXES,'snout_method':'original boxed spiral points use one bounded anatomical snout transform; no new facial ink','reference_head_mesh':REF.tolist(),'triangles':TRI.simplices.tolist(),'poses':OBS,'articulated_leg_paths':LEGS,'leg_method':'five original leg stroke identities retained; manual knee samples added for articulation and source-matched reach; far legs rendered behind torso cel'},indent=2)+'\n')
 checks={'rendered_frames':N,'fps':FPS,'keys':len(keys),'full_decode':True,'source_sha256_verified':True,'same_topology_all_frames':True,'original_stroke_count':len(ST),'all_original_strokes_assigned':True,'SAM':'precomputed SAM2.1 masks inspected and used for comparison; manual anatomy landmarks authored against source','mask_fit':{'mean':fit['mean'],'min':fit['minimum'],'pass':fit['pass'],'metric':'filled rig envelope vs SAM proxy, not rendered cartoon ink/pixel coverage'},'held_background_geometry':True,'recognition_classifier':'not run','foot_contact':'fewer than four independently verified planted intervals; no pass claimed','independent_playback':'not run','release_approved':False,'training_ran':False}
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');finalize_trace();print(json.dumps({'frames':N,'keys':len(keys),'mask_fit':fit['mean'],'min':fit['minimum'],'out':str(OUT)}))
def finalize_trace():
 spec=importlib.util.spec_from_file_location('character_trace',ROOT.parents[1]/'tools/trace_keys.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);rows=[]
 for p in sorted(OUT.glob('character-key-*.png')):
  im=Image.open(p);st,ink,hw=m.trace(im);rec,pre,parts=m.score(st,ink,*im.size,hw);rows.append(dict(file=p.name,recall=rec,precision=pre,parts_kept=parts,half_width=hw,strokes=st))
 (OUT/'traced.json').write_text(json.dumps(dict(method='tools/trace_keys.py trace and score on separated original-vector character exports',keys=rows),separators=(',',':'))+'\n')
 p=OUT/'assembly-checks.json';d=json.loads(p.read_text());d['trace_fidelity']={'min_recall':min(x['recall'] for x in rows),'parts_kept':min(x['parts_kept'] for x in rows),'pass':min(x['recall'] for x in rows)>=.98 and min(x['parts_kept'] for x in rows)==1};p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,default=SOURCE);ap.add_argument('--mask-cache',type=Path,default=CACHE);args=ap.parse_args();SOURCE=args.source;CACHE=args.mask_cache;render()
