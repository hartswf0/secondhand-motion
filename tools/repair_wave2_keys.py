"""Bounded key repairs. Keep original rejected revisions and exact source references."""
import json, math, shutil
from pathlib import Path
from PIL import Image, ImageOps
import cairosvg
import trace_keys
ROOT=Path(__file__).resolve().parent.parent

def save(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def retrace(d,revision):
 plan=json.loads((d/'keyplan.json').read_text());plan['revision']=revision
 entry={'W':512,'H':384,'revision':revision,'keys':[],'correspondence_established':d.name=='see-saw'}
 proof=Image.new('RGB',(1024,1152),'white')
 for i in range(6):
  p=d/'keys'/f'key-{i+1:02d}.png';im=Image.open(p).convert('RGB')
  st,ink,hw=trace_keys.trace(im);r,pr,parts=trace_keys.score(st,ink,512,384,hw)
  entry['keys'].append({'file':'keys/'+p.name,'time':plan['keys'][i]['time'],'n_strokes':len(st),'points':sum(len(s) for s in st),'strokes':st,'recall':r,'precision':pr,'parts_kept':parts,'half_width':hw})
  proof.paste(im,((i%2)*512,(i//2)*384))
 save(d/'keys/traced.json',entry);proof.save(d/'keys'/f'proof-{revision}.jpg',quality=90)
 save(d/'keyplan.json',plan)
 tests=json.loads((d/'tests.json').read_text());ok=all(k['recall']>=.98 and k['parts_kept']==1 for k in entry['keys'])
 for t in tests:
  if t['id']=='T1':t.update(value={'min_recall':min(k['recall'] for k in entry['keys']),'min_parts_kept':min(k['parts_kept'] for k in entry['keys']),'keys':6},unit='fraction',ok=ok)
 save(d/'tests.json',tests)
 gates=json.loads((d/'keys/gates.json').read_text());gates.update(revision=revision,identity_critic='pending');gates['trace']['all_keys_pass']=ok;save(d/'keys/gates.json',gates)
 print(d.name,revision,'min recall',min(k['recall'] for k in entry['keys']),flush=True)

def board_repair(slug,revision=None):
 if revision is None:revision='v3' if (ROOT/'shots'/slug/'keys/revisions/board-v3.png').exists() else 'v2'
 d=ROOT/'shots'/slug;im=Image.open(d/('keys/revisions/board-'+revision+'.png')).convert('RGB');W,H=im.size
 rows=[0,H/4,H/2,3*H/4,H]
 if slug=='raccoon' and H==1390:rows=[0,340,680,970,H]
 boxes=[]
 for i in range(6):
  box=[round(i%2*W/2)+7,round(rows[i//2])+7,round((i%2+1)*W/2)-7,round(rows[i//2+1])-7]
  ImageOps.pad(im.crop(box),(512,384),color='white',method=Image.Resampling.LANCZOS).save(d/'keys'/f'key-{i+1:02d}.png');boxes.append(box)
 save(d/('keys/extraction-'+revision+'.json'),{'source':'revisions/board-'+revision+'.png','boxes':boxes,'operation':'tile extraction; preserve aspect; white pad','background':'held from v1, not replaced'})
 retrace(d,revision)

def seesaw(revision='v3'):
 d=ROOT/'shots/see-saw';original=json.loads((d/'design.json').read_text());drawing=original['drawing'];angles=[-28,-13,-2,27,5,-28]
 # The exact original plank and tiny upper mark rotate rigidly. Fulcrum and nearby dot hold.
 for k,a in enumerate(angles,1):
  lines=[]
  for i,s in enumerate(drawing):
   pts=[]
   for x,y in zip(s[0],s[1]):
    dx=x-97;dy=y-117
    if i in (0,1):
     dy=y-(118+(97-116)*(46-118)/(50-116))
     t=math.radians(a-38);dx,dy=dx*math.cos(t)-dy*math.sin(t),dx*math.sin(t)+dy*math.cos(t)
    pts.append((256+dx*1.3,210+dy*1.3))
   lines.append('<polyline points="'+' '.join(f'{x:.5f},{y:.5f}' for x,y in pts)+'"/>')
  svg='<svg xmlns="http://www.w3.org/2000/svg" width="512" height="384" viewBox="0 0 512 384"><rect width="512" height="384" fill="white"/><g fill="none" stroke="black" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+''.join(lines)+'</g></svg>'
  (d/'keys'/f'key-{k:02d}.svg').write_text(svg);cairosvg.svg2png(bytestring=svg.encode(),write_to=str(d/'keys'/f'key-{k:02d}.png'))
 save(d/'correspondence.json',{'revision':revision,'source':'design.json','kind':'exact original vector stroke correspondence','plank_stroke_indices':[0,1],'held_stroke_indices':[2,3],'support_pivot_original':[97,117],'plank_contact_original':[97,97.2727272727],'pivot_output':[256,210],'scale':1.3,'key_angles_degrees':angles,'angle_status':'authored pose choices from observed low-rise-high-return, not measured source angles','topology':'all four original strokes retained, no reflection','motion_approved':False})
 retrace(d,revision)

def hurricane():
 d=ROOT/'shots/hurricane';base=d/'keys/revisions/v1';order=[3,1,4,5,5,6]
 for k,old in enumerate(order,1):shutil.copy2(base/f'key-{old:02d}.png',d/'keys'/f'key-{k:02d}.png')
 plan=json.loads((d/'keyplan.json').read_text());newposes=['Largest lifted left crest at early source impact','Smaller crest settling','Broad low foreground ridge','Flat foam band','Held quieter foam band','Shallow wash continues']
 for k,old,p in zip(plan['keys'],order,newposes):k.update(pose=p,art_from_v1_key=old)
 plan['note']+=' Retimed v1 art to put largest crest at the early impact; K4/K5 share one held drawing.';save(d/'keyplan.json',plan)
 save(d/'keys/retime-v2.json',{'action':'retime','v1_key_order':order,'unique_drawings_used':5,'reason':'early impact crest, settling later','times_unchanged':True})
 retrace(d,'v2')
if __name__=='__main__':
 for slug in ('pig','raccoon','tractor','mosquito'):board_repair(slug)
 seesaw();hurricane()

