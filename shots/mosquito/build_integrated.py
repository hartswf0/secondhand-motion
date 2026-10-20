"""Mosquito on skin: native doodle strokes posed against observed source frames.
Usage: python shots/mosquito/build_integrated.py --source /path/to/mosquito.mp4
No flight cycle, model training, or classifier recognition is claimed.
"""
from pathlib import Path
import os,json,math,hashlib,tempfile,subprocess,argparse,shutil
import cv2,numpy as np,cairosvg
cv2.setNumThreads(1)
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('SECONDHAND_MOTION_SOURCE',str(ROOT.parents[2]/'wave2-logs/mosquito.mp4')))
FPS=24;START=.2335669002335669;END=5.238571905238572;N=math.ceil((END-START)*FPS)
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(x[0],x[1])),float) for x in D['drawing']]
# These are source-camera coordinates, measured on decoded images, not a centred model sheet.
OBS=[
 {'t':START,'head':[124,89],'root':[133,83],'tip':[166,83],'wing':[139,82,161,75,150,87],'probe':[109,113]},
 {'t':.9009009,'head':[124.5,88.7],'root':[134,83],'tip':[166,80],'wing':[140,82,163,77,151,87],'probe':[109,113]},
 {'t':1.3013013,'head':[125,90],'root':[135,85],'tip':[164,91],'wing':[141,83,162,88,150,91],'probe':[109,113]},
 {'t':1.5682349,'head':[125,90.8],'root':[135,86],'tip':[163,98],'wing':[140,84,162,93,150,93],'probe':[109,113]},
 {'t':2.2355689,'head':[124.8,90],'root':[134.5,85],'tip':[165,89],'wing':[140,83,163,85,151,90],'probe':[109,113]},
 {'t':3.5702369,'head':[124,90],'root':[134,84],'tip':[165,87],'wing':[139,83,161,81,150,89],'probe':[109,113]},
 {'t':4.4044044,'head':[124.1,89.8],'root':[134,84],'tip':[165,88],'wing':[139,83,162,82,150,89],'probe':[109,113]},
 {'t':END,'head':[124.2,90],'root':[134,84],'tip':[165.5,87.5],'wing':[139,83,163,82,150,89],'probe':[109,113]}]
I={k:PchipInterpolator([x['t'] for x in OBS],[x[k] for x in OBS]) for k in OBS[0] if k!='t'}
SKIN=[[0,4],[36,18],[88,34],[145,52],[200,72],[260,92],[320,109],[320,240],[0,240]]
# One sparse hair field drawn against the selected source. Its geometry never changes.
HAIRS=[[[1,78],[19,57],[49,44]],[[0,102],[32,83],[59,69]],[[1,56],[16,60],[33,76]],[[25,110],[49,85],[83,65]],[[34,35],[41,63],[58,81]],[[12,122],[41,103],[84,95]],[[59,32],[60,48],[71,63]],[[90,42],[95,54],[103,69]],[[75,108],[93,98],[112,99]],[[88,133],[106,120],[123,120]],[[119,239],[127,174],[125,120]],[[140,56],[147,75],[154,101]],[[155,71],[169,86],[186,94]],[[174,77],[169,96],[157,118]],[[188,87],[183,105],[169,124]],[[206,87],[204,102],[194,121]],[[203,136],[196,117],[184,106]],[[160,143],[176,131],[196,127]],[[206,158],[224,138],[248,125]],[[219,100],[231,110],[252,119]],[[252,106],[245,120],[245,140]],[[281,113],[264,130],[251,143]],[[315,123],[290,145],[272,155]],[[320,151],[287,147],[251,132]],[[320,172],[286,158],[251,143]],[[318,203],[290,175],[257,161]],[[320,224],[300,203],[280,193]],[[274,239],[283,209],[284,181]],[[225,221],[247,193],[278,177]],[[7,198],[28,169],[43,144]],[[13,171],[42,148],[70,138]],[[51,213],[64,182],[74,163]],[[92,178],[92,151],[103,131]],[[148,198],[158,172],[175,160]],[[185,228],[189,201],[196,182]]]
def pts(a):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in a)
def line(a,w=1.05,c='#25211c'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,fill='#fffdf7'):return f'<polygon points="{pts(a)}" fill="{fill}"/>'
def curve(a):return f'<path d="M{a[0][0]} {a[0][1]} Q{a[1][0]} {a[1][1]} {a[2][0]} {a[2][1]}" fill="none" stroke="#82765f" stroke-width=".67" stroke-linecap="round"/>'
def affine_tri(s,src,dst):
 M=cv2.getAffineTransform(np.float32(src),np.float32(dst));return cv2.transform(np.float32(s)[None],M)[0]
def bone(s,a,b):
 d=s[-1]-s[0];L=np.linalg.norm(d);u=d/L;v=np.array([-u[1],u[0]]);q=s-s[0];axis=np.array(b)-a;scale=np.linalg.norm(axis)/L;uu=axis/max(1e-9,np.linalg.norm(axis));vv=np.array([-uu[1],uu[0]])
 return np.array(a)+np.outer(q@u,uu)*scale+np.outer(q@v,vv)*scale
def geometry(t):
 A={k:np.array(v(t)) for k,v in I.items()};root=A['root'];tip=A['tip'];axis=(tip-root)/136.;perp=np.array([-axis[1],axis[0]])
 head=(ST[0]-[91,96])*[.29,.22]+A['head']
 body=root+np.outer(ST[2][:,0]-108,axis)+np.outer(ST[2][:,1]-85,perp)*1.1
 probe=bone(ST[1],head[5],A['probe'])
 wa=A['wing'].reshape(3,2);goal=wa[1]-wa[0];native=ST[7][3]-ST[7][0];angle=math.atan2(goal[1],goal[0])-math.atan2(native[1],native[0]);R=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]]);wing=wa[0]+.26*(ST[7]-ST[7][0])@R.T
 legs=[]
 # Foot locations are held source contacts. No cyclic foot lifting is invented.
 for idx,base_offset,foot in [(3,[-2,7],[103,120]),(4,[0,8],[147,122]),(5,[2,7],[167,116]),(6,[5,8],[176,123])]:
  base=root+np.array(base_offset)
  legs.append(bone(ST[idx],base,foot))
 return [head,probe,body,*legs,wing],A
def svg_for(t,shift=(0,0),character=False,mask=False):
 S,A=geometry(t);head,probe,body,*rest=S;legs=rest[:4];wing=rest[4]
 c='#fffdf7' if not mask else '#ffffff';ink='#25211c' if not mask else '#ffffff'
 glyph=''.join(line(s,1.02,ink) for s in [probe,*legs])+poly(body,c)+poly(head[:11],c)+poly(wing,c)+line(wing,1.0,ink)+line(body,1.03,ink)+line(head,1.05,ink)
 prefix='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240">'
 if character:return prefix+'<rect width="320" height="240" fill="#fffdf7"/>'+glyph+'</svg>',S,A
 if mask:return prefix+'<rect width="320" height="240" fill="#000000"/>'+glyph+'</svg>',S,A
 bg='<rect width="320" height="240" fill="#26231e"/>'+f'<g transform="translate({shift[0]:.3f} {shift[1]:.3f})">'+poly(SKIN,'#f1ebdf')+''.join(curve(a) for a in HAIRS)+'</g>'
 return prefix+bg+glyph+'</svg>',S,A
def decode_rle(r):return np.repeat(np.arange(len(r['rle']))%2,r['rle']).reshape(r['H'],r['W']).astype(np.uint8)
def finish_checks():
 import sys
 sys.path.insert(0,str(ROOT.parents[1]/'tools'));import trace_keys
 traced=[]
 for k in range(1,9):
  im=Image.open(OUT/f'character-key-{k:02d}.png');st,ink,hw=trace_keys.trace(im);rec,pre,parts=trace_keys.score(st,ink,*im.size,hw)
  traced.append({'key':k,'file':f'character-key-{k:02d}.png','strokes':st,'recall':rec,'precision':pre,'parts_kept':parts,'n_strokes':len(st)})
 (OUT/'traced.json').write_text(json.dumps({'mosquito':{'W':480,'H':360,'keys':traced}},indent=2)+'\n')
 validations={}
 for name in ['cartoon.mp4','comparison.mp4','source-excerpt.mp4']:
  cap=cv2.VideoCapture(str(OUT/name));fps=cap.get(cv2.CAP_PROP_FPS);n=0
  while cap.read()[0]:n+=1
  cap.release();assert n==N and abs(fps-FPS)<.001
  validations[name]={'decoded_frames':n,'fps':fps,'complete':True}
 (OUT/'video-validation.json').write_text(json.dumps(validations,indent=2)+'\n')
 checks=json.loads((OUT/'assembly-checks.json').read_text());checks['trace_fidelity']={'minimum_recall':min(x['recall'] for x in traced),'minimum_parts_kept':min(x['parts_kept'] for x in traced),'keys':8,'pass':all(x['recall']>=.98 and x['parts_kept']==1 for x in traced)};checks['full_decode']=True
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
def main():
 source=json.loads((ROOT/'source.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source['source_sha256']
 clip=json.loads((OUT/'source-clip.json').read_text());track=json.loads((OUT/'source-track.json').read_text())['frames']
 cap=cv2.VideoCapture(str(SOURCE));sfps=cap.get(cv2.CAP_PROP_FPS);cap.set(cv2.CAP_PROP_POS_FRAMES,round(START*sfps));ok,ref=cap.read();assert ok
 grayref=cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY);valid=np.zeros_like(grayref);valid[130:235,10:310]=255
 features=cv2.goodFeaturesToTrack(grayref,maxCorners=120,qualityLevel=.02,minDistance=8,mask=valid)
 td=Path(tempfile.mkdtemp(prefix='secondhand-motion-mosquito-'));keys=[0,16,26,32,48,80,100,N-1];frames=[];ious=[];observed_shifts=[]
 for f in range(N):
  t=START+f/FPS;idx=round(t*sfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY);flow,status,_=cv2.calcOpticalFlowPyrLK(grayref,gray,features,None)
  good=status[:,0]>0;dv=(flow-features)[good,0];shift=np.median(dv,axis=0) if len(dv) else np.zeros(2);observed_shifts.append(shift.tolist())
  sourceimage=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  svg,S,A=svg_for(t,shift);png=cairosvg.svg2png(bytestring=svg.encode());import io
  cartoon=Image.open(io.BytesIO(png)).convert('RGB');cartoon.save(td/f'cartoon-{f:03d}.ppm');sourceimage.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(sourceimage,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | mosquito on skin',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
  tridx=min(len(track)-1,max(0,round((t-clip['t0'])*clip['fps'])));row=track[tridx];sam=decode_rle(row)
  msvg,_,_=svg_for(t,mask=True);inkmask=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=msvg.encode()))).convert('L').resize((row['W'],row['H']),Image.Resampling.NEAREST);mask=np.asarray(inkmask)>127
  iou=float(np.logical_and(mask,sam).sum()/max(1,np.logical_or(mask,sam).sum()));ious.append(iou)
  frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/sfps,'source_track_frame':tridx,'camera_translation':shift.tolist(),'source_sam_estimated_iou':row['iou'],'rendered_subject_vs_sam_iou':iou,'anchors':{k:v.tolist() for k,v in A.items()}})
  if f in keys:
   k=keys.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');sourceimage.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg)
   charsvg,_,_=svg_for(t,character=True);(OUT/f'character-key-{k:02d}.svg').write_text(charsvg);cairosvg.svg2png(bytestring=charsvg.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
  if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 cap.release()
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  temp=td/name
  subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-preset','slow','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(temp),'-f','null','-'],check=True)
  os.replace(temp,OUT/name)
 # Integrated revision uses the native source orientation, not the mirrored isolated-draft preview.
 integrated_design={**D,'transform':'none','previous_isolated_preview_transform':D.get('transform'),'orientation_reason':'native left-facing head matches source, same original eight strokes/key_id'};(OUT/'design.json').write_text(json.dumps(integrated_design,indent=2)+'\n')
 designlines=''.join(line(s,1.6) for s in ST);designsvg='<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="-20 -20 295 235"><rect x="-20" y="-20" width="295" height="235" fill="#fffdf7"/>'+designlines+'</svg>';cairosvg.svg2png(bytestring=designsvg.encode(),write_to=str(OUT/'design.png'))
 notes=['Native doodle head faces left, matching source skin contact.','Abdomen lifts slightly while contact points remain near the skin.','Abdomen begins pitching down; no takeoff.','Observed strongest downward abdomen pitch.','Abdomen recovers toward horizontal.','Small held standing adjustments.','Late resting pose; appendages remain near skin.','End of continuous on-skin interval.']
 shot={'title':'Mosquito on skin','status':'assembled_candidate_review_pending','revision':'integrated-v3','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':keys,'source':source,'design':integrated_design,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K' if f in keys else 'B','note':notes[keys.index(f)] if f in keys else 'Native-stroke in-between; source time recorded in frames.'} for f in range(N)],'planes':[{'id':'skin','source':'drawn by agent once against source frame7','polygon':SKIN},{'id':'hairs','source':'drawn by agent as simplified observed context; not individually tracked','strokes':HAIRS},{'id':'mosquito','source':'original eight QuickDraw strokes, native left-facing orientation, with keyed part correspondence'}],
 'wing_projection':{'method':'rigid2Drotation and uniform.26scale of native wing along observed folded direction','native_contour_proportions_preserved':True},'review_status':'late_registration_repair_pending','review_note':'Late mosquito placement still needs the source’s upward-left shift; motion unapproved.','camera':{'method':'reference-to-frame LK median on skin below y130; subject excluded','tracked_features':len(features),'translation_range':np.ptp(np.array(observed_shifts),axis=0).tolist()},'mask_fit':{'method':'union of closed native head/body/wing fills plus1.02px original appendage lines rendered and nearest-resized to SAM384x288; IoU vs nearest12fps SAM frame. SAM thin-part omissions limit this metric.','mean':float(np.mean(ious)),'minimum':float(np.min(ious)),'frames':N,'bar_mean':.65,'bar_minimum':.45,'pass':bool(np.mean(ious)>=.65 and np.min(ious)>=.45)},
 'source_segmentation':{'model':'facebook/sam2.1-hiera-small','detector':'IDEA-Research/grounding-dino-tiny','source_branch':'wave2-track/mosquito','source_commit':'5a9479364bd6ff739d4362abb7583ad9c985c2f6','track_sha256':hashlib.sha256((OUT/'source-track.json').read_bytes()).hexdigest(),'frames':len(track),'estimated_iou_is_not_measured_fit':True},'assembly_summary':'A source-framed mosquito remains on one held skin surface. Native head, abdomen, wing and leg strokes follow observed pitch changes; no flight cycle is invented.','training_ran':False,'motion_approved':False,'train_eligible':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':8,'parts':{'head':0,'long_head_appendage':1,'abdomen':2,'legs':[3,4,5,6],'wing':7},'source_anchors':OBS,'topology':'same eight original stroke point counts for every frame; affine/piecewise part posing'},indent=2)+'\n')
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="#26231e"/>'+poly(SKIN,'#f1ebdf')+''.join(curve(a) for a in HAIRS)+'</svg>')
 checks={'rendered_frames':N,'keys':len(keys),'source_sha256_verified':True,'all_original_strokes_assigned':True,'original_strokes':8,'same_topology':True,'held_background_geometry':True,'SAM':'ran upstream; source snapshots/provenance retained','mask_fit':shot['mask_fit'],'recognition':'not run','independent_playback':'not run','release_approved':False,'training_ran':False,'contacts':{'authored_held_points':4,'independently_observed_planted_intervals':0,'gate_pass':False,'reason':'Held contacts are authored from source inspection; four independent planted intervals were not established.'}}
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 finish_checks()
 print(json.dumps({'frames':N,'keys':len(keys),'mask_mean':float(np.mean(ious)),'mask_min':float(np.min(ious)),'out':str(OUT)}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=SOURCE);args=p.parse_args();SOURCE=args.source.expanduser().resolve();main()
