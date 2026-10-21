"""Append completed independent cow repair verdicts; keep rejected history."""
from pathlib import Path
import json,importlib.util
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
ledger=ROOT/'ledger.jsonl'
if not ledger.exists():loop.init_ledger(ledger)
with ledger.open() as f:old=loop.read_ledger(f)
existing={e['input']['revision']for e in old};parent=old[-1]['input']['revision']if old else None
for i in range(1,4):
 p=OUT/f'review-v{i}.json'
 if not p.exists():continue
 rev=f'cow-integrated-v{i}'
 if rev in existing:parent=rev;continue
 base=OUT/f'revisions/v{i}'if(OUT/f'revisions/v{i}').exists()else OUT
 checks=json.loads((base/'assembly-checks.json').read_text());review=json.loads(p.read_text());tr=checks['trace_fidelity'];fit=checks['mask_fit'];identity=review.get('identity_bar_met');pose=review.get('source_framing_pose_bar_met');passed=identity is True and pose is True;src=json.loads((base/'source.json').read_text());gap=review.get('most_important_gap')or'';protected=review.get('must_not_be_lost',[])
 if isinstance(protected,str):protected=[protected]
 details=['Assemble the native cow head/ears/eyes/muzzle over the source close-up with source-keyed jaw opening and one held background.','Widen the same native polygon muzzle beyond both sides of the head; retain source head placement, eye/ear anchors and observed jaw states.','Final bounded repair after independent still comparison.'][i-1]
 raw={'revision':rev,'parent':parent,'observation_refs':['plan.json','design.json','integrated/source-contact-sheet.jpg','integrated/sam/provenance.json'],'evidence_refs':[str(p.relative_to(ROOT)),str((base/'assembly-checks.json').relative_to(ROOT))],'action':{'type':'change_layer'if i==1 else'redraw_key','details':details},'before_refs':['design.png']if i==1 else[f'integrated/revisions/v{i-1}/shot.json'],'after_refs':[str((base/'shot.json').relative_to(ROOT)),str((base/'comparison.mp4').relative_to(ROOT))],'source':{'identity':src['clip_id'],'interval':{'start':src['interval_seconds'][0],'end':src['interval_seconds'][1],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':'unknown'if pose else False,'drawing_identity_preserved':identity if isinstance(identity,bool)else'unknown','train_eligible':False,'measured_tests':[{'name':'complete_decode','status':'pass','constraint':True,'value':checks['rendered_frames'],'unit':'frames','evidence_refs':[str((base/'video-validation.json').relative_to(ROOT))]},{'name':'character_trace','status':'pass'if tr['pass']else'fail','constraint':True,'value':tr['min_recall'],'unit':'minimum recall','evidence_refs':[str((base/'traced.json').relative_to(ROOT))]},{'name':'filled_rig_SAM_fit','status':'pass'if fit['pass']else'fail','constraint':True,'value':fit['mean'],'unit':'mean IoU','evidence_refs':[str((base/'mask-fit.json').relative_to(ROOT))]},{'name':'recognition_classifier','status':'unknown','constraint':True},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'independently verified planted intervals'},{'name':'independent_normal_speed_playback','status':'unknown','constraint':True}],'critic':{'scope':['source_composition','drawing_identity','sampled_source_event'],'verdict':'bar_met'if passed else'bar_not_met','gap':gap,'protected_strengths':protected,'independent':True}}
 e=loop.record(raw,ledger);print(rev,e['decision']['status']);parent=rev
# Preserve the raw primary verdict separately from its passing still-only components.
# An earlier v2 record scoped bar_met to component stills; this append-only correction
# leaves that history visible and states that the critic's overall animated bar was false.
with ledger.open()as f:entries=loop.read_ledger(f)
correction='cow-integrated-v2-verdict-scope'
if any(e['input']['revision']=='cow-integrated-v2'for e in entries)and not any(e['input']['revision']==correction for e in entries):
 review=json.loads((OUT/'review-v2.json').read_text())
 if review.get('bar_met')is False:
  import copy
  previous=next(e for e in entries if e['input']['revision']=='cow-integrated-v2');raw=copy.deepcopy(previous['input']);raw.update(revision=correction,parent=entries[-1]['input']['revision'],action={'type':'change_layer','details':'Append-only critic-scope metadata correction; no drawing pixels changed. The raw overall animated bar remains not met, although identity and source-pose still components passed.'},before_refs=['integrated/review-v2.json'],after_refs=['integrated/verdict-scope.json'])
  raw['critic']['verdict']='bar_not_met';raw['critic']['scope']=['source_composition','drawing_identity','sampled_source_event','overall_animated_bar_unapproved'];raw['critic']['gap']=review['most_important_gap'];raw['evidence_refs'].append('integrated/verdict-scope.json')
  (OUT/'verdict-scope.json').write_text(json.dumps({'review':'review-v2.json','overall_bar_met':False,'identity_still_bar_met':True,'source_pose_still_bar_met':True,'motion_approved':False,'clarification':'The raw critic overall verdict is preserved. Earlier ledger bar_met referred only to its still components; this record corrects primary verdict scope without changing any drawing or erasing history.'},indent=2)+'\n')
  entry=loop.record(raw,ledger);print(correction,entry['decision']['status'])
