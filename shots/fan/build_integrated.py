"""Assemble a source-framed fan performance from original doodle strokes.
The rotor speed is authored; source blur does not establish exact RPM.
Usage: python shots/fan/build_integrated.py --source /path/to/fan.mp4
The source.json video_url identifies the input; its SHA-256 is checked before rendering.
"""
from pathlib import Path
import json,math,hashlib,subprocess
import cv2,numpy as np,cairosvg
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'integrated';OUT.mkdir(exist_ok=True)
SOURCE=Path('/workspace/scratch/e78c43b4722d/wave2-logs/fan.mp4')
FPS=24;START=1.2;END=4.3043;N=math.ceil((END-START)*FPS)
D=json.loads((OUT/'design.json').read_text());ST=[list(zip(s[0],s[1])) for s in D['drawing']]
# Hand-placed source anchors in the actual 320x240 camera frame, not a recentered model sheet.
ANCHORS={'cage':[73,10,254,212],'hub':[162,119],'stand_base':[143,236,188,239],
 'bowl':[9,178,85,224],'books':[234,209,320,240]}
# Source-framed background, drawn once as sparse native vector line art.
BG=[[[3,0],[3,188]],[[66,0],[65,186]],[[122,0],[121,183]],[[185,0],[185,186]],[[249,0],[249,193]],[[316,0],[316,194]],
 [[0,185],[68,184]],[[252,193],[319,194]],[[0,218],[75,215],[115,221]],[[201,220],[243,226],[319,238]],
 [[10,184],[22,179],[43,177],[65,180],[83,185],[76,193],[57,198],[33,197],[15,192],[10,184]],
 [[10,185],[16,208],[27,219],[45,224],[62,221],[75,212],[83,185]],
 [[22,184],[25,188],[28,185]],[[41,180],[42,186],[47,184]],[[59,185],[65,189]],
 [[235,209],[274,212],[319,224],[319,237],[272,226],[235,221],[235,209]],
 [[245,215],[276,218],[311,229]],[[238,222],[273,229],[312,240]],[[273,213],[273,225]],[[283,216],[283,228]]]

def points(s):return ' '.join(f'{x:.3f},{y:.3f}' for x,y in s)
def line(s,width=1.3,color='#201d19'):return f'<polyline points="{points(s)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'
HEAD_SHIFT=(0.,0.)
def mapped(s,part,angle=0):
 pts=[]
 for x,y in s:
  if part=='stand':p=[165+(x-117)*.85,111+(y-109)*.85]
  else:
   dx=x-118;dy=y-109
   if part=='rotor':dx,dy=dx*math.cos(angle)-dy*math.sin(angle),dx*math.sin(angle)+dy*math.cos(angle)
   depth=1.0 if part in ('rotor','hub') else .55
   offset=12.5 if part in ('rotor','hub') else 0.0
   p=[162+HEAD_SHIFT[0]*depth+dx*.78,111+HEAD_SHIFT[1]+dy*.90+offset]
  pts.append(p)
 return pts

def frame_svg(angle):
 bg=''.join(line(s,1.05,'#514a40') for s in BG)
 cage=mapped(ST[4],'cage');rotor=line(mapped(ST[3],'rotor',angle),1.5)
 stand=''.join(line(mapped(ST[i],'stand'),1.45) for i in (0,1))
 hub=mapped(ST[2],'hub');wires=line(mapped(ST[5],'cage'),1.1)
 outline='<polygon points="'+points(cage)+'" fill="#fffdf7"/>'
 return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><defs><clipPath id="cage"><polygon points="'+points(cage)+'"/></clipPath></defs><rect width="320" height="240" fill="#fffdf7"/>'+bg+stand+outline+'<g clip-path="url(#cage)">'+rotor+'</g>'+wires+line(cage,1.6)+'<polygon points="'+points(hub)+'" fill="#fffdf7"/>'+line(hub,1.4)+'</svg>'

def main():
 global HEAD_SHIFT
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==json.loads((ROOT/'source.json').read_text())['source_sha256']
 cap=cv2.VideoCapture(str(SOURCE));srcfps=cap.get(cv2.CAP_PROP_FPS)
 keys=[1,15,30,45,59,74];xs=[];frames=[];static=[];held_hash=[]
 cap.set(cv2.CAP_PROP_POS_FRAMES,round(START*srcfps));ok,reference=cap.read();assert ok
 template=cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY)[112:128,90:222]
 import tempfile
 td=Path(tempfile.mkdtemp(prefix='secondhand-motion-fan-'))
 for f in range(N):
  t=f/FPS;source_time=START+t;idx=round(source_time*srcfps)
  cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,bgr=cap.read();assert ok
  gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY);match=cv2.matchTemplate(gray[106:136,70:270],template,cv2.TM_CCOEFF_NORMED);_,confidence,_,pos=cv2.minMaxLoc(match)
  HEAD_SHIFT=(float(pos[0]-20),float(pos[1]-6))
  source=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((480,360),Image.Resampling.LANCZOS)
  # One slow readable procedural revolution rate; it is not an RPM estimate.
  angle=2*math.pi*4*f/N
  svg=frame_svg(angle);p=td/f'cartoon-{f:03d}.png';cairosvg.svg2png(bytestring=svg.encode(),write_to=str(p))
  cartoon=Image.open(p).convert('RGB');cartoon.save(td/f'cartoon-{f:03d}.ppm');source.save(td/f'source-{f:03d}.ppm')
  pair=Image.new('RGB',(960,384),'#f5f1e8');pair.paste(source,(0,24));pair.paste(cartoon,(480,24));pen=ImageDraw.Draw(pair)
  pen.text((10,6),'ARCHIVE | '+format(source_time,'.3f')+' s',fill='#171512');pen.text((490,6),'ASSEMBLED CARTOON | procedural rotor phase',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
  frames.append({'f':f,'time':t,'source_time':source_time,'source_frame_index':idx,'source_index_time':idx/srcfps,'rotor_angle':angle,'head_shift':list(HEAD_SHIFT),'head_template_match_ncc':confidence})
  xs.append({'f':f,'kind':'K' if f in keys else 'B','note':'Running fan: head pivots slowly on stationary stand while blades rotate. Rotor phase authored.' if f in keys else ''})
  if f in keys:
   k=keys.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');source.save(OUT/f'source-{k:02d}.jpg',quality=90);(OUT/f'key-{k:02d}.svg').write_text(svg)
  if f==0:
   cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=90)
 cap.release()
 for stem,out in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
  subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-preset','slow','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/out)],check=True)
 (OUT/'background.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 320 240"><rect width="320" height="240" fill="#fffdf7"/>'+''.join(line(s,1.05,'#514a40') for s in BG)+'</svg>')
 data={'title':'Fan in its room','status':'assembled_candidate_review_pending','assembly_summary':'A held room and stand, a source-tracked head turn, and authored rotor motion.','W':480,'H':360,'fps':FPS,'frame_count':N,'duration':N/FPS,
  'source':json.loads((ROOT/'source.json').read_text()),'design':D,'revision':'integrated-v2','source_anchors':ANCHORS,
  'planes':[{'id':'background','source':'drawn by agent against source frame 36, held once','strokes':BG},{'id':'rotor','source_strokes':[3]},{'id':'housing','source_strokes':[4,5]},{'id':'hub','source_strokes':[2]},{'id':'stand','source_strokes':[0,1]}],
  'source_registration':{'method':'manual source-frame anchors; different part mappings for cage and stand','coordinates':[320,240],'automatic_registration':'not run','camera':'background held; LK/RANSAC first-to-last background shift measured separately under2px','head_depth_mapping':'cage horizontal shift .55 times frontal-hub shift; manually inferred yaw projection; hub/rotor offset 12.5px','head_motion':'black crossbar template registration per decoded source frame; correlation scores retained, not probabilities'},
  'phase':{'method':'procedural constant angular speed','revolutions_per_second':4/(N/FPS),'loop_revolutions':4,'source_rpm_measured':False},'frames':frames,'xsheet':xs,'keys':keys,
  'render_files':['cartoon.mp4','comparison.mp4','source-excerpt.mp4'],'training_ran':False,'motion_approved':False}
 (OUT/'shot.json').write_text(json.dumps(data,indent=2)+'\n')
 tests={'frame_count':N,'every_frame_rendered':all((td/f'cartoon-{f:03d}.png').exists() for f in range(N)),
  'held_geometry':{'background':True,'housing':False,'stand':True,'hub':False,'method':'background and stand fixed; head cage, wires and hub receive one shared source-derived transform; rotor additionally rotates'},
  'all_original_doodle_strokes_assigned':set([0,1,2,3,4,5])==set(range(len(ST))),
  'rotor_moves':len({round(x['rotor_angle'],6) for x in frames})==N,'six_integrated_keys':len(keys),
  'source_decode_sha256_verified':True,'source_frame_matches_numeric':'not measured','recognition':'not run','SAM':'not run','independent_playback':'not run','release_approved':False}
 (OUT/'assembly-checks.json').write_text(json.dumps(tests,indent=2)+'\n')
 print(json.dumps({'frames':N,'duration':N/FPS,'keys':len(keys),'output':str(OUT)}))
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,default=SOURCE,help='Downloaded archive clip; see source.json video_url')
 SOURCE=parser.parse_args().source
 main()

