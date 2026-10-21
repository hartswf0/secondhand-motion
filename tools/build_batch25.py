"""Refresh batch25 catalogue records from actual reviewed assemblies.

Review records remain separate from technical integrity, playback and training.
This does not approve a shot or modify any original source/drawn/GWP lane.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
MANIFEST=ROOT/'production/batches/2026-10-20-batch25/manifest.json'
def build():
 batch=json.loads(MANIFEST.read_text());total_keys=total_frames=still_pass=0
 for candidate in batch['subjects']:
  out=ROOT/'shots'/candidate['slug']/'integrated';assert list(out.glob('review-v[123].json')), f"{candidate['slug']}: no valid blind review"
 for row in batch['subjects']:
  slug=row['slug'];folder=ROOT/'shots'/slug;out=folder/'integrated';shot=json.loads((out/'shot.json').read_text());design=json.loads((out/'design.json').read_text());source=json.loads((out/'source.json').read_text());checks=json.loads((out/'assembly-checks.json').read_text());reviews=sorted(out.glob('review-v[123].json'));assert reviews,f'{slug}: no valid blind review';selection=json.loads((out/'selection.json').read_text()) if (out/'selection.json').exists() else {};selected_review=out/selection['selected_review'] if selection.get('selected_review') else reviews[-1];assert selected_review in reviews;review=json.loads(selected_review.read_text());identity=review.get('identity_bar_met',review.get('original_doodle_identity_bar_met'));pose=review.get('source_framing_pose_bar_met');assert isinstance(identity,bool) and isinstance(pose,bool)
  k,n=len(shot['keys']),shot['frame_count'];total_keys+=k;total_frames+=n;passed=identity and pose;still_pass+=int(passed)
  row.update(status='integrated_review',keys=k,rendered_frames=n,fps=shot['fps'],source_interval=source['interval_seconds'],native_key_id=design['key_id'],identity_bar_met=identity,source_framing_pose_bar_met=pose,normal_speed_playback_watched=review.get('normal_speed_playback_watched',False),motion_approved=False,train_eligible=False,trace_pass=checks.get('trace_fidelity',{}).get('pass'),selected_blind_review=str(selected_review.relative_to(ROOT)),latest_blind_review=str(reviews[-1].relative_to(ROOT)),selection=selection,remaining_gap=review.get('most_important_gap','See raw blind review.'),mask_fit=checks.get('mask_fit',{}))
  blurb=f'{k} source-paired keys; {n} rendered frames at {shot["fps"]} fps. '+('Both sampled still checks pass.' if passed else 'A sampled identity or source-pose gap remains; see the raw review.')
  if row['trace_pass'] is False:blurb+=' Trace fidelity remains below its gate.'
  blurb+=' Playback approval pending.'
  item={'lot':row['lot'],'id':slug,'kind':'subject','title':row['title'],'category':source.get('category',slug.replace('-',' ')),'wave':5,'lane':'join','stage':4,'status':'in progress','added':batch['date'],'blurb':blurb,'cover':f'shots/{slug}/integrated/poster.png','cover_credit':f'Native Quick, Draw! key {design["key_id"]}; Quick, Draw! contributors / Google Creative Lab, CC BY 4.0. Source-observed scenery and operating props credited in the assembly.','links':[{'label':'Watch assembled comparison','href':f'shots/{slug}/integrated/index.html'},{'label':'Watch the new batch of 25','href':f'shots/batch-25.html#{slug}/comparison'},{'label':'Watch in shared player','href':f'shots/moving-drawings.html#{slug}/comparison'},{'label':'Inspect source / mask / drawing','href':f'shots/wave2-segmentation/index.html#{slug}'},{'label':'Vector study','href':f'pages/{slug}-gwp.html'},{'label':'Source record','href':f'shots/{slug}/integrated/source.json'}],'tests':f'shots/{slug}/tests.json','tags':['assembled review','batch 25','native QuickDraw','source paired']}
  (folder/'item.json').write_text(json.dumps(item,indent=2)+'\n')
 batch.update(actual_count=len(batch['subjects']),paired_keys=total_keys,rendered_frames=total_frames,sampled_still_pass=still_pass,motion_approved_count=0,train_eligible_count=0,scope='25 integrated review assemblies with independent still reviews. Technical verification and normal-speed motion approval are separate; no training ran.')
 MANIFEST.write_text(json.dumps(batch,indent=2)+'\n');print(f'Batch25: {total_keys} paired keys / {total_frames} frames / {still_pass} sampled still passes')
if __name__=='__main__':build()
