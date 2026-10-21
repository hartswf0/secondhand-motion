"""Publish only measured statuses; a still verdict never becomes playback approval."""
from pathlib import Path
import json,hashlib,numpy as np
R=Path(__file__).resolve().parent;D=R/'integrated'
s=json.loads((D/'shot.json').read_text());c=json.loads((D/'assembly-checks.json').read_text());reviews=sorted(D.glob('review-v*.json'));review=json.loads(reviews[-1].read_text());n=int(reviews[-1].stem.split('v')[-1]);f=c['mask_fit'];tr=c['trace_fidelity']
identity=review.get('identity_bar_met',review.get('drawing_identity_bar_met'));pose=review.get('source_framing_pose_bar_met',review.get('source_event_pose_bar_met'));gap=review.get('most_important_gap',review.get('one_gap_that_matters_most',review.get('gap','See unedited independent review.')))
s.update(revision=f'integrated-v{n}',review_status='review_only_constraints_unmet',review_badge='REVIEW ONLY · MOTION UNAPPROVED',review_note=f'Fresh blind v{n}: '+gap+' Recognition and normal-speed playback remain unrun; zero planted-contact intervals cannot pass the four-interval gate. No training ran.',motion_approved=False,train_eligible=False)
s['source']['actual_sampled_source_pts_interval_seconds']=[s['frames'][0]['source_index_time'],s['frames'][-1]['source_index_time']];s['source']['source_sampling']='Nearest decoded raw source frame to each 24fps logical source_time; actual frame index and PTS retained per frame.';(D/'source.json').write_text(json.dumps(s['source'],indent=2)+'\n')
s['independent_review']={'path':reviews[-1].name,'identity_still_bar_met':identity,'source_pose_still_bar_met':pose,'overall_bar_met':review.get('bar_met',False),'normal_speed_playback_approved':False}
(D/'shot.json').write_text(json.dumps(s,indent=2)+'\n')
jerk=float(np.linalg.norm(np.diff(np.array([a['pose']['crown']for a in s['frames']])*1.5,n=3,axis=0),axis=1).max())
c['crown_anchor_max_third_difference_px']=jerk;c['nose_jerk_gate']='not measured';(D/'assembly-checks.json').write_text(json.dumps(c,indent=2)+'\n')
entries=[json.loads(x)for x in(R/'ledger.jsonl').read_text().splitlines()if x.strip()]
def row(i,v,ok,unit='',method=None):
 a={'id':i,'value':v,'unit':unit,'ok':ok}
 if method:a['method']=method
 return a
rows=[row('S6','Archive source/interval/raw SHA and SAM pin retained; archive public-domain claim attributed',True),row('M1','not run',None),row('M2','not run',None),row('J4',f'Fresh blind v{n}: see unedited {reviews[-1].name}',identity),row('B1',1.0,True,'fraction','One identical held wall geometry, no assigned camera motion.'),row('T1',{'min_recall':tr['min_recall'],'min_parts_kept':tr['min_parts_kept'],'keys':tr['keys']},tr['pass'],'fraction','tools/trace_keys.py on separated character keys'),row('M3',{'mean':f['mean'],'min':f['min'],'frames':f['frames_measured']},f['pass'],'IoU','Filled native head/body/ears vs nearest approximate 12fps SAM target; source PTS independent.'),row('M4','0 independently observed planted intervals; minimum-four gate fails',False),row('M5','not run',None),row('M6','Nose-specific world-space jerk not measured; crown-anchor diagnostic is not this gate',None),row('S1','No independent depth/parallax validation; held wall',None),row('S2','12 native stroke identities and authored held wall are sourced in shot.json',True),row('S3',{'frames':s['frame_count'],'fps':s['fps'],'keys':s['keys'],'per_frame_source_times':True},True),row('S4','Local links/scripts checked; phone browser/playback unrun',None),row('S5','Body and far ears painted before the opaque head; inspected exact paired keys',True),row('J1','No independent normal-speed viewing',None),row('J2','not run',None),row('J3','not run',None),row('S7',len(entries),True,'verified hash-linked entries')]
(R/'tests.json').write_text(json.dumps(rows,indent=2)+'\n')
readme=f'''# Monkey: the same doodle lowers its head and returns

This is a review candidate, not an accepted training pair. No training ran.

- Source: *The Story* (1969), clip `{s['source']['clip_id']}`; raw interval .333333–3.5 s, excluding the opening dissolve. Sixteen actual source frames were inspected. Source framing is 4:3; render 480×360.
- Native Quick, Draw! monkey `{s['design']['key_id']}`, twelve original stroke identities and point counts in every dense frame. Contributors / Google Creative Lab, CC BY 4.0. Head, face mask, angular eye marks, mouth U and both ear constructions stay assigned. The tail exists in the cast but is outside the close-up crop, with no claim about its hidden source placement.
- Eleven source-event keys, 77 dense frames at 24 fps. Each dense frame records clip-relative source time, actual nearest decoded raw source frame index and timestamp. The x-sheet names lowering, low hold and return events. One held background is composited with separate character keys.
- Archive reports public domain; independent rights verification did not run. See source.json for archive URLs, film time and exact raw SHA.

## Reproduce

From the repository root:

```sh
python shots/monkey/build_integrated.py --source /path/to/0c93c28c-6d9b-53c2-8cc7-905df20ec940.mp4 --mask-cache /path/to/pinned/monkey
python shots/monkey/record_integrated.py
python shots/monkey/finalize_integrated.py
python shots/monkey/build_integrated_page.py
python tools/verify_integrated.py monkey
```

The source and SAM JSON are SHA-pinned. Rendering uses a unique temporary directory, fully decodes each final movie, verifies 77 frames and atomically replaces it. Boards are built after all movie writers and tracing finish. The player opens without a server and keeps the playback position when switching source/cartoon/comparison.

## Evidence and remaining gaps

Current independent review: `{reviews[-1].name}` (unedited). {gap}

Trace minimum recall {tr['min_recall']:.6f}, ink pieces retained {tr['min_parts_kept']:.3f}. Held background geometry is 100% unchanged. Filled rig/SAM fit mean {f['mean']:.6f}, minimum {f['min']:.6f}; original bars remain mean ≥.65, minimum ≥.45. The target is an approximate broad fur/body segmentation; CI nominal timestamps differ from raw PTS and are not continuity evidence.

Recognition was not run. No normal-speed motion approval is claimed. No independently observed planted-foot intervals are available in this close-up, so the minimum-four foot-contact gate fails. No depth/parallax validation or phone browser check ran. All rejected full revisions and unedited independent reviews remain available; the parent ledger is hash-linked and append-only. Still-image components and the overall animated bar are separate.

Assembly and final decode/key comparison reports contain measured results. Technical validation does not establish drawing recognition or approved motion.
'''
readme+='\nStage wall-clock durations were not instrumented; no duration measurements are claimed.\n';(D/'README.md').write_text(readme)
print({'revision':n,'identity':identity,'pose':pose,'jerk':jerk,'ledger':len(entries)})
