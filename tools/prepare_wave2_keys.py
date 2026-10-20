"""Prepare explicit draft-key packets from source observations and generated sheets.
No correspondence, SAM, recognition, or motion approval is inferred.
"""
import hashlib, importlib.util, json, math, shutil, sys
from pathlib import Path
from PIL import Image, ImageOps
import trace_keys
ROOT=Path(__file__).resolve().parent.parent
# All indices refer to the saved dense16-photo source sheet, one-based.
PLANS={
 'tornado':([1,4,7,10,13,16],[.2335666667,3.2699333333],['Funnel contour establishes the street view','Subtle contour widening','Funnel edge changes behind foreground trees','Narrower lower funnel, same upper rim','Upper contour softens','Last clean funnel pose before credits'], 'Observed contour anchors; rotation is not established.'),
 'raccoon':([3,4,7,9,11,15],[10.810810811,13.580246914],['Frontal head upright','Frontal head dropping','Three-quarter left, muzzle low','Forward reach as body turns left','Left side, head low','Low foraging hold'], 'Tail and feet are partly occluded; contacts and hidden contours remain unverified.'),
 'hurricane':([4,5,7,9,12,16],[31.1311311311,34.2008675342],['Right water bunch rises','Right falls, smaller left splash','Largest observed left plume','Low broad foreground ridge','Flatter foam band','Shallow restless wash'], 'Storm surf/flooding against a building, not visible cyclone rotation. Seven-stroke doodle is an abstraction of water.'),
 'rain':([4,6,8,10,12,14],[34.4344344344,38.8054721388],['Establish nine rain strokes','Staggered descent phase','Lower marks shorten near impact','Upper marks continue downward','Lower marks recycle at staggered phases','Continue steady rainfall'], 'Procedural phases assigned to observed timestamps; individual source drops are not tracked.'),
 'mosquito':([1,3,5,7,11,16],[.2335669002,5.2385719052],['Standing, wing upright','Small head dip and front-leg bend','Foreleg lifts toward proboscis','Foreleg returns, small body pitch','Subtle lean and leg reposition','Settled standing pose'], 'Proposed grooming keys, not flight. Source-pose fidelity needs critique. Environment plate remains pending.'),
 'pig':([8,10,11,12,13,15],[6.3063063063,8.2415749082],['Broadside left hold','Leading foreleg advances, turn begins','Quarter-turn reach toward camera','Three-quarter approach','Closer, foreshortened barrel','Near-frontal three-quarter, lowered head'], 'Source rump partly cropped. Preserve original five dangling leg strokes as drawing grammar; no contact measurements.'),
 'tractor':([1,3,5,7,10,11],[.5,2.45],['Distant three-quarter approach','Larger approach, hood leading left','Turning into near pass','Near three-quarter, rear wheel dominant','Close almost side-on pass','Near-profile at left edge'], 'Driver and trailer are omitted context layers. Later source frames crop the tractor and show doubled exposure.'),
 'fan':([1,4,7,10,13,16],[1.2,4.3043],['Establish held housing and rotor','Rotor phase check 2','Rotor phase check 3','Rotor phase check 4','Rotor phase check 5','Rotor phase check 6'], 'Procedural rotor phases; exact angles and RPM are unresolved by source blur. Housing must hold; generated drafts may require repair.'),
 'flying-saucer':([3,4,5,6,13,14],[2.3356690023,4.5378712045],['First clean steep aeroshell attitude','Slight right/down drift','Further downward drift','Low rightward position','Returns left/up, broader face','Last clean pre-tether sampled pose'], 'NASA CGI entry aeroshell transfers attitude to a saucer doodle; not physical UFO footage. Middle source samples crop lower rim; hidden contour not verified.'),
 'see-saw':([1,8,10,12,14,16],[8.8,16.1],['Near left end low','Near end begins rising','Mid-rise, near level','Highest observed near-end pose','Near end descending','Low return'], 'Prop-only key draft. Riders omitted. Plank should retain rigid length and fixed fulcrum; exact reversal times not measured.')
}

def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')

def prepare(slug,plan):
 d=ROOT/'shots'/slug; indices,interval,poses,note=plan
 req=json.loads((d/'source-review-request.json').read_text());cid=req['clip_ids'][0]
 record=json.loads((d/'source-review/selected'/f'{cid}.json').read_text());c=record['source']
 source={**c,'source_id':c['video_url'].split('/sources/')[1].split('/')[0],
  'interval_seconds':interval,'time_basis':'clip_relative_seconds',
  'film_interval_seconds':[float(c['start_seconds'])+t for t in interval],
  'rights':{'reported':None,'status':'not provided in candidate manifest; unverified'},
  'why_this_clip':note,'sampled_continuity':'No cut visible in retained sampled window; continuous playback not approved.',
  'source_sha256':record['source_sha256'],'fps':record['fps'],
  'source_review':'source-review/selected/'+cid+'-16frames.jpg','source_approved':False,
  'source_kind':'NASA CGI archive animation' if slug=='flying-saucer' else 'archive footage',
  'motion_approved':False,'train_eligible':False}
 write(d/'source.json',source)
 keys=[]
 for k,(idx,pose) in enumerate(zip(indices,poses),1):
  f=record['frames'][idx-1]
  keys.append({'key':k,'file':f'keys/key-{k:02d}.png','source_sheet_index':idx,'time':f['index_time'],'source_frame_index':f['frame_index'],'pose':pose})
 keyplan={'status':'draft_still_keys','revision':'v1','source_clip_id':cid,'keys':keys,'note':note,
 'representation':'procedural phases' if slug in ('rain','fan') else 'proposed source-pose keys',
 'background':None if slug=='mosquito' else 'keys/bg-plate.png','motion_approved':False,'training_ran':False}
 write(d/'keyplan.json',keyplan)
 im=Image.open(d/'keys/revisions/board-v1.png').convert('RGB');W,H=im.size
 # Explicit extraction windows: sheets are model outputs, so rows are checked rather than assumed uniform.
 rows=[0,H/4,H/2,H*3/4,H]
 if slug=='raccoon': rows=[0,340,680,970,H]
 if slug=='hurricane': rows=[0,340,680,990,H]
 cells=[]; traced={'W':512,'H':384,'revision':'v1','keys':[],'correspondence_established':False}
 crops=[]
 for i in range(7 if slug!='mosquito' else 6):
  x0=round((i%2)*W/2);x1=round((i%2+1)*W/2);row=i//2
  # 7px inset strips generated sheet rules, not character strokes.
  box=[x0+7,round(rows[row])+7,x1-7,round(rows[row+1])-7]
  crop=im.crop(box)
  crop=ImageOps.pad(crop,(512,384),color='white',method=Image.Resampling.LANCZOS)
  name=f'key-{i+1:02d}.png' if i<6 else 'bg-plate.png'
  crop.save(d/'keys'/name)
  cells.append({'output':'keys/'+name,'box':box,'source_size':[W,H],'output_size':[512,384],'operation':'extract tile; preserve aspect ratio; white pad; no semantic repaint'})
  if i<6:
   st,ink,hw=trace_keys.trace(crop)
   recall,precision,parts=trace_keys.score(st,ink,512,384,hw)
   entry={'file':'keys/'+name,'time':keys[i]['time'],'n_strokes':len(st),'points':sum(len(s) for s in st),'recall':recall,'precision':precision,'parts_kept':parts,'half_width':hw,'strokes':st}
   traced['keys'].append(entry);crops.append(crop)
 write(d/'keys/extraction-v1.json',{'board_sha256':hashlib.sha256((d/'keys/revisions/board-v1.png').read_bytes()).hexdigest(),'cells':cells})
 write(d/'keys/traced.json',traced)
 proof=Image.new('RGB',(1024,1152),'white')
 for i,crop in enumerate(crops):proof.paste(crop,((i%2)*512,(i//2)*384))
 proof.save(d/'keys/proof-v1.jpg',quality=90)
 tests=json.loads((d/'tests.json').read_text())
 for t in tests:
  # Never reuse placeholder scores from other work.
  if t['id']=='T1':
   ok=all(k['recall']>=.98 and k['parts_kept']==1 for k in traced['keys'])
   t.update(value={'min_recall':min(k['recall'] for k in traced['keys']),'min_parts_kept':min(k['parts_kept'] for k in traced['keys']),'keys':6},unit='fraction',ok=ok)
  elif t['id']=='S6':t.update(value='source record complete; rights explicitly unverified',unit='',ok=True)
 write(d/'tests.json',tests)
 gates={'revision':'v1','source_sampled':True,'identity_critic':'pending','trace':{'recall_bar':.98,'parts_kept_bar':1.,'all_keys_pass':all(k['recall']>=.98 and k['parts_kept']==1 for k in traced['keys'])},
 'held_background':'one separate plate provided' if slug!='mosquito' else 'pending',
 'recognition_classifier':'not run','SAM_segmentation':'not run','mask_fit':'not run','stroke_correspondence':'not established','foot_slide':'not measured','motion_approved':False,'training_ran':False,'train_eligible':False}
 write(d/'keys/gates.json',gates)
 item=json.loads((d/'item.json').read_text());item.update(status='in progress',lane='look',stage=4,
  blurb='Six proposed keys with timed source references. Still drafts; motion review pending.',
  cover=f'shots/{slug}/keys/key-01.png',cover_credit='Image-model draft from Quick, Draw! key_id '+json.loads((d/'design.json').read_text())['key_id']+'; Quick, Draw! contributors / Google Creative Lab, CC BY 4.0',
  tags=['key drafts','wave 2'],links=[{'label':'Review six keys','href':f'shots/{slug}/index.html'},{'label':'Candidate search','href':f'shots/{slug}/candidates.json'}])
 write(d/'item.json',item)
 print(slug,'6 keys traced; minimum recall',min(k['recall'] for k in traced['keys']),'parts',min(k['parts_kept'] for k in traced['keys']),flush=True)

def main():
 for slug,p in PLANS.items():prepare(slug,p)
if __name__=='__main__':main()

