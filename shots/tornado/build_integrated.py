"""Source-framed tornado cartoon. No spin is inferred from this archive shot.
Usage: python shots/tornado/build_integrated.py --source /path/to/tornado.mp4 --mask-cache /path/to/cache
"""
from pathlib import Path
import os,json,math,tempfile,subprocess,hashlib,shutil,argparse,io
import cv2,numpy as np,cairosvg
cv2.setNumThreads(1)
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('SECONDHAND_MOTION_SOURCE',str(ROOT.parents[2]/'wave2-logs/tornado.mp4')))
CACHE=OUT/'sam'
START=.2335666667;END=3.2699333333;FPS=24;N=math.ceil((END-START)*FPS);KEYS=[0,14,29,44,58,N-1]
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float) for s in D['drawing']]
# Manually observed source-camera coordinates on actual decoded 320x240 frames.
# Camera registration uses utility pole/tree landmarks; untrustworthy LK fits were rejected.
OBS=[{'t':START,'camera':[0,0],'left':63,'right':214,'top':-6,'bottom':[153,218]},
 {'t':.8341667,'camera':[-1,18],'left':67,'right':214,'top':-4,'bottom':[154,218]},
 {'t':1.4347667,'camera':[0,24],'left':71,'right':215,'top':-3,'bottom':[155,217]},
 {'t':2.0687333,'camera':[-4,24],'left':75,'right':213,'top':-2,'bottom':[156,218]},
 {'t':2.6693333,'camera':[-9,18],'left':79,'right':214,'top':-1,'bottom':[157,218]},
 {'t':END,'camera':[-10,22],'left':81,'right':214,'top':0,'bottom':[157,219]}]
I={k:PchipInterpolator([o['t'] for o in OBS],[o[k] for o in OBS],axis=0) for k in OBS[0] if k!='t'}
LEFT=[[-40,260],[-40,145],[-5,137],[4,124],[14,127],[24,117],[32,120],[40,114],[51,120],[60,119],[68,132],[78,133],[80,146],[89,151],[94,166],[110,172],[113,190],[127,202],[133,239]]
RIGHT=[[184,260],[187,195],[201,190],[204,177],[218,174],[221,158],[232,158],[235,145],[246,143],[250,131],[263,123],[273,112],[282,119],[291,115],[300,128],[312,124],[326,139],[355,145],[365,270]]
ROAD=[[110,270],[140,216],[150,209],[165,208],[185,270]]
MIDDLE=[[109,260],[120,213],[127,214],[136,207],[144,210],[150,204],[158,207],[165,200],[173,203],[181,196],[190,202],[199,260],[109,260]]
BG_LINES=[[[104,240],[139,206],[153,200]],[[174,200],[198,240]],[[12,220],[40,215],[63,219]],[[17,211],[17,229]],[[28,209],[28,225]],[[55,219],[70,216],[85,221]],[[66,214],[66,228]],[[214,100],[213,250]],[[208,103],[221,102]],[[211,103],[225,-40]],[[220,101],[245,-40]],[[223,103],[285,-40]],[[211,104],[185,188]],[[196,174],[196,240]],[[236,178],[236,245]]]
# One held car and roadside context drawn against the source. They share the camera transform.
CARS=[[[113,240],[117,226],[123,222],[131,222],[136,228],[139,240]],[[118,227],[133,227]],[[122,224],[122,229]],[[120,235],[124,235]],[[132,235],[136,235]],[[39,228],[43,218],[52,218],[57,228]],[[43,220],[52,220]],[[280,231],[283,219],[292,217],[299,224],[300,237]]]
def pts(a):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in a)
def line(a,w=1.15,c='#29261f'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,c='#fffdf7'):return f'<polygon points="{pts(a)}" fill="{c}"/>'
def geometry(t):
 A={k:np.asarray(v(t)) for k,v in I.items()};cam=A['camera'];left=float(A['left']);right=float(A['right']);top=float(A['top']);bottom=A['bottom']
 result=[]
 for stroke_index,s in enumerate(ST):
  y=s[:,1]/255;baseline=left+(right-left)*s[:,0]/184
  # Mild source-keyed width/centre changes; same original points and stroke correspondence.
  x=baseline+(bottom[0]-(left+(right-left)*106/184))*y
  # Bounded pose repair keeps native point counts.
  if stroke_index: x+=(-1 if stroke_index==1 else 1)*16*np.sin(np.pi*np.clip((y-.4)/.6,0,1))
  yy=top+y*(bottom[1]-top)
  result.append(np.column_stack([x,yy])+cam)
 return result,A

def svg_for(t,character=False,mask=False):
 S,A=geometry(t);cam=A['camera'];prefix='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'
 if mask:
  shell=np.vstack([S[1],S[2][1:]])
  return prefix+'<rect width="320" height="240" fill="#000"/>'+poly(shell,'#fff')+'</svg>',S,A
 if character:return prefix+'<rect width="320" height="240" fill="#fffdf7"/>'+''.join(line(s,1.5) for s in S)+'</svg>',S,A
 # Background fill extends outside the camera so there are no finite-plate edges.
 scene='<rect x="-100" y="-100" width="520" height="440" fill="#fffdf7"/>'
 funnel=''.join(line(s,1.5) for s in S)
 near='<g transform="translate('+str(float(cam[0]))+' '+str(float(cam[1]))+')">'
 near+=poly(LEFT,'#eee9dd')+poly(RIGHT,'#eee9dd')+poly(MIDDLE,'#eee9dd')+line(LEFT,1.0,'#746f62')+line(RIGHT,1.0,'#746f62')+line(MIDDLE,.85,'#746f62')
 near+=poly(ROAD,'#fffdf7')
 near+=''.join(line(s,.9,'#746f62') for s in BG_LINES)
 near+=poly(CARS[0],'#fffdf7')+''.join(line(s,.95,'#5a564d') for s in CARS)
 near+='</g>'
 return prefix+scene+funnel+near+'</svg>',S,A

def trace_and_validate():
 import sys
 sys.path.insert(0,str(ROOT.parents[1]/'tools'));import trace_keys
 tr=[]
 for k in range(1,len(KEYS)+1):
  p=OUT/f'character-key-{k:02d}.png';im=Image.open(p);s,ink,hw=trace_keys.trace(im);rec,pre,parts=trace_keys.score(s,ink,*im.size,hw)
  tr.append(dict(key=k,file=p.name,strokes=s,recall=rec,precision=pre,parts_kept=parts,n_strokes=len(s)))
 (OUT/'traced.json').write_text(json.dumps({'tornado':{'W':480,'H':360,'keys':tr}},indent=2)+'\n')
 return {'minimum_recall':min(x['recall'] for x in tr),'minimum_parts_kept':min(x['parts_kept'] for x in tr),'keys':len(tr),'pass':all(x['recall']>=.98 and x['parts_kept']==1 for x in tr)}

def main():
 source=json.loads((ROOT/'source.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source['source_sha256']
 cache=OUT/'sam';cache.mkdir(exist_ok=True)
 for n in ['clip.json','track.json']:
  if (CACHE/n).resolve()!=(cache/n).resolve():shutil.copy2(CACHE/n,cache/n)
 prov={'branch':'wave2-track/tornado','commit':'6c0f7bc661837f4c71dd12ee9f1c2d5622654757','model':'facebook/sam2.1-hiera-small','track_sha256':hashlib.sha256((cache/'track.json').read_bytes()).hexdigest(),'clip_sha256':hashlib.sha256((cache/'clip.json').read_bytes()).hexdigest(),'source_sha256':source['source_sha256'],'snapshot_policy':'Pinned clip/track JSON and audited evidence retained; bulk source frames/depth not copied. Mask rejected for object fitting.','valid_for_object_fit':False,'reason':'Mask switches from most sky to foreground tree and back; model confidence is not correctness.'}
 (cache/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 cap=cv2.VideoCapture(str(SOURCE));sfps=cap.get(cv2.CAP_PROP_FPS);workspace=tempfile.TemporaryDirectory(prefix='secondhand-motion-tornado-');td=Path(workspace.name);frames=[];validation={}
 for f in range(N):
  t=START+f/FPS;idx=round(t*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  sourceim=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  svg,S,A=svg_for(t);cartoon=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB');cartoon.save(td/f'cartoon-{f:03d}.ppm');sourceim.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(sourceim,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | source-keyed contour; no invented spin',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
  frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'camera_translation':A['camera'].tolist(),'anchors':{k:v.tolist() for k,v in A.items()}})
  if f in KEYS:
   k=KEYS.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');sourceim.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg);ch=svg_for(t,True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(ch);cairosvg.svg2png(bytestring=ch.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
  if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 cap.release()
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  temp=td/name;subprocess.run(['ffmpeg','-v','error','-threads','1','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(temp),'-f','null','-'],check=True);probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,r_frame_rate','-of','json',str(temp)]))['streams'][0];assert int(probe['nb_read_frames'])==N;os.replace(temp,OUT/name);validation[name]={'decoded_frames':int(probe['nb_read_frames']),'fps':FPS,'complete':True}
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n');shutil.copy(ROOT/'design.json',OUT/'design.json');shutil.copy(ROOT/'design.png',OUT/'design.png')
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240"><rect width="320" height="240" fill="#fffdf7"/>'+poly(LEFT,'#eee9dd')+poly(RIGHT,'#eee9dd')+poly(MIDDLE,'#eee9dd')+poly(ROAD,'#fffdf7')+line(LEFT)+line(RIGHT)+line(MIDDLE)+''.join(line(x) for x in BG_LINES+CARS)+'</svg>')
 (OUT/'source-contact-sheet.jpg').write_bytes((ROOT/'source-review/selected/b615f6f9-22b3-571b-bbb6-0739a4f7cf1d-16frames.jpg').read_bytes())
 if (CACHE/'frames').exists():
  audit=Image.new('RGB',(768,624),'#fffaf0');ap=ImageDraw.Draw(audit);track=json.loads((cache/'track.json').read_text())['frames']
  for j,i in enumerate([1,13,25,38]):
   q=track[min(i,len(track)-1)];img=np.asarray(Image.open(CACHE/'frames'/f'f{i:03d}.jpg').convert('RGB')).copy();m=np.repeat(np.arange(len(q['rle']))%2,q['rle']).reshape(q['H'],q['W']).astype(bool);img[m]=(.6*img[m]+.4*np.array([255,0,0])).astype(np.uint8);x=j%2*384;y=j//2*312;audit.paste(Image.fromarray(img),(x,y+24));ap.text((x+5,y+4),f"frame{i} area{q['area']} estimate{q['iou']}",fill='#111')
  audit.save(cache/'audit.jpg')
 else:assert (cache/'audit.jpg').exists(),'Committed SAM audit required when cache frames unavailable'
 trace=trace_and_validate()
 shot={'title':'Tornado beyond the street','revision':'integrated-v2','status':'assembled_candidate_review_pending','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':KEYS,'source':source,'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K' if f in KEYS else 'B','note':(['Funnel framed by street trees; top cloud cropped.','Upper contours shift while foreground drops in the camera.','Broad column continues behind the trees.','Lower funnel remains occluded; no contact or rotation inferred.','Camera settles; contour narrows slightly.','Last retained contour before later credits.'][KEYS.index(f)] if f in KEYS else 'Same native three-stroke topology, smooth keyed source contour.')} for f in range(N)],'planes':[{'id':'sky','source':'held paper sky drawn by agent'},{'id':'tornado','source':'QuickDraw original three strokes key6522189199179776'},{'id':'trees_street','source':'drawn once by agent from source frame7, receives camera translation'}],'camera':{'method':'manual pole/tree landmark registration at six observed source times; LK rejected as unstable','pose_coordinates':[320,240],'background_overscan':True},'source_segmentation':prov,'assembly_summary':'The native three-stroke funnel changes contour behind one held street, tree and utility-pole drawing. Camera movement follows manually observed landmarks. Rotation is not inferred.','review_status':'review_pending','review_note':'Source contour and normal-speed motion review pending.','training_ran':False,'motion_approved':False,'train_eligible':False}
 review_path=OUT/'review-v2.json'
 if review_path.exists():
  review=json.loads(review_path.read_text())
  if review.get('source_framing_pose_bar')=='met' and review.get('same_drawing_identity_bar')=='met':
   shot.update(status='assembled_stills_pass_playback_pending',review_status='still_pass_playback_pending',review_note='Independent review passed the six still poses and original doodle identity. Recognition, valid silhouette fit and normal-speed motion approval remain pending. No training ran.')
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':3,'mapping':'same original point counts; height/width/centre source-keyed, lower sides widened in bounded pose repair; foreground road/tree occlusion hides terminal point','anchors':OBS},indent=2)+'\n')
 checks={'rendered_frames':N,'keys':len(KEYS),'source_sha256_verified':True,'full_decode':True,'same_topology':True,'original_strokes':3,'all_original_strokes_assigned':True,'held_background_geometry':True,'background_camera_registration':'manually observed, not numerically validated','SAM':prov['reason'],'mask_fit':'not measured: unstable sky/tree masks are not a valid tornado target','trace_fidelity':trace,'recognition':'not run','independent_playback':'not run','planted_intervals':0,'foot_slide_gate':False,'release_approved':False,'training_ran':False};(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 workspace.cleanup()
 print(json.dumps({'frames':N,'keys':len(KEYS),'trace':trace,'out':str(OUT)}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--mask-cache',type=Path,default=CACHE);a=p.parse_args();SOURCE=a.source;CACHE=a.mask_cache;main()
