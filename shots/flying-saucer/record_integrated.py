"""Append completed integrated saucer reviews, retaining each candidate and raw verdict."""
from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('search_loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
with (ROOT/'ledger.jsonl').open() as f:entries=loop.read_ledger(f)
existing={e['input']['revision'] for e in entries};parent=entries[-1]['input']['revision'];source=json.loads((ROOT/'source.json').read_text())
for i in (1,2,3):
 review_file=OUT/f'review-v{i}.json'
 if not review_file.exists():break
 revision=f'flying-saucer-integrated-v{i}'
 if revision in existing:continue
 base=OUT/f'revisions/v{i}' if (OUT/f'revisions/v{i}').exists() else OUT
 c=json.loads((base/'assembly-checks.json').read_text());r=json.loads(review_file.read_text());trace=c['trace_fidelity'];fit=c['mask_fit']
 identity=r.get('original_quickdraw_identity_bar_met',r.get('quickdraw_identity',{}).get('bar_met','unknown'));pose=r.get('source_framing_pose_bar_met',r.get('source_framing_pose',{}).get('bar_met','unknown'))
 gap=r.get('most_important_gap',r.get('source_framing_pose',{}).get('most_important_gap',r.get('one_gap_that_matters_most',r.get('single_most_important_gap','Normal-speed playback remains unreviewed.'))))
 strength=r.get('must_not_be_lost',r.get('strengths_to_preserve','Original sparse imperfect rim, dome and specks.'));strength=[strength] if isinstance(strength,str) else strength
 refs=lambda name:str((base/name).relative_to(ROOT))
 raw=dict(revision=revision,parent=parent,observation_refs=['source.json','design.json','integrated/source-contact-sheet.jpg','integrated/source-masks/provenance.json'],evidence_refs=[str(review_file.relative_to(ROOT)),refs('assembly-checks.json')],action=dict(type='change_layer' if i==1 else 'repair_tracking',details='Assemble original six native saucer strokes under NASA CGI source top/cap trajectory and held cloud plate.' if i==1 else 'Retain observed bottom crop with a bounded lower-contour extension; source top/cap landmarks fixed, hidden continuation unverified.'),before_refs=['keys/'] if i==1 else [f'integrated/revisions/v{i-1}/shot.json'],after_refs=[refs('shot.json'),refs('comparison.mp4')],source=dict(identity=source['clip_id'],interval=dict(start=source['interval_seconds'][0],end=source['interval_seconds'][1],unit='seconds')),claims=['drawing','motion'],source_event_preserved=False if pose is False else 'unknown',drawing_identity_preserved=identity,train_eligible=False,
 measured_tests=[dict(name='complete_movie_decode',status='pass',constraint=True,value=c['rendered_frames'],unit='frames per movie',evidence_refs=[refs('video-validation.json')]),dict(name='trace_fidelity',status='pass' if trace['pass'] else 'fail',constraint=True,value=trace['min_recall'],unit='minimum recall',metric='Recall >=.98; every ink part kept in all8 separated character exports.',evidence_refs=[refs('traced.json')]),dict(name='filled_rig_mask_fit',status='pass' if fit['pass'] else 'fail',constraint=True,value=fit['mean'],unit='mean IoU',metric=fit['method']+'; mean>=.65, minimum>=.45; SAM predicted confidence reported separately.',evidence_refs=[refs('mask-fit.json')]),dict(name='recognition_classifier',status='unknown',constraint=True),dict(name='planted_contacts',status='fail',constraint=True,value=0,unit='verified planted intervals',metric='No planted contacts in flying subject; cannot pass a gate requiring >=4.'),dict(name='normal_speed_playback',status='unknown',constraint=True)],critic=dict(scope=['drawing_identity','source_composition','source_pose'],verdict='bar_met' if identity is True and pose is True else 'bar_not_met',gap=gap,protected_strengths=strength,independent=True))
 entry=loop.record(raw,ROOT/'ledger.jsonl');parent=revision;print(revision,entry['decision']['status'])
