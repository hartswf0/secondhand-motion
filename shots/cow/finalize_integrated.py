"""Attach real review outcomes and registry-shaped checks to current cow artifacts."""
from pathlib import Path
import json,subprocess,sys,importlib.util
import numpy as np
R=Path(__file__).resolve().parent;D=R/'integrated';s=json.loads((D/'shot.json').read_text());checks=json.loads((D/'assembly-checks.json').read_text());rev=int(s['revision'].split('v')[-1]);p=D/f'review-v{rev}.json';review=json.loads(p.read_text())if p.exists()else{}
identity=review.get('identity_bar_met');pose=review.get('source_framing_pose_bar_met');stillpass=identity is True and pose is True;gap=review.get('most_important_gap')or''
if stillpass:
 s.update(status='assembled_stills_pass_playback_pending',review_status='still_pass_fit_and_playback_pending',review_badge='STILLS PASS · FIT / MOTION GAPS',review_note='Independent review passes original-doodle identity and sampled source framing/pose. Filled-rig/SAM fit remains below its mean threshold. Normal-speed motion approval and recognition remain unrun. No training ran.')
else:
 s.update(status='assembled_review_gap',review_status='still_bar_not_met_playback_pending',review_badge='REVIEW GAP · MOTION UNAPPROVED',review_note=('Independent still review gap: '+gap+'. 'if gap else'Independent still review pending. ')+'Normal-speed motion approval and recognition remain unrun. No training ran.')
# Numerical arc gate reports exactly the controller position and sampling it measures.
poll=np.array([f['pose']['poll']for f in s['frames']]);jerk=np.linalg.norm(np.diff(poll,n=3,axis=0),axis=1)*1.5;maxjerk=float(jerk.max())
checks.update(independent_still_review={'identity_bar_met':identity,'source_framing_pose_bar_met':pose,'rounds':rev,'evidence':p.name,'scope':'Individual still keys and contact sheets; not normal-speed playback'},head_arc={'max_jerk':maxjerk,'unit':'render pixels per frame cubed','bar':4,'method':'Third finite difference of source-keyed poll anchor in 24fps 480x360 render coordinates','pass':maxjerk<4})
s['mask_fit']=checks['mask_fit'];s['head_arc']=checks['head_arc'];s['motion_approved']=False;s['train_eligible']=False
(D/'shot.json').write_text(json.dumps(s,indent=2)+'\n');(D/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
subprocess.run([sys.executable,str(R/'record_integrated.py')],check=True)
spec=importlib.util.spec_from_file_location('loop',R.parents[1]/'batches/2026-10-20-selected-drawings/loop.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with(R/'ledger.jsonl').open()as f:entries=m.read_ledger(f)
tr=checks['trace_fidelity'];fit=checks['mask_fit']
def row(id,value,ok,unit='',method=None):
 d={'id':id,'value':value,'unit':unit,'ok':ok}
 if method:d['method']=method
 return d
rows=[row('S6','Archive source/interval/hash retained; reported public-domain status explicitly attributed',True),row('M1','not run',None),row('M2','not run',None),row('J4',f'Fresh blind v{rev}: '+('same-drawing identity bar met on individual keys'if identity is True else'identity bar not met'if identity is False else'identity not reviewed'),identity),row('B1',1.0,True,'fraction','One literal background geometry string is reused unchanged across every frame; no camera transform.'),row('T1',{'min_recall':tr['min_recall'],'min_parts_kept':tr['min_parts_kept'],'keys':tr['keys']},tr['pass'],'fraction','tools/trace_keys.py on separated visible character PNGs'),row('M3',{'mean':fit['mean'],'min':fit['min'],'frames':fit['frames_measured']},fit['pass'],'IoU',fit['metric']+'; model estimates are not fit scores.'),row('M4','0 independently observed planted intervals; minimum-four gate fails',False),row('M5','not run',None),row('M6',maxjerk,maxjerk<4,'render px/frame^3',checks['head_arc']['method']),row('S1','No independent depth/parallax validation; held distant scene',None),row('S2','17 native cow stroke IDs and agent-drawn held sky/horizon sourced in integrated/shot.json',True),row('S3',{'frames':s['frame_count'],'fps':s['fps'],'keys':s['keys'],'per_frame_source_times':True},True),row('S4','Local links/scripts checked; no 390px browser layout or interactive playback check',None),row('S5','Far body lines painted before opaque face/muzzle; inspected ten source-key pairs',True),row('J1','No normal-speed blind viewing',None),row('J2','not run',None),row('J3','not run',None),row('S7',len(entries),True,'verified hash-linked entries')]
(R/'tests.json').write_text(json.dumps(rows,indent=2)+'\n')
readme=f'''# Cow: the cow chews toward us

Current review copy: `{s['revision']}`. Open `index.html` for the source/cartoon comparison and ten exact source-key pairs. {s['frame_count']} frames at24fps,3.5seconds. {s['review_note']}

The real Quick, Draw! design is key5459491900358656, credited to Quick, Draw! contributors / Google Creative Lab, CC BY4.0. All17original stroke IDs and original point counts are retained in every editable cast frame. Separate semantic mappings carry the head, eyes, ears, muzzle and mouth mark. Lower body strokes remain assigned but the source close-up crops most of them. This is authored vector adaptation, not a photographed silhouette outline.

The archive source is *Triple Goodness*(1948), clip1f60b8f5-a603-5713-b971-a95ca6401d04. Raw clip-relative interval1.5–5seconds; film-relative interval1313.38–1316.88seconds. The source film and declared public-domain status are attributed in source.json; independent rights verification has not run. SourceSHA256783ccd872a3c2f6ecc4d16b954bf2bb004a3b29e3a1819af9c48bcea115b65be.

Observed keys follow the early head turn and later opening/closing jaw extrema. Jaw position, ear placement and poll/muzzle anchors were read on decoded source grids; intermediate poses use monotone cubic interpolation. Individual keys establish sampled correspondence, not natural continuous performance. The background sky and horizon are drawn once. The scene is source-aspect4:3, rendered480×360.

Current separate-character trace minimum recall{tr['min_recall']:.6f},all pieces retained{tr['min_parts_kept']:.1f}. Filled-rig/SAM IoU mean{fit['mean']:.6f},minimum{fit['min']:.6f}; mean bar0.65 FAILS. SAM snapshot commit44af07db8fe9559e69b56fb94f65aa9179aca08c, fixed hashes in sam/provenance.json; audit.jpg shows four inspected samples. Broad head/ears are selected; dark shoulders are ragged. Model-estimated IoU does not measure drawing fit or jaw correctness. CI resampling timestamps are approximate.

Independent reviews are preserved unedited. v1identity failed because the broad native muzzle was lost; bounded v2widens that same polygon beyond the head while retaining placement and chew states. v2individual still identity and source framing/pose pass. Its reviewer caught a stale last image on the paired board; boards were regenerated from final key PNGs after writers exited, and decoded movie keyframes are checked separately in movie-key-audit.json. The individual key pixels reviewed are unchanged. No fourth or hidden revision is implied. v1 remains under revisions/v1; the append-only ledger retains every reviewed candidate. The ledger has two reviewed visual candidates and one append-only verdict-scope correction. The raw critic overall bar remains false; passing still components do not imply animated approval. All decisions remain rejected because applicable constraints are failed or unknown.

Rebuild from the exact original source bytes and committed SAM JSON:

```sh
python shots/cow/build_integrated.py --source /path/to/1f60b8f5-a603-5713-b971-a95ca6401d04.mp4
python shots/cow/finalize_integrated.py
python shots/cow/build_integrated_page.py
python shots/cow/audit_integrated.py
```

Optional `--mask-cache /path/to/cow-cache` imports the same pinned clip/track JSON. Renderer checks both source and snapshot hashes, uses a unique temporary directory, verifies all decoded frames before atomic movie installation, then generates paired boards after rendering completes. Rejected snapshots and review JSONs are not overwritten by this procedure. The review metadata must be re-evaluated if pixels change. No classifier inference, independent normal-speed playback approval, or training ran. Zero measured planted intervals is explicitly a failed foot-slide gate, not a no-contact pass. No accepted training pairs are exported.
'''
(D/'README.md').write_text(readme)
print('Cow metadata:',s['review_status'],'ledger',len(entries),'max poll jerk',maxjerk)
