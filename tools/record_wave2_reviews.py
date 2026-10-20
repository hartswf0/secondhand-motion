"""Record real blind still reviews without manufacturing motion or learning evidence."""
import hashlib,importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('repair_loop',ROOT/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)

def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def verdict(obj):
 if isinstance(obj,str):obj={'verdict':obj}
 if not isinstance(obj,dict):return None
 if isinstance(obj.get('met'),bool):return obj['met']
 v=obj.get('verdict',obj.get('status'))
 if v in ('met','pass','bar_met','pass_still_keys'):return True
 if v in ('not_met','fail','bar_not_met','repair_required','not met'):return False
 return None

def assessments(r):
 if r.get('verdict')=='pass_still_keys' or r.get('still_key_verdict')=='pass':return True,True
 a=verdict(r.get('identity',r.get('exact_chosen_doodle_identity')))
 b=next((verdict(r.get(k)) for k in ('source_pose','source_poses','poses','source_pose_mechanics','source_pose_progression') if isinstance(r.get(k),(dict,str))),None)
 return a,b

def main():
 for d in sorted((ROOT/'shots').iterdir()):
  if not (d/'keyplan.json').exists() or not (d/'keys/revisions/board-v1.png').exists():continue
  plan=json.loads((d/'keyplan.json').read_text());rev=plan['revision'];src=json.loads((d/'source.json').read_text());trace=json.loads((d/'keys/traced.json').read_text())
  # Every proposal keeps immutable key bytes, not only a mutable current-path reference.
  dest=d/'keys/revisions'/rev;dest.mkdir(exist_ok=True)
  for p in [*(d/'keys'/f'key-{k:02d}.png' for k in range(1,7)),d/'keys/traced.json']:
   if not (dest/p.name).exists():shutil.copy2(p,dest/p.name)
  manifest={'revision':rev,'source_sha256':src['source_sha256'],'files':{}}
  for p in [d/'design.json',d/'design.png',*(d/'keys'/f'key-{k:02d}.png' for k in range(1,7)),d/'keys/traced.json']:
   manifest['files'][p.relative_to(d).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
  write(d/'keys/artifacts.json',manifest)
  ledger=d/'ledger.jsonl'
  if not ledger.exists():loop.init_ledger(ledger)
  existing={json.loads(l)['input']['revision'] for l in ledger.read_text().splitlines() if l.strip()}
  reviews=sorted((d/'reviews').glob('blind-v*.json'))
  latest=None;last_revision=None
  for rp in reviews:
   r=json.loads(rp.read_text());identity,pose=assessments(r);rv=rp.stem.split('-')[-1];candidate=d.name+'-'+rv
   latest=(rp,r,identity,pose)
   if candidate in existing:
    prior=next(json.loads(l)['input'] for l in ledger.read_text().splitlines() if json.loads(l)['input']['revision']==candidate)
    corrected=(prior['source_event_preserved']!=(pose if pose is not None else 'unknown') or prior['drawing_identity_preserved']!=(identity if identity is not None else 'unknown'))
    if not corrected:last_revision=candidate;continue
    last_revision=candidate;candidate+='-review-normalization'
    if candidate in existing:last_revision=candidate;continue
   current=rv==rev
   measured=[{'name':'recognition_classifier','status':'unknown','constraint':True,'evidence_refs':['tests.json']}]
   if current:
    passed=all(k['recall']>=.98 and k['parts_kept']==1 for k in trace['keys'])
    measured.append({'name':'trace_fidelity','status':'pass' if passed else 'fail','constraint':True,'value':min(k['recall'] for k in trace['keys']),'unit':'fraction','metric':'minimum recall; parts_kept must equal1 per key','evidence_refs':['keys/traced.json']})
   else:measured.append({'name':'trace_fidelity','status':'unknown','constraint':True})
   gap=r.get('one_gap_that_matters_most',r.get('greatest_gap',r.get('biggest_gap','')))
   raw={'revision':candidate,'parent':last_revision,'observation_refs':['source.json','design.json'],'evidence_refs':[rp.relative_to(d).as_posix()],
     'action':{'type':'add_key' if rv=='v1' else 'redraw_key','details':'Six proposed still keys; one bounded repair per critique. No motion or model training.'},
     'before_refs':['design.png' if rv=='v1' else 'reviews/blind-v'+str(int(rv[1:])-1)+'.json'],
     'after_refs':['keys/revisions/'+rv+'/' if (d/'keys/revisions'/rv).exists() else 'keys/revisions/board-'+rv+'.png'],
     'source':{'identity':src['clip_id'],'interval':{'start':src['interval_seconds'][0],'end':src['interval_seconds'][1],'unit':'seconds'}},
     'claims':['drawing'],'source_event_preserved':pose if pose is not None else 'unknown','drawing_identity_preserved':identity if identity is not None else 'unknown','train_eligible':False,
     'measured_tests':measured,'critic':{'scope':['drawing_identity','still_source_poses'],'verdict':'bar_met' if identity is True and pose is True else ('bar_not_met' if identity is False or pose is False else 'uncertain'),'gap':gap or '',
      'protected_strengths':r.get('must_not_be_lost',r.get('protected_strengths',r.get('protect',[]))),'independent':True}}
   loop.record(raw,ledger);last_revision=candidate
  rp,r,identity,pose=latest
  status='passed still review' if identity is True and pose is True else ('pose review uncertain' if pose is None else 'pose repair required')
  gates=json.loads((d/'keys/gates.json').read_text());gates.update(identity_critic={'met':identity,'evidence':rp.relative_to(d).as_posix()},still_pose_critic={'met':pose,'evidence':rp.relative_to(d).as_posix()},still_review=status,motion_approved=False,training_ran=False);write(d/'keys/gates.json',gates)
  tests=json.loads((d/'tests.json').read_text())
  for t in tests:
   if t['id']=='J4':t.update(value='independent identity '+('met' if identity else 'uncertain'),unit='',ok=identity)
  loop.select(ledger)
  for t in tests:
   if t['id']=='S7':t.update(value=len(ledger.read_text().splitlines()),unit='verified hash-linked entries',ok=True)
  if not any(t['id']=='S7' for t in tests):tests.append({'id':'S7','value':len(ledger.read_text().splitlines()),'unit':'verified hash-linked entries','ok':True})
  write(d/'tests.json',tests)
  it=json.loads((d/'item.json').read_text());it['blurb']='Six source-linked key drafts; '+status+'. Motion not reviewed.';write(d/'item.json',it)
  print(d.name,status,flush=True)
if __name__=='__main__':main()

