from pathlib import Path
from PIL import Image,ImageOps
from io import BytesIO
import base64,json
R=Path(__file__).resolve().parent
items=json.loads((R/'data/curation.json').read_text())['items']
def jpg(im,size,q):
 b=BytesIO();ImageOps.pad(im.convert('RGB'),size,color='white').save(b,format='JPEG',quality=q,optimize=True);return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
def cells(path,size,q):
 im=Image.open(path);w,h=im.size;return[jpg(im.crop((x*w//2,y*h//2,(x+1)*w//2,(y+1)*h//2)),size,q) for y in range(2) for x in range(2)]
for size,q in [((256,192),64),((224,168),58),((192,144),52)]:
 out=[]
 for item in items:
  f=R/'subjects'/item['category'];s=json.loads((f/'source.json').read_text());v=item['selected_revision']
  out.append({'title':item['category'].title(),'category':item['category'],'times':s['key_times'],'hero':item['hero_key'],'note':item['note'],'photos':cells(f/'source-keys.png',(192,144),58),'first':cells(f/'revisions/keys-v1.png',size,q),'selected':cells(f/f'revisions/keys-{v}.png',size,q)})
 encoded=json.dumps({'items':out},separators=(',',':'))
 if len(encoded)<950000:break
p=Path('/workspace/cartoon-archive-selected-drawings.html');t=(R/'inline-template.html').read_text() if (R/'inline-template.html').exists() else p.read_text();assert '__DRAWING_DATA__' in t;(R/'inline-template.html').write_text(t);p.write_text(t.replace('__DRAWING_DATA__',encoded));(R/'data/inline-data.json').write_text(encoded);print('Inline fragment',p.stat().st_size,'bytes',size,q)
