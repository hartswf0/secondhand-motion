"""Freeze native review candidates and append unedited critic evidence; no training."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';REPO=ROOT.parents[1]
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def snapshot(name):
 target=OUT/'revisions'/name
 assert not target.exists(), 'Never overwrite a reviewed revision'
 target.mkdir(parents=True)
 for p in OUT.iterdir():
  if p.name in {'revisions','freeze.json','final-verification.json'} or p.name.startswith('review-v') or p.name.startswith('.'):continue
  if p.is_dir():shutil.copytree(p,target/p.name)
  else:shutil.copy2(p,target/p.name)
 files=[]
 for p in sorted(target.rglob('*')):
  if p.is_file():files.append({'path':str(p.relative_to(target)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 write(target/'snapshot-hashes.json',{'revision':name,'files':files});print('Frozen',name,len(files),'files')
def finalize():
 spec=importlib.util.spec_from_file_location('repair_loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
 ledger=ROOT/'ledger.jsonl'
 if not ledger.exists():loop.init_ledger(ledger)
 with ledger.open()as f:old=loop.read_ledger(f)
 reviews=sorted(OUT.glob('review-v*.json'),key=lambda p:int(p.stem.split('v')[-1]))
 assert reviews,'Need fresh unedited critic verdict'
 for review in reviews:
  num=int(review.stem.split('v')[-1]);revision=ROOT.name+'-integrated-v'+str(num)
  if any(r['input']['revision']==revision for r in old):continue
  base=OUT/'revisions'/('v'+str(num));assert base.exists(),'Freeze version before critique/repair'
  r=read(review);c=read(base/'assembly-checks.json');s=read(base/'shot.json');src=read(base/'source.json');tr=c['trace_fidelity'];identity=r.get('identity_bar_met',r.get('original_doodle_identity_bar_met'));pose=r.get('source_framing_pose_bar_met');still=identity is True and pose is True
  gap=r.get('most_important_gap',r.get('primary_gap','Unresolved independent review gap.'));protect=r.get('must_not_be_lost',r.get('protect',[]));protect=[str(x)for x in protect]if isinstance(protect,list)else[str(protect or 'Preserve native stroke identity and the source event.')]
  rel=str(base.relative_to(ROOT));raw={'revision':revision,'parent':old[-1]['input']['revision']if old else None,'observation_refs':[rel+'/source.json',rel+'/design.json',rel+'/source-contact-sheet.jpg'],'evidence_refs':[str(review.relative_to(ROOT)),rel+'/assembly-checks.json',rel+'/snapshot-hashes.json'],'action':{'type':'change_layer','details':'Source-paired native vector assembly from immutable study inputs; original point/stroke topology retained with separately credited operation props.'if num==1 else'Repair only the bounded independent source-pose/identity gap; previous full revision retained.'},'before_refs':['integrated/input/gwp-original.json']if not old else[old[-1]['input']['after_refs'][0]],'after_refs':[rel+'/shot.json',rel+'/comparison.mp4'],'source':{'identity':src['clip_id'],'interval':{'start':src['start_seconds'],'end':src['end_seconds'],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':False if pose is False else'unknown','drawing_identity_preserved':identity if isinstance(identity,bool)else'unknown','train_eligible':False,'measured_tests':[{'name':'complete_decode','status':'pass','constraint':True,'value':s['frame_count'],'unit':'frames'},{'name':'trace_fidelity','status':'pass'if tr['pass']else'fail','constraint':True,'value':tr['min_recall'],'unit':'minimum recall; bar .98'},{'name':'audited_final_mask_fit','status':'unknown','constraint':True,'metric':'Final native geometry not measured against audited same-instance masks; model confidence is not fit.'},{'name':'verified_planted_intervals','status':'fail','constraint':True,'value':0,'unit':'independent planted intervals; minimum4'},{'name':'recognition_classifier','status':'unknown','constraint':True},{'name':'normal_speed_playback','status':'unknown','constraint':True}],'critic':{'scope':['original_doodle_identity','sampled_source_framing_pose'],'verdict':'bar_met'if still else'bar_not_met','gap':gap or'No still gap; actual motion evidence missing.','protected_strengths':protect,'independent':True}}
  loop.record(raw,ledger)
  with ledger.open()as f:old=loop.read_ledger(f)
 r=read(reviews[-1]);c=read(OUT/'assembly-checks.json');s=read(OUT/'shot.json');cfg=read(OUT/'config.json');tr=c['trace_fidelity'];identity=r.get('identity_bar_met',r.get('original_doodle_identity_bar_met'));pose=r.get('source_framing_pose_bar_met');still=identity is True and pose is True;gap=r.get('most_important_gap',r.get('primary_gap','Unresolved still-review gap.'))
 note=('Fresh blind still review passed native identity and sampled source framing/pose. 'if still else'Fresh blind still review leaves a gap: '+str(gap)+' ')+'Final same-instance mask fit, classifier and normal-speed playback remain unrun; zero verified planted intervals fails the contact gate. No training ran.'
 if not tr['pass']:note+=' Raster trace fidelity remains below its unchanged threshold (minimum recall '+format(tr['min_recall'],'.4f')+'); all measured ink components are retained.'
 if ROOT.name in ['roller-coaster','skateboard']:
  c['static_background_geometry_held']=True;c['held_background_geometry']=None;c['background_strokes_unchanged_fraction']=None;c['background_gate_scope']='Static scenery remains held, but source-observed projected track/cone/operator geometry is not a verified held world-space background; overall B1 remains unknown.'
 s.update(status='assembled_stills_pass_motion_gates_unmet'if still else'assembled_still_gap_motion_gates_unmet',review_status='still_pass_motion_gates_unmet'if still else'still_gap_motion_gates_unmet',review_note=note,motion_approved=False,train_eligible=False,training_ran=False)
 c['independent_still_review']={'identity_bar_met':identity,'source_framing_pose_bar_met':pose,'rounds':len(reviews),'evidence':reviews[-1].name};c['ledger_entries']=len(old);cfg['review_note']=note;write(OUT/'shot.json',s);write(OUT/'assembly-checks.json',c);write(OUT/'config.json',cfg)
 rows=[{'id':x,'value':'not run','unit':'','ok':None}for x in ['M1','M2','M2b','M5','M6','J1','J2','J3']]
 rows += [{'id':'S6','value':'Source IDs, archive URLs, retained interval, raw SHA256 and archive-reported rights preserved; rights independently unverified','unit':'','ok':True},{'id':'J4','value':{'rounds':len(reviews),'identity':identity,'sampled_pose':pose,'normal_speed_playback_watched':False},'unit':'sampled still scope only','ok':identity},{'id':'B1','value':'Static scenery is held; separately credited source-observed animated operation/props retain exposure sequences. No world-geometry solve for per-frame projected props.','unit':'static scenery scope only','ok':None if ROOT.name in ['roller-coaster','skateboard']else True},{'id':'T1','value':tr,'unit':'fraction','ok':tr['pass']},{'id':'T3','value':c['native_topology'],'unit':'original native stroke IDs and pointcounts','ok':c['native_topology']},{'id':'M3','value':{'mean_iou':None,'min_iou':None,'reason':'Audited final same-instance render/mask fit not run; source segmentation target caveats retained.'},'unit':'IoU','ok':None},{'id':'M4','value':0,'unit':'verified planted intervals;minimum4','ok':False},{'id':'S1','value':'Camera and scenery are separated; independent depth ordering unmeasured','unit':'','ok':None},{'id':'S2','value':'Native QuickDraw identity and separately credited operational props retained in compatibility/source records','unit':'','ok':True},{'id':'S3','value':{'frames':s['frame_count'],'fps':s['fps'],'keys':len(s['keys']),'source_time_every_frame':True},'unit':'','ok':True},{'id':'S4','value':'Static local links/JS checked; actual390px browser inspection not performed','unit':'','ok':None},{'id':'S5','value':'Native paper fills where configured; occlusion and projected prop depth not independently solved','unit':'','ok':None},{'id':'S7','value':len(old),'unit':'hash-linked ledger entries','ok':True}]
 write(ROOT/'tests.json',rows)
 sys.path.insert(0,str(REPO/'tools'));import integrated_batch;integrated_batch.build_page(OUT,s,cfg)
 html=(OUT/'index.html').read_text();html=html.replace('<h2>Source and keyframe checks</h2>','<p><a href=\"'+reviews[-1].name+'\">Read the independent still review</a> · <a href=\"../ledger.jsonl\">Repair ledger</a> · <a href=\"../tests.json\">All gate results</a></p><h2>Source and keyframe checks</h2>');(OUT/'index.html').write_text(html)
 (ROOT/'README-integrated.md').write_text('# '+s['title']+'\n\n'+note+'\n\n'+s['assembly_summary']+'\n\nOriginal source/study/design files remain unchanged. The frozen input snapshot and every reviewed version live in integrated/. Reproduce using build_integrated.py --source /path/to/raw.mp4. Native extra strokes are credited separately.\n')
 print(json.dumps({'subject':ROOT.name,'still_pass':still,'trace_pass':tr['pass'],'ledger_entries':len(old)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot');args=p.parse_args()
 snapshot(args.snapshot)if args.snapshot else finalize()
