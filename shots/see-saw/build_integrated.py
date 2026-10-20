"""Source-framed seesaw assembly. Usage: python shots/see-saw/build_integrated.py --source /path/to/see-saw.mp4
Original board strokes keep one rigid 3D construction; source pose angles are manually observed.
The available SAM mask mixes separate parallel boards and is not used as an instance-fit target.
"""
from pathlib import Path
import argparse,os,json,math,hashlib,subprocess,tempfile,shutil
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('SECONDHAND_MOTION_SOURCE',str(ROOT.parents[2]/'wave2-logs/see-saw.mp4')))
CACHE=(OUT/'sam') if (OUT/'sam/track.json').exists() else ROOT.parents[2]/'wave2-track-cache/see-saw'
FPS=24;START=9.45;END=16.1;N=math.ceil((END-START)*FPS)
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),float) for s in D['drawing']]
OBS=[(9.45,30),(10.5,30),(11.6,29),(12.05,25),(12.4,11),(12.7,0),(13.05,-10),(13.35,-14),(13.75,-18),(14.2,-19),(14.65,-17),(15.,-8),(15.3,3),(15.65,20),(16.1,29)]
ANGLE=PchipInterpolator(*np.array(OBS).T)
PIVOT=np.array([151.,155.]);HALF=112.;U=np.array([.94,.20]);Z=np.array([0.,-.80]);FILL='#fffdf7';INK='#24211d'
DIR=np.array([.796,.605]);NORM=np.array([-.605,.796]);CENTER=np.array([127.,96.])
BG=[[[0,108],[46,111],[101,105],[146,103],[209,108],[254,107],[320,112]],[[0,174],[45,170],[94,172]],[[224,199],[270,200],[320,196]],[[0,213],[55,209],[112,214],[169,222],[220,238]],[[123,198],[162,201],[203,211],[248,224],[285,232]],[[235,185],[271,191],[319,207]]]
# One drawing of tree trunks and shrub contours, held throughout this fixed camera shot.
for x,y in [(8,13),(39,30),(74,5),(112,22),(151,8),(187,25),(230,10),(271,29),(310,1)]:
 BG += [[[x,y],[x+2,76],[x-3,105]],[[x+1,y+40],[x-12,y+19]],[[x+1,y+58],[x+13,y+35]]]
for x,y in [(0,90),(28,84),(58,91),(87,79),(116,85),(144,77),(173,85),(201,89),(226,81),(257,89),(286,83),(315,90)]:
 BG += [[[x-17,y+14],[x-20,y+6],[x-13,y-2],[x-7,y],[x-5,y-8],[x+4,y-10],[x+10,y-3],[x+18,y-4],[x+23,y+5],[x+18,y+12]]]

def pts(a):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in a)
def line(a,w=1.2,c=INK):
 a=np.asarray(a)
 if len(a)==1:return f'<circle cx="{a[0,0]:.3f}" cy="{a[0,1]:.3f}" r=".85" fill="{c}"/>'
 return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
def poly(a,w=1.2,c=INK):return f'<polygon points="{pts(a)}" fill="{FILL}" stroke="{c}" stroke-width="{w}" stroke-linejoin="round"/>'
def circ(p,r,w=1):return f'<circle cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="{r}" fill="{FILL}" stroke="{INK}" stroke-width="{w}"/>'
def vec(theta):
 a=math.radians(theta);return U*math.cos(a)+Z*math.sin(a)
def boardpoint(u,theta,v=0):return PIVOT+vec(theta)*u+np.array([0.,v])
def mapped_board(s,theta):
 a=(s-CENTER)@DIR/140*HALF;b=(s-CENTER)@NORM/14*2.8
 return np.array([boardpoint(u,theta,v) for u,v in zip(a,b)])
def fixed_support(s):
 mn=ST[3].min(0);mx=ST[3].max(0)
 return (s-mn)/(mx-mn)*[42,43]+[130,154]
def plank(a,b,width=3):
 a=np.array(a,float);b=np.array(b,float);d=b-a;n=np.array([-d[1],d[0]])/np.linalg.norm(d)*width
 return poly([a+n,b+n,b-n,a-n],1.)
def rider(seat,theta):
 # Child added as sparse source-derived context. Head and hip follow the seat; legs fold on descent.
 x,y=seat;lift=float(np.clip((30-theta)/49,0,1));hip=np.array([x-1,y-3]);head=np.array([x+3,y-36])
 s=circ(head,5.4,.9)+line([head+[-4,-3],head+[3,-4]],.75)+line([head+[-5,1],head+[-6,3],head+[-3,3]],.75)
 shoulders=np.array([x+1,y-25]);s+=poly([shoulders+[-5,0],shoulders+[6,-1],hip+[6,0],hip+[-5,0]],.95)
 s+=line([shoulders+[-4,2],[x-15,y-22],[x-20,y-23]],1.1)+line([shoulders+[5,2],[x+18,y-24],[x+20,y-27]],1.05)
 knee=np.array([x-17,y-6-8*lift]);foot=np.array([x-31,y-1-20*lift]);s+=line([hip+[-1,0],knee,foot,foot+[-5,0]],1.3)
 s+=line([hip+[4,0],knee+[5,4],foot+[6,4],foot+[1,4]],1.)
 return s

def background_context():
 s=''.join(line(a,.7,'#877f72') for a in BG)
 # Rear stationary board and two distant riders are agent drawn from source.
 s+=plank([94,88],[325,192],2.)+line([[242,150],[242,183],[228,188]],1.)+line([[242,150],[260,184]],1.)
 for x,y in [(166,122),(187,126)]:
  s+=circ([x,y-30],4.3,.8)+poly([[x-6,y-22],[x+6,y-23],[x+8,y-3],[x-7,y-2]],.8)
  s+=line([[x-5,y-18],[x-12,y-8],[x-7,y-6]],.85)+line([[x+3,y-2],[x+12,y+7],[x+9,y+17]],.9)
 s+=plank([67,167],[312,131],2.5)+line([[186,151],[185,193]],1.)
 return s

def leg_knee(hip,ankle,l1,l2):
 delta=ankle-hip;d=float(np.linalg.norm(delta));along=delta/d;a=(l1*l1-l2*l2+d*d)/(2*d);h=math.sqrt(max(0,l1*l1-a*a));normal=np.array([along[1],-along[0]])
 return hip+along*a+normal*h

def foreground_context(t):
 # Near figure bends at the waist, with neck attached; leg IK preserves planted ankle anchors.
 s=plank([-27,96],[250,247],3.2)+line([[77,173],[75,239]],1.2)+line([[77,173],[103,218]],1.)
 lift=float(np.clip((30-float(ANGLE(t)))/49,0,1));hip=np.array([4.+14*lift,164.-7*lift]);waist=np.array([1.+9*lift,134.-6*lift]);shoulder=np.array([29.-30*lift,142.-40*lift]);head=np.array([43.-47*lift,151.-64*lift])
 left=np.array([-5.,0.]);right=np.array([5.,0.])
 s+=poly([hip+left,waist+left,shoulder+[-5,-2],shoulder+[5,-2],waist+right,hip+right],1.)
 s+=line([shoulder,head+(shoulder-head)/np.linalg.norm(shoulder-head)*6],1.)+circ(head,6.7,1.)+line([head+[-4,-3],head+[4,-3]],.8)
 for origin,ankle,L1,L2 in [(hip+[-4,0],np.array([13.,209.]),27.,29.),(hip+[5,0],np.array([32.,197.]),25.,27.)]:
  knee=leg_knee(origin,ankle,L1,L2);s+=line([origin,knee,ankle,ankle+[7,1]],1.35)
 hand=np.array([49-15*lift,173-65*lift]);s+=line([shoulder+[3,1],(shoulder+hand)/2+[6,2],hand],1.2)
 return s

def snapshot(t):
 theta=float(ANGLE(t));board=mapped_board(ST[1],theta);support=fixed_support(ST[3]);dot0=mapped_board(ST[0],theta);dot2=fixed_support(ST[2])
 subject=poly(support,1.15)+line(dot2,1.)+poly(board,1.55)+line(dot0,1.)
 seat=boardpoint(-102,theta,-2)
 handle=[seat+[-4,0],seat+[-4,-12],seat+[2,-15],seat+[9,-10],seat+[9,0]]
 actors=rider(seat,theta)+line(handle,.85)
 # Near context occludes the selected rider naturally when the left end is down.
 body=background_context()+subject+actors+foreground_context(t)
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="{FILL}"/>{body}</svg>'
 char=f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="white"/>{subject}</svg>'
 return svg,char,{'angle_degrees':theta,'fulcrum':PIVOT.tolist(),'left_seat':seat.tolist(),'left_endpoint':boardpoint(-HALF,theta).tolist(),'right_endpoint':boardpoint(HALF,theta).tolist()}

def trace_character_keys():
 import sys
 sys.path.insert(0,str(ROOT.parents[1]/'tools'))
 import trace_keys as tracer
 result={'source':'native vector character-only exports; original four doodle strokes','keys':[]}
 for f in sorted(OUT.glob('character-key-*.png')):
  st,ink,hw=tracer.trace(Image.open(f));rec,prec,parts=tracer.score(st,ink,480,360,hw)
  result['keys'].append({'file':f.name,'recall':rec,'precision':prec,'parts_kept':parts,'half_width':hw,'strokes':st})
 result['min_recall']=min(k['recall'] for k in result['keys']);result['min_parts_kept']=min(k['parts_kept'] for k in result['keys']);result['gate_pass']=result['min_recall']>=.98 and result['min_parts_kept']==1.
 (OUT/'traced.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
 return {k:v for k,v in result.items() if k!='keys'}

def encode(td,stem,name):
 import uuid
 temp=OUT/(name+'.'+uuid.uuid4().hex+'.pending.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(temp),'-f','null','-'],check=True,capture_output=True);temp.replace(OUT/name)

def main():
 raw=json.loads((ROOT/'source.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==raw['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));srcfps=cap.get(cv2.CAP_PROP_FPS);td=Path(tempfile.mkdtemp(prefix='secondhand-motion-see-saw-'))
 keys=[0,52,67,78,93,107,123,140,N-1];frames=[];cards=[]
 for f in range(N):
  t=START+f/FPS;idx=round(t*srcfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  source=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  svg,char,A=snapshot(t);cairosvg.svg2png(bytestring=svg.encode(),write_to=str(td/'frame.png'));cartoon=Image.open(td/'frame.png').convert('RGB')
  cartoon.save(td/f'cartoon-{f:03}.ppm');source.save(td/f'source-{f:03}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | source-keyed rigid board',fill='#171512');pair.save(td/f'pair-{f:03}.ppm')
  frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/srcfps,'anchors':A})
  if f in keys:
   k=keys.index(f)+1;cartoon.save(OUT/f'key-{k:02}.png');source.save(OUT/f'source-{k:02}.jpg',quality=91);(OUT/f'key-{k:02}.svg').write_text(svg);(OUT/f'character-key-{k:02}.svg').write_text(char);cairosvg.svg2png(bytestring=char.encode(),write_to=str(OUT/f'character-key-{k:02}.png'));cards.append(pair.copy())
  if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 cap.release()
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:encode(td,stem,name)
 sheet=Image.new('RGB',(960,len(cards)*384),'white')
 for i,c in enumerate(cards):sheet.paste(c,(0,i*384))
 sheet.save(OUT/'paired-keys.jpg',quality=90)
 # Current source selection refines away the opening exposure fade; original root source record stays intact.
 src={**raw,'interval_seconds':[START,END],'prior_draft_interval_seconds':raw['interval_seconds'],'film_interval_seconds':[float(raw['start_seconds'])+START,float(raw['start_seconds'])+END],'why_this_clip':'The opening exposure fade is excluded. One near-board lift, high reversal, and return are visible with fixed fulcrum, rider and parallel equipment context.'}
 (OUT/'source.json').write_text(json.dumps(src,indent=2)+'\n');shutil.copy(ROOT/'design.json',OUT/'design.json');shutil.copy(ROOT/'design.png',OUT/'design.png')
 samdir=OUT/'sam';samdir.mkdir(exist_ok=True)
 for name in ['track.json','clip.json']:
  if (CACHE/name).resolve()!=(samdir/name).resolve():shutil.copy(CACHE/name,samdir/name)
 (samdir/'provenance.json').write_text(json.dumps({'repository':'hartswf0/secondhand-motion','branch':'wave2-track/see-saw','commit':'cf5df58ca80c8c9536d8f920654f5a01ee65898f','model':'facebook/sam2.1-hiera-small','frames':87,'RLE_all_lengths_valid':True,'input_sha256':{name:hashlib.sha256((samdir/name).read_bytes()).hexdigest() for name in ['track.json','clip.json']},'single_instance_mask_valid':False,'limitation':'SAM merges multiple parallel boards. Whole combined mask is not a valid single-board target; no source mask-fit gate is claimed.','predicted_iou_is_not_measured_source_fit':True},indent=2)+'\n')
 (OUT/'background.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="{FILL}"/>{background_context()}</svg>')
 notes=['Left end remains low; rider is partly hidden by the nearer row.','Low hold ends; rider starts rising.','Left end rises through the middle of its travel.','Rider rises into view.','Near highest observed position.','High reversal and brief hold.','Left end begins descending.','Mid descent.','Low return, rider again partly occluded.']
 shot={'title':'See-saw: lift, wait, return','status':'assembled_candidate_review_pending','review_status':'rider_seat_pose_repair_pending','review_note':'High rider pose still needs a clearer seated hip and bent knees; motion unapproved.','review_badge':'RIDER SEATED POSE NEEDS REPAIR','independent_review':'review-v3.json','revision':'integrated-v3','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':keys,'source':src,'design':D,'frames':frames,'xsheet':[{'f':f,'kind':'K' if f in keys else ('H' if abs(float(ANGLE.derivative()(START+f/FPS)))<.01 else 'B'),'note':dict(zip(keys,notes)).get(f,'Held low source pose.' if abs(float(ANGLE.derivative()(START+f/FPS)))<.01 else 'In-between source-observed angle anchors.')} for f in range(N)],'source_angle_observations':[{'time':t,'angle_degrees':a} for t,a in OBS],'rig':{'original_doodle_strokes':D['drawing'],'foreground_actor':{'foot_anchors':[[13,209],[32,197]],'leg_lengths':[[27,29],[25,27]],'method':'Keyed waist/shoulder positions, attached neck, two-bone leg IK with fixed ankles; source contact intervals unmeasured'},'pivot':PIVOT.tolist(),'board_half_length_world_units':HALF,'rigid_length_world_units':2*HALF,'projection_horizontal_depth_axis':U.tolist(),'projection_vertical_axis':Z.tolist(),'method':'Original plank points expressed in one board-local coordinate system, then projected under a single source-keyed 3D hinge angle; no unmatched-stroke morph.'},'camera':{'type':'held','method':'Manual source inspection; no camera movement inferred'},'planes':[{'id':'wooded_background','source':'drawn by agent once against source'},{'id':'rear_equipment_and_riders','source':'drawn by agent as held observed context'},{'id':'selected_board','source_strokes':[0,1,2,3],'source':'Original QuickDraw four strokes with one fixed support and one rigid hinged plank'},{'id':'selected_rider','source':'drawn by agent against source seat/head/leg relationships'},{'id':'foreground_occluder','source':'nearer parallel board drawn once; foreground child straightening keyed from source with fixed foot anchors'}],'assembly_summary':'A rigid hinged plank lifts its rider, pauses near the observed high reversal, and returns. One wooded setting and parallel equipment remain held; nearer context occludes the low rider.','training_ran':False,'motion_approved':False,'train_eligible':False,'sam':'Available but combines distinct boards; not a valid single-instance fit target.'}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'correspondence.json').write_text(json.dumps({'original_strokes':4,'assignment':{'0':'hinged plank point mark','1':'hinged plank outline','2':'fixed support point mark','3':'fixed support outline'},'all_frames_same_topology':True,'board_3d_length':2*HALF,'fulcrum':PIVOT.tolist()},indent=2)+'\n')
 trace_result=trace_character_keys()
 checks={'trace':trace_result,'xsheet_covers_every_frame':True,'background_stroke_geometry_unchanged_fraction':1.,'every_frame_rendered':N,'source_sha256_verified':True,'integrated_keys':len(keys),'original_strokes_assigned':4,'held_background_geometry':True,'board_3d_length_variation_fraction':0.,'fixed_fulcrum_drift_pixels':0.,'source_angle_estimation':'manual observations; not a calibrated 3D reconstruction','SAM':'SAM2.1 output inspected; mixed-instance segmentation unsuitable for single-board mask-fit gate','numeric_source_mask_fit':'not measured','recognition':'not run','planted_contacts_observed':0,'foot_slide_gate':'not passed; zero planted intervals measured','independent_playback':'not run','release_approved':False,'training_ran':False}
 (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 validation={}
 for name in ['cartoon.mp4','source-excerpt.mp4','comparison.mp4']:
  c=cv2.VideoCapture(str(OUT/name));fps=c.get(cv2.CAP_PROP_FPS);n=0
  while c.read()[0]:n+=1
  c.release();assert n==N;validation[name]={'decoded_frames':n,'fps':fps,'complete':True,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest(),'bytes':(OUT/name).stat().st_size}
 (OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
 print(json.dumps({'frames':N,'keys':len(keys),'duration':N/FPS,'output':str(OUT)}))
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,default=SOURCE);ap.add_argument('--sam-cache',type=Path,default=CACHE);a=ap.parse_args();SOURCE=a.source.expanduser().resolve();CACHE=a.sam_cache.expanduser().resolve();main()
