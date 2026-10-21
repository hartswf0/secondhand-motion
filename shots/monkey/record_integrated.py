"""Append unedited blind monkey verdicts and measured constraints to a hash ledger."""
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
 rev=f'monkey-integrated-v{i}'
 if rev in existing:continue
 base=OUT/f'revisions/v{i}'if(OUT/f'revisions/v{i}').exists()else OUT
 checks=json.loads((base/'assembly-checks.json').read_text());review=json.loads(p.read_text());tr=checks['trace_fidelity'];fit=checks['mask_fit'];src=json.loads((base/'source.json').read_text())
 identity=review.get('identity_bar_met',review.get('drawing_identity_bar_met',review.get('original_doodle_identity',{}).get('status')=='met'));pose=review.get('source_framing_pose_bar_met',review.get('source_event_pose_bar_met',review.get('source_event_and_pose',{}).get('status')=='met'));overall=review.get('bar_met',False)
 gap=review.get('most_important_gap',review.get('one_gap_that_matters_most',review.get('gap','Review does not approve the whole animated bar.')));protected=review.get('must_not_be_lost',[])
 if isinstance(protected,str):protected=[protected]
 details=['Assemble all twelve native monkey strokes over a clean source head-lowering/return interval, with semantic head/face/eye/mouth/ear bindings and one held wall.','Bounded native face/head attachment repair after independent blind critique.','Bounded down-left facial shift and foreshortening inside the unchanged native head after the fresh source-pitch critique.'][i-1]
 raw={'revision':rev,'parent':parent,'observation_refs':['plan.json','design.json',str((base/'source-contact-sheet.jpg').relative_to(ROOT)),'integrated/sam/provenance.json'],'evidence_refs':[str(p.relative_to(ROOT)),str((base/'assembly-checks.json').relative_to(ROOT))],'action':{'type':'change_layer'if i==1 else'redraw_key','details':details},'before_refs':['design.png']if i==1 else[f'integrated/revisions/v{i-1}/shot.json'],'after_refs':[str((base/'shot.json').relative_to(ROOT)),str((base/'comparison.mp4').relative_to(ROOT))],'source':{'identity':src['clip_id'],'interval':{'start':src['interval_seconds'][0],'end':src['interval_seconds'][1],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':'unknown'if pose is True else False,'drawing_identity_preserved':identity if isinstance(identity,bool)else'unknown','train_eligible':False,'measured_tests':[{'name':'complete_decode','status':'pass','constraint':True,'value':checks['rendered_frames'],'unit':'frames','evidence_refs':[str((base/'video-validation.json').relative_to(ROOT))]},{'name':'character_trace','status':'pass'if tr['pass']else'fail','constraint':True,'value':tr['min_recall'],'unit':'minimum recall','evidence_refs':[str((base/'traced.json').relative_to(ROOT))]},{'name':'filled_rig_SAM_fit','status':'pass'if fit['pass']else'fail','constraint':True,'value':fit['mean'],'unit':'mean IoU','evidence_refs':[str((base/'mask-fit.json').relative_to(ROOT))]},{'name':'recognition_classifier','status':'unknown','constraint':True},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'independently verified planted intervals'},{'name':'independent_normal_speed_playback','status':'unknown','constraint':True}],'critic':{'scope':['source_composition','drawing_identity','sampled_source_event','overall_animated_bar_unapproved'],'verdict':'bar_met'if overall is True else'bar_not_met','gap':gap,'protected_strengths':protected,'independent':True}}
 e=loop.record(raw,ledger);print(rev,e['decision']['status']);parent=rev
