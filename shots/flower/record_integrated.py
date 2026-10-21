"""Record a frozen integrated repair and raw independent review; no training."""
from pathlib import Path
import json,sys,argparse,hashlib,shutil,importlib.util
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1];OUT=ROOT/'integrated'
def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def flag(d,keys):
 for k in keys:
  if d.get(k) is True:return True
  if d.get(k) is False:return False
 return None
def run(revision,review=None):
 shot=read(OUT/'shot.json');checks=read(OUT/'assembly-checks.json');raw=read(review)if review else {};identity=flag(raw,['identity_bar_met','original_doodle_identity_bar_met','original_doodle_identity']);pose=flag(raw,['source_framing_pose_bar_met','source_pose_bar_met','sampled_source_pose_bar_met']);watched=flag(raw,['normal_speed_playback_watched','actually_viewed_normal_speed_motion','playback_watched']) is True;motion=watched and raw.get('motion_approved')is True
 gap=raw.get('most_important_gap',raw.get('gap','Fresh independent review pending.'))
 if isinstance(gap,dict):gap=json.dumps(gap)
 cfg=read(OUT/'config.json');cfg.update(revision='integrated-'+revision,review_status='review_candidate',review_note=f"Native identity {'passes'if identity is True else 'fails'if identity is False else 'unreviewed'}; sampled source pose {'passes'if pose is True else 'fails'if pose is False else 'unreviewed'}. {gap} Normal-speed motion remains unapproved; classifier unrun. No training ran.")
 write(OUT/'config.json',cfg)
 sys.path.insert(0,str(REPO/'tools'));import integrated_batch
 integrated_batch.refresh_page(OUT/'config.json')
 shot=read(OUT/'shot.json');checks=read(OUT/'assembly-checks.json');trace=checks['trace_fidelity'];scene=read(OUT/'input/gwp-shot.json');bg_strokes=sum(len(o.get('strokes',[]))for o in scene.get('objects',[])if not o.get('frames'))
 rows=[{'id':i,'value':'not run','unit':'','ok':None}for i in ['M1','M2','M2b','M5','M6','J1','J2','J3']]
 def add(i,v,ok,unit=''):rows.append({'id':i,'value':v,'unit':unit,'ok':ok})
 add('S6','Clip/source ids, reported rights, URLs, rawSHA256 and retained decoded source times preserved',True)
 add('J4',{'identity':identity,'sampled_source_pose':pose,'raw_review':Path(review).name if review else None,'normal_speed_playback_watched':watched},identity,'independent still scope only')
 add('B1',{'held_world_background':True,'static_authored_strokes':bg_strokes,'scope':'Held world geometry with separate recorded camera; no pixel/stroke matching run'if bg_strokes else 'Blank heldpaper; no authored background ink to measure'},False if bg_strokes==0 else None)
 add('T1',trace,trace['pass'],'fraction')
 add('T3',{'native_topology':checks.get('native_topology'),'scope':'Explicit native point correspondence retained; registry Hungarian matched-ink metric unrun'},None)
 add('M3',checks.get('mask_fit'),False,'unmeasured against audited final render')
 add('M4',0,False,'verified planted intervals; minimum4')
 add('S1','Depth planes retained from source-observed study; ordering not independently measured',None)
 add('S2','All native/extra/scenery sources retained in frozen input and editable timeline',True)
 add('S3',{'frames':shot['frame_count'],'keys':len(shot['keys']),'source_time_every_frame':True},True)
 add('S4','Offline relative links/script syntax checked by technical verifier; actual phone viewport unrun',None)
 add('S5','Native/background occlusion not independently verified',None)
 checks['independent_still_review']={'identity':identity,'sampled_source_pose':pose,'raw_review':str(Path(review).name)if review else None};checks['motion_approved']=False;checks['training_ran']=False
 checks['background_strokes_checked']=bg_strokes
 if bg_strokes==0:checks['held_background_geometry']=False;checks['background_strokes_unchanged_fraction']=None;checks['background_gate_scope']='Blank held paper; no authored background ink to measure; zero inventory cannot pass B1'
 write(OUT/'assembly-checks.json',checks)
 # Freeze full exact candidate BEFORE recording an immutable evidence reference.
 dest=OUT/'revisions'/revision
 if dest.exists():raise RuntimeError('Revision already frozen; do not overwrite')
 shutil.copytree(OUT,dest,ignore=shutil.ignore_patterns('revisions','__pycache__','*.tmp.mp4','.*render*'))
 write(dest/'snapshot-sha256.json',{str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.rglob('*')if p.is_file()})
 spec=importlib.util.spec_from_file_location('ledger_loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop);ledger=ROOT/'ledger.jsonl'
 if not ledger.exists():loop.init_ledger(ledger)
 with ledger.open() as f:old=loop.read_ledger(f)
 prefix=str(dest.relative_to(REPO));src=shot['source'];refs=[prefix+'/'+p for p in ['shot.json','source.json','design.json','config.json','assembly-checks.json','snapshot-sha256.json']];review_ref=prefix+'/'+Path(review).name if review else prefix+'/config.json'
 candidate={'revision':'integrated-'+revision,'parent':old[-1]['input']['revision']if old else None,'observation_refs':[prefix+'/source-contact-sheet.jpg',prefix+'/source.json'],'evidence_refs':[review_ref,prefix+'/assembly-checks.json'],'action':{'type':'redraw_key','details':cfg['assembly_summary']},'before_refs':[str(OUT.relative_to(REPO))+'/input/gwp-original.json']if not old else old[-1]['input']['after_refs'],'after_refs':refs,'source':{'identity':src['clip_id'],'interval':{'start':src['start_seconds'],'end':src['end_seconds'],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':'unknown','drawing_identity_preserved':identity if identity is not None else 'unknown','train_eligible':False,'measured_tests':[{'name':'trace','status':'pass'if trace['pass']else'fail','constraint':True,'value':trace['min_recall'],'unit':'fraction'},{'name':'held_background_ink_inventory','status':'fail'if bg_strokes==0 else'unknown','constraint':True,'value':bg_strokes,'unit':'static authored strokes'},{'name':'mask_fit','status':'unknown','constraint':True},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'verified intervals'},{'name':'recognition','status':'unknown','constraint':True},{'name':'native_topology','status':'pass'if checks.get('native_topology')else'fail','constraint':True}],'critic':{'scope':['drawing identity','source-pose stills']if review else[],'verdict':'bar_not_met'if identity is False or pose is False else'uncertain','gap':gap,'protected_strengths':['Native construction and source event phases retained as recorded'],'independent':bool(review)}}
 entry=loop.record(candidate,ledger);add('S7',len(old)+1,True,'hash-linked entries');write(ROOT/'tests.json',rows)
 print(ROOT.name,revision,'identity',identity,'pose',pose,'ledger',entry['id'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--review',type=Path);a=p.parse_args();run(a.revision,a.review)
