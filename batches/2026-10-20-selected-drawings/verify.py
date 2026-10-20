"""Artifact and evidence-boundary checks; artistic verdicts come from critics."""
from pathlib import Path
from PIL import Image
import hashlib,json,math,subprocess
import loop
R=Path(__file__).resolve().parent
manifest=json.loads((R/'data/curation.json').read_text())['items'];assert len(manifest)==10
records=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for item in manifest:
 cat=item['category'];f=R/'subjects'/cat;review=json.loads((R/item['review_path']).read_text());assert review['verdict']==item['key_bar']=='bar_met'
 source=json.loads((f/'source.json').read_text());assert all(item['interval'][0]<=t<item['interval'][1] for t in source['key_times'])
 for k in range(4):assert Image.open(f/f'art-key-{k}.png').size==(384,288)
 assert len({sha(f/f'art-key-{k}.png') for k in range(4)})==4
 stats=[]
 for filename in ['source-excerpt.mp4','held-key-comparison.mp4']:
  p=f/filename;stream=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)]))['streams'][0]
  n=int(stream['nb_frames']);expected=math.ceil((item['interval'][1]-item['interval'][0])*12-1e-7)
  assert abs(n-expected)<=1,(cat,filename,n,expected)
  assert stream['height']==288 and stream['width']==(384 if filename.startswith('source') else 768)
  stats.append({'file':filename,'frames':n,'duration_seconds':float(stream['duration']),'sha256':sha(p)})
 records.append({'category':cat,'selected_revision':item['selected_revision'],'selected_art_sha256':sha(f/f"revisions/keys-{item['selected_revision']}.png"),'review':item['review_path'],'review_sha256':sha(R/item['review_path']),'accepted_scope':'four still keys','motion_scope':'not independently reviewed','media':stats})
selection=loop.select(R/'data/repair-ledger.jsonl');assert len(selection['candidates'])==19;assert sum(x['status']=='accepted' for x in selection['candidates'])==9;assert all(not x['train_eligible'] for x in selection['candidates'])
inline=Path('/workspace/cartoon-archive-selected-drawings.html');assert inline.stat().st_size<1000000
ui=json.loads(subprocess.check_output(['node',str(R/'test_inline.cjs'),str(inline)]));assert ui['passed']
gallery=json.loads((R/'data/gallery-data.json').read_text());assert [x['category'] for x in gallery['items']]==[x['category'] for x in manifest]
for record in gallery['items']:
 assert len(record['source_frames'])==len(record['source_frame_times'])>0
 for path in record['paths'].values():assert (R/path).is_file(),path
result={'artifact_checks_passed':True,'selected_subjects':10,'selected_key_drawings':40,'new_selected_drawings':36,'carried_giraffe_drawings':4,'new_image_generation_calls':19,'new_candidate_drawings':76,'new_repair_episodes':19,'accepted_new_still_key_episodes':9,'motion_acceptance':False,'actual_rl_training':False,'review_scope':'Independent fresh-context agent still reviews only; no normal-speed playback inspection.','ui_checks':ui,'inline_bytes':inline.stat().st_size,'ledger_sha256':sha(R/'data/repair-ledger.jsonl'),'subjects':records}
(R/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='subjects'},indent=2))
