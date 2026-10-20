"""Record the three completed pig assembly reviews without editing existing history."""
from pathlib import Path
import json,importlib.util
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('search_loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
with open(ROOT/'ledger.jsonl') as f:entries=loop.read_ledger(f)
existing={x['input']['revision'] for x in entries};parent=entries[-1]['input']['revision']
source=json.loads((ROOT/'source.json').read_text())
for i in range(1,4):
 revision=f'pig-integrated-v{i}'
 if revision in existing:
  parent=revision;continue
 base=OUT/f'revisions/v{i}' if i<3 else OUT
 review=json.loads((OUT/f'review-v{i}.json').read_text());checks=json.loads((base/'assembly-checks.json').read_text());trace=checks['trace_fidelity']
 gap=review.get('one_gap_that_matters_most',review.get('most_important_gap',review.get('single_most_important_gap','')))
 identity=i!=2
 raw={'revision':revision,'parent':parent,'observation_refs':['source.json','design.json','integrated/source-contact-sheet.jpg','integrated/source-masks/provenance.json'],'evidence_refs':[f'integrated/review-v{i}.json',str((base/'assembly-checks.json').relative_to(ROOT))],
 'action':{'type':['change_layer','repair_tracking','redraw_key'][i-1],'details':['Assemble cropped pig from original10strokes, held scene and source-framed anatomical keys.','Repair parallel pole legs into source-observed reaching/bending paths; occlude far legs behind torso.','Keep original compact boxed spiral snout under its own bounded source-observed transform.'][i-1]},
 'before_refs':['keys/proof-v2.jpg'] if i==1 else [f'integrated/revisions/v{i-1}/shot.json'],
 'after_refs':[str((base/'shot.json').relative_to(ROOT)),str((base/'comparison.mp4').relative_to(ROOT))],
 'source':{'identity':source['clip_id'],'interval':{'start':source['interval_seconds'][0],'end':source['interval_seconds'][1],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':False,'drawing_identity_preserved':identity,'train_eligible':False,
 'measured_tests':[{'name':'all47frames_decode','status':'pass','constraint':True,'value':47,'unit':'frames','evidence_refs':[str((base/'video-validation.json').relative_to(ROOT))]},
 {'name':'character_trace','status':'pass' if trace['pass'] else 'fail','constraint':True,'value':trace['min_recall'],'unit':'minimum recall','metric':'recall >=.98 and every ink piece kept; six separated character exports','evidence_refs':[str((base/'traced.json').relative_to(ROOT))]},
 {'name':'source_pose_mask_fit','status':'unknown','constraint':True,'metric':'Filled rig-envelope proxy measured separately; not pixel-exact rendered cartoon coverage. Independent source-pose review does not pass.','evidence_refs':[str((base/'mask-fit.json').relative_to(ROOT))]},
 {'name':'recognition_classifier','status':'unknown','constraint':True},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'independently verified planted intervals','metric':'At least4 required; no zero-interval pass.'},{'name':'independent_normal_speed_playback','status':'unknown','constraint':True}],
 'critic':{'scope':['drawing_identity','source_composition','source_pose'],'verdict':'bar_not_met','gap':gap,'protected_strengths':review.get('strengths_not_to_lose',review.get('strengths_to_preserve',[])),'independent':True}}
 entry=loop.record(raw,ROOT/'ledger.jsonl');print(revision,entry['decision']['status']);parent=revision
