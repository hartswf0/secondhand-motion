"""Append independent tiger verdicts with immutable rejected revisions preserved."""
from pathlib import Path
import importlib.util,json,copy
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'integrated'; REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('repair_loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
ledger=ROOT/'ledger.jsonl'
if not ledger.exists():loop.init_ledger(ledger)
with ledger.open()as handle:old=loop.read_ledger(handle)
known={e['input']['revision']for e in old};parent=old[-1]['input']['revision']if old else None
for i in range(1,4):
 p=OUT/f'review-v{i}.json';rev=f'tiger-integrated-v{i}'
 if not p.exists():continue
 if rev in known:continue
 base=OUT/f'revisions/v{i}'if(OUT/f'revisions/v{i}').exists()else OUT
 checks=json.loads((base/'assembly-checks.json').read_text());r=json.loads(p.read_text());src=json.loads((base/'source.json').read_text());tr=checks['trace_fidelity'];fit=checks['mask_fit']
 pose=r['source_framing_pose_bar_met'];identity=r['original_doodle_identity_bar_met'];still=pose and identity
 protected=r.get('must_not_be_lost',[])
 if isinstance(protected,str):protected=[protected]
 raw={'revision':rev,'parent':parent,'observation_refs':['integrated/source.json','integrated/design.json','integrated/source-contact-sheet.jpg','integrated/sam/provenance.json'],'evidence_refs':[str(p.relative_to(ROOT)),str((base/'assembly-checks.json').relative_to(ROOT))],'action':{'type':'change_layer'if i==1 else'redraw_key','details':'First integrated source-matched candidate: retain the locked native11-stroke crouched tiger; source-key head/eye anchors, hold native striped body and source-authored background.'if i==1 else json.loads((base/'repair.json').read_text())['repair']},'before_refs':['integrated/design.png']if i==1 else[f'integrated/revisions/v{i-1}/shot.json'],'after_refs':[str((base/'shot.json').relative_to(ROOT)),str((base/'comparison.mp4').relative_to(ROOT))],'source':{'identity':src['clip_id'],'interval':{'start':3.25,'end':6.,'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':'unknown'if pose else False,'drawing_identity_preserved':identity,'train_eligible':False,'measured_tests':[{'name':'complete_decode','status':'pass','constraint':True,'value':checks['rendered_frames'],'unit':'frames','evidence_refs':[str((base/'video-validation.json').relative_to(ROOT))]},{'name':'character_trace','status':'pass'if tr['pass']else'fail','constraint':True,'value':tr['min_recall'],'unit':'minimum recall','evidence_refs':[str((base/'traced.json').relative_to(ROOT))]},{'name':'filled_native_tiger_SAM_fit','status':'pass'if fit['pass']else'fail','constraint':True,'value':fit['mean'],'unit':'mean IoU','evidence_refs':[str((base/'mask-fit.json').relative_to(ROOT))]},{'name':'recognition_classifier','status':'unknown','constraint':True},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'independently verified planted intervals'},{'name':'independent_normal_speed_playback','status':'unknown','constraint':True}],'critic':{'scope':['sampled_source_framing_pose','original_doodle_identity_stills'],'verdict':'bar_met'if still else'bar_not_met','gap':r.get('most_important_gap')or'No sampled still gap; actual normal-speed playback, recognition and planted contact gates remain unmet or unrun.','protected_strengths':protected,'independent':True}}
 entry=loop.record(raw,ledger);print(rev,entry['decision']['status']);parent=rev

# Earlier proposals were recorded immediately before snapshotting. Preserve those
# envelopes and append the durable artifact references rather than rewrite history.
with ledger.open()as handle:entries=loop.read_ledger(handle)
for i in (1,2):
 revision=f'tiger-integrated-v{i}';correction=revision+'-evidence-freeze';base=OUT/f'revisions/v{i}'
 if not base.exists()or any(e['input']['revision']==correction for e in entries):continue
 prior=next((e for e in entries if e['input']['revision']==revision),None)
 if prior is None:continue
 if any('revisions/'in ref for ref in prior['input']['after_refs']):continue
 raw=copy.deepcopy(prior['input']);prefix=f'integrated/revisions/v{i}/'
 raw.update(revision=correction,parent=entries[-1]['input']['revision'],action={'type':'change_layer','details':f'Append-only evidence reference freeze for {revision}; no drawing pixels or raw critic verdict changed. The original entry preceded snapshotting and used then-current integrated paths; these references identify its preserved immutable artifacts.'},observation_refs=[prefix+'source.json',prefix+'design.json',prefix+'source-contact-sheet.jpg',prefix+'sam/provenance.json'],evidence_refs=[prefix+f'review-v{i}.json',prefix+'assembly-checks.json'],before_refs=prior['input']['after_refs'],after_refs=[prefix+'shot.json',prefix+'comparison.mp4'])
 for test in raw['measured_tests']:
  if'evidence_refs'in test:test['evidence_refs']=[prefix+Path(ref).name for ref in test['evidence_refs']]
 entry=loop.record(raw,ledger);entries.append(entry);print(correction,entry['decision']['status'])

reviews=sorted(OUT.glob('review-v*.json'));r=json.loads(reviews[-1].read_text());c=json.loads((OUT/'assembly-checks.json').read_text());s=json.loads((OUT/'shot.json').read_text());tr=c['trace_fidelity'];fit=c['mask_fit'];pose=r['source_framing_pose_bar_met'];identity=r['original_doodle_identity_bar_met'];still=pose and identity
with ledger.open()as handle:old=loop.read_ledger(handle)
gap=r.get('most_important_gap')or'No sampled still gap identified.'
s.update(status='assembled_stills_pass_motion_gates_unmet'if still else'assembled_review_gaps',review_status='still_pass_motion_gates_unmet'if still else'still_gap_motion_unapproved',review_badge='STILL BARS MET · MOTION GATES UNMET'if still else'REVIEW GAP · MOTION UNAPPROVED',review_note=f'{len(reviews)} independent blind still review round(s). Source framing/pose: {"met"if pose else"not met"}; original doodle identity: {"met"if identity else"not met"}. {gap} No actual normal-speed playback approval, recognition classifier or verified planted-contact gate. No training ran.')
(OUT/'shot.json').write_text(json.dumps(s,indent=2)+'\n');c['independent_still_review']={'source_framing_pose_bar_met':pose,'original_doodle_identity_bar_met':identity,'rounds':len(reviews),'evidence':reviews[-1].name};c['ledger_entries']=len(old);(OUT/'assembly-checks.json').write_text(json.dumps(c,indent=2)+'\n')
rows=[{'id':i,'value':'not run','unit':'','ok':None}for i in ['M1','M2','M2b','M5','M6','J1','J2','J3']]
rows += [{'id':'S6','value':'Archive ids, raw SHA, retained and original film intervals, URLs and reported public_domain preserved. Rights independently unverified.','unit':'','ok':True},{'id':'J4','value':{'review':reviews[-1].name,'rounds':len(reviews),'source_framing_pose_bar_met':pose,'original_doodle_identity_bar_met':identity},'unit':'sampled still review only','ok':still},{'id':'B1','value':1.,'unit':'fraction of held background geometry unchanged; bar0.9','ok':True},{'id':'T1','value':tr,'unit':'fraction','ok':tr['pass']},{'id':'T3','value':'All11 native strokes and original point counts retained in all67 dense frames','unit':'','ok':True},{'id':'M3','value':fit,'unit':'filled native silhouette/SAM IoU','ok':fit['pass']},{'id':'M4','value':0,'unit':'independently verified planted intervals; minimum4 required','ok':False},{'id':'S1','value':'Locked camera / single held rock plane, no depth pan measured','unit':'','ok':None},{'id':'S2','value':'QuickDraw key6296227597516800, CC BY4.0; held rocks drawn once by agent from source','unit':'','ok':True},{'id':'S3','value':{'frames':67,'fps':24,'keys':s['keys'],'source_time_every_frame':True},'unit':'','ok':True},{'id':'S4','value':'Relative links and script syntax checked separately;390px browser layout unrun','unit':'','ok':None},{'id':'S5','value':'Opaque native body/head fills hide farther background; no separate depth-contact review','unit':'','ok':None},{'id':'S7','value':len(old),'unit':'verified append-only hash-linked entries','ok':True}]
(ROOT/'tests.json').write_text(json.dumps(rows,indent=2)+'\n')
