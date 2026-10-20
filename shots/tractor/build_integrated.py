"""Source-framed tractor approach: original five doodle strokes, observed pose keys.
Driver, trailer and depth-side wheel copies are explicitly agent-authored context.
No SAM, learned in-betweening, classifier or training is claimed.
"""
from pathlib import Path
import cv2,numpy as np,json,math,hashlib,subprocess,os,shutil,argparse,tempfile
from PIL import Image,ImageDraw
import cairosvg
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
LOCAL_SOURCE=ROOT.parents[2]/'wave2-logs'/'tractor.mp4'
SOURCE=Path(os.environ.get('SECONDHAND_MOTION_SOURCE',str(LOCAL_SOURCE)))
FPS=24;START=.5;END=2.45;N=math.ceil((END-START)*FPS)
D=json.loads((ROOT/'design.json').read_text());ST=[np.array(list(zip(s[0],s[1])),dtype=float) for s in D['drawing']]
# Anchors observed on the actual source frames in 320x240 coordinates.
OBS=[
 {'t':.5,'rear':[173,136,16,25],'front':[125,154,11,16],'hood':[120,109,164,112,163,139,117,134],'exhaust':[124,108,125,79],'head':[154,87],'trailer':[183,110,230,111,225,129,185,134],'trailer_wheel':[211,144,6,13],'horizon':112},
 {'t':.9,'rear':[183,145,19,29],'front':[119,161,13,18],'hood':[116,106,174,111,171,141,113,136],'exhaust':[121,106,123,72],'head':[160,84],'trailer':[201,111,260,112,253,134,204,142],'trailer_wheel':[232,153,7,14],'horizon':109},
 {'t':1.3,'rear':[194,147,23,35],'front':[111,171,17,20],'hood':[103,101,179,108,177,145,99,139],'exhaust':[115,100,117,63],'head':[169,80],'trailer':[216,110,284,112,277,140,216,148],'trailer_wheel':[253,159,8,16],'horizon':109},
 {'t':1.7,'rear':[208,157,33,43],'front':[92,181,23,26],'hood':[83,96,191,102,187,147,78,145],'exhaust':[101,94,104,48],'head':[182,67],'trailer':[238,111,319,114,318,148,238,157],'trailer_wheel':[282,169,10,18],'horizon':104},
 {'t':2.1,'rear':[220,160,46,52],'front':[62,184,27,32],'hood':[48,87,189,95,183,144,43,142],'exhaust':[80,85,82,28],'head':[203,54],'trailer':[265,113,340,116,340,159,264,165],'trailer_wheel':[317,182,12,20],'horizon':85},
 {'t':2.45,'rear':[224,158,57,61],'front':[22,182,35,34],'hood':[0,81,178,88,169,132,-4,135],'exhaust':[74,80,78,17],'head':[228,43],'trailer':[284,113,380,117,375,159,285,162],'trailer_wheel':[354,185,14,22],'horizon':86}]
INTERP={k:PchipInterpolator([x['t'] for x in OBS],[x[k] for x in OBS]) for k in OBS[0] if k!='t'}
BG=[[[0,108],[75,110],[151,109],[229,111],[320,113]],[[0,129],[58,128],[101,125]],[[240,126],[283,126],[320,123]],[[0,182],[54,161],[105,144],[160,128],[229,119],[320,117]],[[26,240],[79,204],[124,170],[165,141],[228,122],[320,117]],[[0,222],[14,211],[25,214]],[[18,190],[27,186],[33,188]],[[271,180],[280,175],[291,180]],[[233,212],[241,205],[249,207]],[[288,235],[299,226],[311,228]]]
# Sparse field marks are a single held drawing, transformed by observed horizon shift.
for x,y in [(170,207),(186,190),(202,174),(215,218),(238,190),(257,224),(279,204),(305,186),(139,230),(116,220),(221,153),(300,146)]:
 BG.extend([[[x-4,y],[x,y-10],[x+1,y]],[[x,y],[x+6,y-7]],[[x,y],[x-7,y-4]]])

def pts(a):return ' '.join(f'{float(x):.3f},{float(y):.3f}' for x,y in a)
def line(a,w=1.35,c='#24211d'):return f'<polyline points="{pts(a)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def poly(a,w=1.35):return f'<polygon points="{pts(a)}" fill="#fffdf7" stroke="#24211d" stroke-width="{w}" stroke-linejoin="round"/>'
def ellipse(cx,cy,rx,ry,w=1.1):return f'<ellipse cx="{cx:.3f}" cy="{cy:.3f}" rx="{rx:.3f}" ry="{ry:.3f}" fill="#fffdf7" stroke="#24211d" stroke-width="{w}"/>'
def wheel(s,a):
 cx,cy,rx,ry=a;mn=s.min(0);mx=s.max(0);return (s-(mn+mx)/2)/(mx-mn)*[2*rx,2*ry]+[cx,cy]
def hoodmap(s,a):
 H=cv2.getPerspectiveTransform(np.float32([[3,48],[141,52],[148,124],[10,126]]),np.float32(np.array(a).reshape(4,2)))
 return cv2.perspectiveTransform(np.float32(s).reshape(1,-1,2),H)[0]
def snapshot(t,f):
 A={k:np.array(v(t)).tolist() for k,v in INTERP.items()};rear=A['rear'];front=A['front'];hood=np.array(A['hood']).reshape(4,2);ex=A['exhaust'];head=A['head'];tr=np.array(A['trailer']).reshape(4,2)
 bgdy=A['horizon']-112;bg=''.join(line(np.array(s)+[0,bgdy],.75,'#80776a') for s in BG)
 # Trailer is drawn behind the tractor; one original small-wheel contour is reused for its wheel.
 trailer=poly(wheel(ST[0],A['trailer_wheel']),1.05)+poly(tr,1.05)
 for q in [.2,.4,.6,.8]:trailer+=line([tr[0]*(1-q)+tr[1]*q,tr[3]*(1-q)+tr[2]*q],.85)
 trailer+=line([tr[3],np.array([rear[0]+rear[2]*.5,rear[1]+rear[3]*.45])],1.2)
 # Depth-side wheels become less separated as the tractor reaches a profile view.
 yaw=float(np.clip((t-START)/(END-START),0,1));sep=14*(1-yaw)+8
 farrear=[rear[0]-rear[2]*1.55,rear[1]+5,rear[2]*.60,rear[3]*.85]
 farfront=[front[0]-sep,front[1]-5,front[2]*.74,front[3]*.94]
 far=poly(wheel(ST[2],farrear),1.05)+poly(wheel(ST[0],farfront),1.0)
 body=poly(hoodmap(ST[1],A['hood']),1.4)
 # Hood front face exposes the view change that a flat size-only scaling loses.
 depth=(1-yaw)*max(4,float(hood[1,0]-hood[0,0])*.20)
 face=[hood[0],hood[0]+[-depth,3],hood[3]+[-depth,3],hood[3]]
 body+=poly(face,1.1)
 # Preserve bent exhaust's source stroke, separately mapped to observed height.
 s=ST[4];sx=(s[:,0]-19)/11;sy=(s[:,1]-54)/54
 exhaust=np.c_[ex[0]+sx*max(2,(ex[1]-ex[3])*.065),ex[1]+sy*(ex[1]-ex[3])]
 body+=line(exhaust,1.45)
 # Original seat/back stroke remains connected to the rear wheel region, without turning it into a mast.
 seat=hoodmap(ST[3],A['hood']);seat[:,1]=np.maximum(seat[:,1],head[1]+20);body+=line(seat,1.15)
 # Agent-authored seated driver follows source head, shoulders and steering wheel placement.
 sc=rear[3]/25;hx,hy=head;hand=np.array([hx-9*sc,hy+16*sc]);hip=np.array([rear[0]-4*sc,rear[1]-13*sc]);shoulder=np.array([hx+2*sc,hy+9*sc])
 driver=poly([[hx-3*sc,hy-4*sc],[hx+4*sc,hy-4*sc],[hx+5*sc,hy+3*sc],[hx,hy+6*sc],[hx-3*sc,hy+2*sc]],.9)
 driver+=line([[hx-7*sc,hy-4*sc],[hx+8*sc,hy-4*sc]],1.1)+line([[hx-4*sc,hy-5*sc],[hx-3*sc,hy-8*sc],[hx+4*sc,hy-8*sc],[hx+5*sc,hy-4*sc]],1.0)
 driver+=poly([shoulder,shoulder+[5*sc,7*sc],hip+[3*sc,0],hip+[-7*sc,0],shoulder+[-5*sc,0]],.95)
 driver+=line([shoulder+[0,3*sc],hand+[4*sc,4*sc],hand],1.1)+ellipse(hand[0]-3*sc,hand[1],5*sc,5*sc,.85)
 driver+=line([hip+[-5*sc,0],hip+[-12*sc,7*sc],hip+[-7*sc,15*sc]],1.1)
 near=poly(wheel(ST[2],rear),1.5)+poly(wheel(ST[0],front),1.4)
 # Wheel hubs/spokes are observed context, authored in the same spare line vocabulary.
 angle=-2*math.pi*(t-START)*.65
 for cx,cy,rx,ry in [rear,front]:
  near+=ellipse(cx,cy,rx*.22,ry*.22,.8)
  for phase in [0,2.094,4.189]:
   p=angle+phase;near+=line([[cx+rx*.24*math.cos(p),cy+ry*.24*math.sin(p)],[cx+rx*.70*math.cos(p),cy+ry*.70*math.sin(p)]],.85)
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="#fffdf7"/>'+bg+trailer+far+body+driver+near+'</svg>'
 return svg,A

def main():
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==json.loads((ROOT/'source.json').read_text())['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));srcfps=cap.get(cv2.CAP_PROP_FPS)
 td=Path(tempfile.mkdtemp(prefix='secondhand-motion-tractor-'))
 keys=[0,10,19,29,38,N-1];frames=[]
 for f in range(N):
  t=START+f/FPS;idx=round(t*srcfps);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  source=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  svg,A=snapshot(t,f);cairosvg.svg2png(bytestring=svg.encode(),write_to=str(td/'frame.png'));cartoon=Image.open(td/'frame.png').convert('RGB')
  cartoon.save(td/f'cartoon-{f:03d}.ppm');source.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair);pen.text((10,6),f'ARCHIVE | {t:.3f} s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | observed approach and crop',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
  frames.append({'f':f,'time':f/FPS,'source_time':t,'source_frame_index':idx,'source_index_time':idx/srcfps,'anchors':A})
  if f in keys:
   k=keys.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');source.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg)
  if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
 cap.release()
 for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-preset','slow','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/name)],check=True)
  subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(OUT/name),'-f','null','-'],check=True)
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="#fffdf7"/>'+''.join(line(s,.75,'#80776a') for s in BG)+'</svg>')
 shutil.copy(ROOT/'design.json',OUT/'design.json');shutil.copy(ROOT/'design.png',OUT/'design.png')
 shot={'title':'Tractor comes around the bend','status':'assembled_candidate_review_pending','revision':'integrated-v1','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,'keys':keys,'source':json.loads((ROOT/'source.json').read_text()),'design':D,'source_anchors':OBS,'frames':frames,'xsheet':[{'f':f,'kind':'K','note':n} for f,n in zip(keys,['Distant oblique approach; far wheels exposed.','Near wheel grows as tractor approaches.','Driver and trailer remain behind the hood.','Near pass opens hood side face.','Large rear wheel dominates; front nears left edge.','Near profile and authentic left-edge crop.'])],
 'planes':[{'id':'field','source':'drawn by agent once from archive field, y translation estimated from horizon','strokes':BG},{'id':'trailer','source':'drawn by agent against source anchors'},{'id':'tractor','source':'original QuickDraw five strokes, independently posed by part'},{'id':'driver','source':'drawn by agent; omitted from original doodle but visible in source'}],
 'camera':{'method':'manual horizon observations; PCHIP y-shift only','measured_3d_pan':False,'depth_parallax':'not inferred'},'wheel_rotation':{'method':'authored hub/spoke phase; source RPM not measured','revolutions_per_second':.65},
 'assembly_summary':'The source approach, growing wheels, changing hood projection, driver, trailer and left-edge crop are assembled over one field drawing. Wheel spoke phase is authored; final playback review is pending.',
 'training_ran':False,'motion_approved':False,'train_eligible':False}
 (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n')
 tests={'rendered_frames':N,'fps':FPS,'keys':len(keys),'full_decode':True,'source_sha256_verified':True,'all_original_doodle_strokes_assigned':True,'original_strokes':5,'same_topology_all_frames':True,'background_single_geometry':True,'background_transform':'observed horizon y-shift','classifier':'not run','SAM':'not run','mask_fit':'not measured','recognition':'not run','trace_fidelity':'native vectors; raster tracer not run','foot_slide':'not measured; wheels are moving, not planted feet','independent_playback':'not run','release_approved':False,'training_ran':False}
 (OUT/'assembly-checks.json').write_text(json.dumps(tests,indent=2)+'\n')
 print(json.dumps({'frames':N,'keys':len(keys),'duration':N/FPS,'output':str(OUT)}))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,default=SOURCE,help='Downloaded source clip; defaults to SECONDHAND_MOTION_SOURCE or a sibling wave2-logs/tractor.mp4')
 args=parser.parse_args();SOURCE=args.source.expanduser().resolve()
 main()
