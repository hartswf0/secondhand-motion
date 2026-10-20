from pathlib import Path
from PIL import Image,ImageDraw
import json,cv2
R=Path(__file__).resolve().parent;choices={'cat':16,'dog':9,'horse':23,'rabbit':6,'butterfly':27,'duck':19,'bicycle':9,'windmill':28,'helicopter':8}
for cat,i in choices.items():
 f=R/'subjects'/cat;records=[json.loads(x) for x in (f/'quickdraw.ndjson').read_text().splitlines()];q=records[i];(f/'design.json').write_text(json.dumps(q,indent=2));im=Image.new('RGB',(512,512),'white');d=ImageDraw.Draw(im)
 for stroke in q['drawing']:
  pts=[(35+a*1.7,25+b*1.7) for a,b in zip(*stroke)]
  if len(pts)>1:d.line(pts,fill='black',width=4)
 im.save(f/'design.png');meta=json.loads((f/'source.json').read_text());meta['design_selection']={'bank_index':i,'key_id':q['key_id'],'method':'GPT visual selection from 32 actual recognized QuickDraw samples; no model quality score.'}
 if cat=='cat':
  meta['key_times'][-1]=15.3;cap=cv2.VideoCapture(str(R.parent/'mia-quickdraw-dataset'/meta['source']['local_video_path']));cap.set(cv2.CAP_PROP_POS_MSEC,15300);ok,fr=cap.read();assert ok;Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)).resize((384,288)).save(f/'source-key-3.png');cap.release()
  grid=Image.new('RGB',(768,576),'white')
  for k in range(4):grid.paste(Image.open(f/f'source-key-{k}.png'),(k%2*384,k//2*288))
  grid.save(f/'source-keys.png')
 (f/'source.json').write_text(json.dumps(meta,indent=2))
p=R/'prepare.py';p.write_text(p.read_text().replace('14.0,16.2','14.0,15.3'))
t=json.loads((R/'data/targets.json').read_text());t['cat'][-1]=15.3;(R/'data/targets.json').write_text(json.dumps(t,indent=2))
print('9 designs selected; cat dissolve excluded')
