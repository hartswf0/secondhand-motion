"""Verify the concrete movie/key correspondence, counts, links and ledger; no playback judgment."""
from pathlib import Path
import json,hashlib,subprocess,re,importlib.util
from html.parser import HTMLParser
import cv2,numpy as np
from PIL import Image
R=Path(__file__).resolve().parent;D=R/'integrated';s=json.loads((D/'shot.json').read_text());N=s['frame_count'];assert len(s['frames'])==N;assert all('source_time'in f for f in s['frames']);assert not list(D.rglob('*.tmp.mp4'));assert not list(D.glob('.cow-render-*'))
assert len(s['frames'][0]['cast'][0]['strokes'])==17
sourcepointcounts=[len(q[0])for q in s['design']['drawing']]
for f in s['frames']:assert[len(q)for q in f['cast'][0]['strokes']]==sourcepointcounts
class Links(HTMLParser):
 def __init__(self):super().__init__();self.urls=[]
 def handle_starttag(self,t,attrs):self.urls +=[v for k,v in attrs if k in('href','src','poster')and v]
p=Links();html=(D/'index.html').read_text();p.feed(html);external_pending=[]
for url in p.urls:
 if url.startswith(('http:','https:','#','data:','mailto:')):continue
 target=D/url.split('#')[0].split('?')[0]
 if target.name=='moving-drawings.html'and not target.exists():external_pending.append(url);continue
 assert target.exists(),url
for js in re.findall(r'<script>(.*?)</script>',html,re.S):
 r=subprocess.run(['node','-e','new Function('+json.dumps(js)+')'],capture_output=True,text=True);assert r.returncode==0,r.stderr
movieaudit={};keyaudit=[]
for name in['cartoon.mp4','source-excerpt.mp4','comparison.mp4']:
 path=D/name;cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);count=0
 while True:
  ok,frame=cap.read()
  if not ok:break
  if name in ['cartoon.mp4','comparison.mp4']and count in s['keys']:
   k=s['keys'].index(count)+1;expected=np.asarray(Image.open(D/f'key-{k:02d}.png').convert('RGB'),dtype=float);actual=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
   if name=='comparison.mp4':actual=actual[24:,480:]
   mae=float(np.abs(actual.astype(float)-expected).mean());assert mae<2.0,(name,k,mae);keyaudit.append({'movie':name,'key':k,'frame':count,'mean_absolute_RGB_difference':mae,'interpretation':'Expected lossy h264 difference from exact final key PNG; not a motion quality gate'})
  count+=1
 cap.release();assert count==N and fps==24,(name,count,fps)
 subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(path),'-f','null','-'],check=True)
 movieaudit[name]={'decoded_frames':count,'fps':fps,'complete':True,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
boards=[]
for start,stop,name in[(1,7,'paired-keys-01.jpg'),(7,11,'paired-keys-02.jpg')]:
 board=np.asarray(Image.open(D/name).convert('RGB'),dtype=float)
 for j,k in enumerate(range(start,stop)):
  x=j%2*480+240;y=j//2*204+24;actual=board[y:y+180,x:x+240];expected=np.asarray(Image.open(D/f'key-{k:02d}.png').convert('RGB').resize((240,180)),dtype=float);mae=float(np.abs(actual-expected).mean());assert mae<4,(name,k,mae);boards.append({'board':name,'key':k,'mean_absolute_RGB_difference':mae})
spec=importlib.util.spec_from_file_location('loop',R.parents[1]/'batches/2026-10-20-selected-drawings/loop.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with(R/'ledger.jsonl').open()as f:entries=m.read_ledger(f)
for path in R.rglob('*.json'):json.loads(path.read_text())
(D/'movie-key-audit.json').write_text(json.dumps({'movies':movieaudit,'movie_key_correspondence':keyaudit,'paired_board_key_correspondence':boards,'scope':'All current movies decoded completely and checked at every key index; does not approve actual normal-speed motion. Paired boards regenerated from unchanged final individual key PNGs after the v2 reviewer found a stale board cell.','local_player_links_checked':len(p.urls),'pending_shared_gallery':external_pending,'ledger_entries_verified':len(entries),'all_original_stroke_point_counts_preserved':True},indent=2)+'\n')
(D/'video-validation.json').write_text(json.dumps(movieaudit,indent=2)+'\n')
print(json.dumps({'movie_counts':{k:v['decoded_frames']for k,v in movieaudit.items()},'keys_verified':len(keyaudit),'board_cells_verified':len(boards),'max_movie_key_MAE':max(x['mean_absolute_RGB_difference']for x in keyaudit),'ledger_entries':len(entries),'pending_shared_gallery':external_pending,'movies':movieaudit},indent=2))
