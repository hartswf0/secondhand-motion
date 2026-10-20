from pathlib import Path
import csv,cv2,json
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;D=R.parent/'mia-quickdraw-dataset'
categories=['cat','dog','frog','horse','rabbit','butterfly','fish','duck','bicycle','train','windmill','helicopter','tiger','bear','kangaroo','lion','owl','sea turtle','squirrel','snake','guitar','drums','giraffe','bird']
rows=list(csv.DictReader(open(D/'candidates.csv')));selected=[]
for cat in categories:
 q=next((q for q in rows if q['category']==cat and q['local_video_path'] and (D/q['local_video_path']).exists()),None)
 if q:selected.append(q)
(R/'data/probe-sources.json').write_text(json.dumps(selected,indent=2))
for page in range((len(selected)+5)//6):
 sheet=Image.new('RGB',(1536,6*220),'white');draw=ImageDraw.Draw(sheet)
 for row,q in enumerate(selected[page*6:(page+1)*6]):
  cap=cv2.VideoCapture(str(D/q['local_video_path']));dur=cap.get(7)/cap.get(5)
  for col,fraction in enumerate([.02,.18,.36,.54,.72,.90]):
   t=dur*fraction;cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,fr=cap.read()
   if ok:
    im=Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB));im.thumbnail((256,185));sheet.paste(im,(col*256,row*220));draw.text((col*256+5,row*220+189),f'{q["category"]} {t:.2f}s',fill='black')
  draw.text((5,row*220+205),q['source_title'][:130],fill='black');cap.release()
 sheet.save(R/f'references/probe-{page}.jpg')
print(len(selected),'clips inspected by temporal samples')
