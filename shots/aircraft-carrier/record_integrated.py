"""Append bounded integrated proposals/reviews; never mutate raw critic verdicts."""
from pathlib import Path
import argparse,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('repair_loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def frozen(n):
 base=OUT/'revisions'/f'v{n}'
 if not base.exists():
  base.mkdir(parents=True)
  for p in OUT.iterdir():
   if p.name=='revisions' or p.name.startswith('.'):continue
   if p.is_dir():shutil.copytree(p,base/p.name)
   else:shutil.copy2(p,base/p.name)
 return base

def main(n,kind,details):
 ledger=ROOT/'ledger.jsonl'
 if not ledger.exists():loop.init_ledger(ledger)
 with ledger.open()as h:old=loop.read_ledger(h)
 revision=f'{ROOT.name}-integrated-v{n}-{kind}'
 if any(e['input']['revision']==revision for e in old):print('already recorded',revision);return
 base=frozen(n);check=read(base/'assembly-checks.json');src=read(base/'source.json');tr=check['trace_fidelity'];critic_file=OUT/f'review-v{n}.json'
 raw=read(critic_file)if kind=='review'else{}
 if kind=='review':shutil.copy2(critic_file,base/critic_file.name)
 identity=raw.get('original_doodle_identity_bar_met',raw.get('identity_bar_met','unknown'))
 pose=raw.get('source_framing_pose_bar_met','unknown');still=identity is True and pose is True
 protected=raw.get('must_not_be_lost',[]);protected=[protected]if isinstance(protected,str)else protected
 prefix=str(base.relative_to(ROOT))+'/'
 gap=raw.get('most_important_gap') or ('No sampled still gap identified; actual normal-speed playback, recognition and material contacts remain unapproved.' if raw else 'Independent critique pending; no actual normal-speed playback, classifier or contact verification.')
 entry={'revision':revision,'parent':old[-1]['input']['revision']if old else None,'observation_refs':['integrated/preflight-source-design.jpg','integrated/input/design.json','integrated/input/manifest.json'],'evidence_refs':[prefix+'assembly-checks.json']+([prefix+critic_file.name]if raw else[]),'action':{'type':'change_layer'if n==1 else'redraw_key','details':details or('Assemble frozen source-observed native vectors with exact decoded source photographs; retain held geometry, separate camera and explicit extra-stroke credits.'if kind=='proposal'else'Record unedited independent still critique; no motion approval inferred.')},'before_refs':['integrated/input/design.png']if n==1 else[f'integrated/revisions/v{n-1}/shot.json'],'after_refs':[prefix+'shot.json',prefix+'comparison.mp4'],'source':{'identity':src['clip_id'],'interval':{'start':src['start_seconds'],'end':src['end_seconds'],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':False if pose is False else'unknown','drawing_identity_preserved':identity,'train_eligible':False,'measured_tests':[{'name':'full_movie_decode','status':'pass','constraint':True,'value':check['rendered_frames'],'unit':'frames','evidence_refs':[prefix+'video-validation.json']},{'name':'character_trace','status':'pass'if tr['pass']else'fail','constraint':True,'value':tr['min_recall'],'unit':'minimum recall','evidence_refs':[prefix+'traced.json']},{'name':'native_topology','status':'pass'if check['native_topology']else'fail','constraint':True},{'name':'audited_same_instance_mask_fit','status':'unknown','constraint':True},{'name':'recognition_classifier','status':'unknown','constraint':True},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'independently verified planted intervals'},{'name':'independent_normal_speed_playback','status':'unknown','constraint':True}],'critic':{'scope':['original_doodle_identity_stills','sampled_source_framing_pose']if raw else[],'verdict':('bar_met'if still else'bar_not_met')if raw else'uncertain','gap':gap,'protected_strengths':protected,'independent':bool(raw)}}
 loop.record(entry,ledger)
 with ledger.open()as h:entries=loop.read_ledger(h)
 current=read(OUT/'shot.json');checks=read(OUT/'assembly-checks.json');reviews=sorted(OUT.glob('review-v*.json'))
 if raw:
  current['review_status']='still_pass_motion_gates_unmet'if still else'still_gap_motion_unapproved'
  current['review_note']=f'{len(reviews)} independent still review round(s). Native identity: {identity}; sampled source pose: {pose}. {gap} Normal-speed playback, classifier and verified material contacts remain unrun. No training ran.'
  checks['independent_still_review']={'rounds':len(reviews),'original_doodle_identity_bar_met':identity,'source_framing_pose_bar_met':pose,'evidence':critic_file.name}
  cfg=read(OUT/'config.json');cfg['review_note']=current['review_note'];cfg['review_status']=current['review_status'];write(OUT/'config.json',cfg)
 current.update(motion_approved=False,train_eligible=False,training_ran=False);checks['ledger_entries']=len(entries);write(OUT/'shot.json',current);write(OUT/'assembly-checks.json',checks)
 rows=[{'id':i,'value':'not run','unit':'','ok':None}for i in ['M1','M2','M2b','M5','M6','J1','J2','J3']]
 def row(i,v,ok=None,unit=''):rows.append(dict(id=i,value=v,unit=unit,ok=ok))
 row('S6','Archive ids, original URLs, reported rights, pinned raw SHA and refined source interval retained; rights independently unverified.',True)
 row('J4',{'rounds':len(reviews),'identity':identity,'sampled_source_pose':pose,'playback_watched':False},still if raw else None,'sampled still review only')
 row('B1',checks['background_strokes_unchanged_fraction'],checks['held_background_geometry'],'fraction of static background geometry unchanged; animated props separately credited')
 row('T1',tr,tr['pass'],'fraction');row('T3',{'native_topology':checks['native_topology'],'native_key_id':current['design']['key_id'],'explicit_extra_strokes':read(OUT/'compatibility.json').get('extras',[])},checks['native_topology'])
 row('M3',checks['mask_fit'],False,'audited target unavailable or not measured');row('M4',0,False,'verified planted intervals; minimum4')
 row('S1','Frozen source camera and depth planes preserved; no independent parallax verification.')
 row('S2','Native key credited; all scene geometry and extra strokes retain separate source records.',True)
 row('S3',{'frames':current['frame_count'],'fps':current['fps'],'keys':current['keys'],'source_time_every_frame':True},True)
 row('S4','Static links/scripts checked separately; actual390px browser layout unrun.')
 row('S5','Native fill regions may occlude held scene; complete actor/prop occlusion not independently reviewed.')
 row('S7',len(entries),True,'hash-linked append-only ledger entries');write(ROOT/'tests.json',rows)
 spec2=importlib.util.spec_from_file_location('integrated_batch',REPO/'tools/integrated_batch.py');engine=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(engine);engine.build_page(OUT,current,read(OUT/'config.json'))
 print(revision,len(entries),'ledgerentries',entry['critic']['verdict'])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--round',type=int,required=True);p.add_argument('--kind',choices=['proposal','review'],required=True);p.add_argument('--details',default='');a=p.parse_args();main(a.round,a.kind,a.details)
