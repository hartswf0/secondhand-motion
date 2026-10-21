"""Freeze each candidate and record proposals/blind still reviews without motion acceptance."""
from pathlib import Path
import argparse,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1];OUT=ROOT/'integrated'
spec=importlib.util.spec_from_file_location('loop',REPO/'batches/2026-10-20-selected-drawings/loop.py');loop=importlib.util.module_from_spec(spec);spec.loader.exec_module(loop)
def read(p):return json.loads(p.read_text())
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def load_ledger():
 p=ROOT/'ledger.jsonl'
 if not p.exists():loop.init_ledger(p)
 with p.open()as h:return loop.read_ledger(h)
def freeze(revision):
 target=OUT/'revisions'/revision
 if not target.exists():
  target.mkdir(parents=True)
  for p in OUT.iterdir():
   if p.name in ['revisions'] or p.name.startswith('.'):continue
   if p.is_dir():shutil.copytree(p,target/p.name)
   elif p.is_file():shutil.copy2(p,target/p.name)
 return target

def run(revision,review=None,details='Source-observed native vectors assembled with separately held scenery and camera.'):
 s=read(OUT/'shot.json');c=read(OUT/'assembly-checks.json');config=read(OUT/'config.json');base=freeze(revision);rel=str(base.relative_to(ROOT));old=load_ledger();r=read(review)if review else None
 ident=r.get('original_doodle_identity_bar_met',r.get('identity_bar_met'))if r else None;pose=r.get('source_framing_pose_bar_met')if r else None
 if r:
  shutil.copy2(review,base/'blind-review.json');gap=r.get('most_important_gap',r.get('gap','Still review gap unspecified.'));protected=r.get('must_not_be_lost',[]);protected=[protected]if isinstance(protected,str)else protected
 else:gap='Independent identity/source-pose review and actual normal-speed playback pending.';protected=['Locked native doodle topology, source interval and source camera/crop.']
 tests=[{'name':'complete_decode','status':'pass','constraint':True,'value':s['frame_count'],'unit':'decoded frames','evidence_refs':[rel+'/video-validation.json']},{'name':'trace_fidelity','status':'pass'if c['trace_fidelity']['pass']else'fail','constraint':True,'value':c['trace_fidelity']['min_recall'],'unit':'minimum key recall','evidence_refs':[rel+'/traced.json']},{'name':'native_topology','status':'pass'if c['native_topology']else'fail','constraint':True},{'name':'mask_fit','status':'unknown','constraint':True,'metric':'No audited final-render mask fit evaluated; legacy contour proxies do not clear the gate.'},{'name':'planted_contacts','status':'fail','constraint':True,'value':0,'unit':'verified intervals; minimum4'},{'name':'recognition','status':'unknown','constraint':True},{'name':'normal_speed_playback','status':'unknown','constraint':True}]
 rev=ROOT.name+'-'+revision+('-blind'if r else'-proposal')
 if not any(e['input']['revision']==rev for e in old):
  raw={'revision':rev,'parent':old[-1]['input']['revision']if old else None,'observation_refs':[rel+'/source.json',rel+'/source-contact-sheet.jpg',rel+'/design.png'],'evidence_refs':[rel+'/blind-review.json'if r else rel+'/assembly-checks.json'],'action':{'type':'redraw_key'if review else'change_layer','details':details},'before_refs':['design.png']if not old else[old[-1]['input']['after_refs'][0]],'after_refs':[rel+'/shot.json',rel+'/comparison.mp4'],'source':{'identity':s['source']['clip_id'],'interval':{'start':config['interval'][0],'end':config['interval'][1],'unit':'seconds'}},'claims':['drawing','motion'],'source_event_preserved':'unknown','drawing_identity_preserved':ident if isinstance(ident,bool)else'unknown','train_eligible':False,'measured_tests':tests,'critic':{'scope':['drawing_identity','sampled_source_framing_pose']if r else['proposal_unreviewed'],'verdict':'bar_met'if r and ident and pose else'bar_not_met'if r else'uncertain','gap':gap,'protected_strengths':protected,'independent':bool(r)}};loop.record(raw,ROOT/'ledger.jsonl');old=load_ledger()
 static=[o for o in s.get('scene_objects',[])if not o.get('frames')];b1=bool(static)and c['held_background_geometry'];c['held_background_gate']={'pass':b1,'static_objects_measured':len(static),'scope':'Static frozen scenery only; separate camera motion, no regenerated background. Zero static geometry does not pass.'};c['independent_still_review']={'identity':ident,'sampled_source_pose':pose,'normal_speed_playback_watched':False,'review':review.name if review else None};c['ledger_entries']=len(old)
 rows=[{'id':x,'value':'not run','unit':'','ok':None}for x in ['M1','M2','M2b','M5','M6','J1','J2','J3']]
 rows += [{'id':'T1','value':c['trace_fidelity'],'unit':'fraction','ok':c['trace_fidelity']['pass']},{'id':'T3','value':{'native_topology':c['native_topology'],'point_counts':read(OUT/'correspondence.json')['original_point_counts']},'unit':'','ok':c['native_topology']},{'id':'B1','value':c['held_background_gate'],'unit':'','ok':b1},{'id':'M3','value':{'mean_iou':None,'min_iou':None,'reason':'Not measured against audited same-instance final-render target'},'unit':'IoU','ok':False},{'id':'M4','value':0,'unit':'verified planted intervals; minimum4','ok':False},{'id':'J4','value':{'identity':ident,'sampled_pose':pose,'normal_speed_playback_watched':False},'unit':'sampled still scope only','ok':ident},{'id':'S1','value':'Depth planes retained from frozen study; no independent current parallax ordering check','unit':'','ok':None},{'id':'S2','value':'Native doodle key '+str(s['design']['key_id'])+' and separately source-credited frozen scene objects; optional extras explicitly credited','unit':'','ok':True},{'id':'S3','value':{'frames':s['frame_count'],'fps':s['fps'],'source_time_every_frame':True,'keys':s['keys']},'unit':'','ok':True},{'id':'S4','value':'Offline links/scripts checked by artifact verifier; no actual mobile browser observation','unit':'','ok':None},{'id':'S5','value':'Native closed fill strokes occlude scenery; separate independent occlusion audit not run','unit':'','ok':None},{'id':'S6','value':'Raw source SHA256, decoded PTS, original archive ids/URLs/reported rights and QuickDrawCCBY retained','unit':'','ok':True},{'id':'S7','value':len(old),'unit':'verified hash-linked ledger entries','ok':True}]
 dump(ROOT/'tests.json',rows);dump(OUT/'assembly-checks.json',c)
 if r:
  s['review_status']='still_pass_motion_gates_unmet'if ident and pose else'still_gap_motion_gates_unmet';s['review_note']=('Fresh blind still review passes native identity and sampled source framing/pose. 'if ident and pose else'Fresh blind still review leaves a gap: '+str(gap)+' ')+'Classifier, audited final mask fit, verified contacts and actual normal-speed playback remain unmet/unrun. No training ran.';s['status']='assembled_'+s['review_status'];dump(OUT/'shot.json',s);config['review_note']=s['review_note'];dump(OUT/'config.json',config)
  sys.path.insert(0,str(REPO/'tools'));import integrated_batch;integrated_batch.build_page(OUT,s,config)
 print(json.dumps({'subject':ROOT.name,'revision':revision,'review':bool(r),'identity':ident,'source_pose':pose,'ledger_entries':len(old),'background_gate':b1}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',default='v1');p.add_argument('--review',type=Path);p.add_argument('--details',default='Source-observed native vectors assembled with separately held scenery/camera.');a=p.parse_args();run(a.revision,a.review,a.details)
