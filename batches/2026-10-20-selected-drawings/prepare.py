from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw
import json,urllib.request,cv2,shutil
R=Path(__file__).resolve().parent;D=R.parent/'mia-quickdraw-dataset';P=R.parent/'cartoon-archive-pilot/data/quickdraw'
rows={r['category']:r for r in json.loads((R/'data/probe-sources.json').read_text())}
targets={'cat':[10.4,12.2,14.0,15.3],'dog':[.2,1.4,2.8,4.0],'horse':[4.3,5.5,6.4,7.5],'rabbit':[4.8,5.8,7.,8.8],'butterfly':[9.2,10.8,12.6,15.4],'duck':[.1,1.1,2.2,3.8],'bicycle':[1.9,2.4,2.9,3.4],'windmill':[.3,1.6,3.,4.4],'helicopter':[.2,1.4,2.6,3.8]}
def prep(cat):
 folder=R/'subjects'/cat;folder.mkdir(parents=True,exist_ok=True);(folder/'revisions').mkdir(exist_ok=True)
 q=rows[cat];meta={'category':cat,'source':q,'key_times':targets[cat],'selection_scope':'Chosen by GPT temporal-sample review from 24 downloaded candidate clips, not an exhaustive global best.','review_scope':'sampled frames only; not normal-speed playback','state':'awaiting drawing and independent key review'}
 (folder/'source.json').write_text(json.dumps(meta,indent=2))
 bank=folder/'quickdraw.ndjson'
 if not bank.exists():
  if (P/(cat+'.ndjson')).exists():shutil.copy2(P/(cat+'.ndjson'),bank)
  else:
   url='https://storage.googleapis.com/quickdraw_dataset/full/simplified/'+cat+'.ndjson'
   with urllib.request.urlopen(url,timeout=60) as stream,bank.open('w') as f:
    n=0
    for line in stream:
     d=json.loads(line)
     if d['recognized'] and 2<=len(d['drawing'])<=30:
      f.write(json.dumps(d)+'\n');n+=1
      if n==48:break
 records=[json.loads(x) for x in bank.read_text().splitlines()][:32]
 sheet=Image.new('RGB',(1024,512),'white');draw=ImageDraw.Draw(sheet)
 for i,d in enumerate(records):
  x=i%8*128;y=i//8*128
  for stroke in d['drawing']:
   pts=[(x+8+a*.40,y+5+b*.40) for a,b in zip(*stroke)]
   if len(pts)>1:draw.line(pts,fill='black',width=2)
  draw.text((x+5,y+112),str(i),fill='black')
 sheet.save(folder/'doodle-bank.jpg')
 cap=cv2.VideoCapture(str(D/q['local_video_path']));sheet=Image.new('RGB',(768,576),'white')
 for i,t in enumerate(targets[cat]):
  cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,fr=cap.read();assert ok,(cat,t)
  im=Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)).resize((384,288));im.save(folder/f'source-key-{i}.png');sheet.paste(im,(i%2*384,i//2*288))
 cap.release();sheet.save(folder/'source-keys.png');return cat
with ThreadPoolExecutor(max_workers=3) as ex:
 for cat in ex.map(prep,targets):print(cat,flush=True)
(R/'data/targets.json').write_text(json.dumps(targets,indent=2))
