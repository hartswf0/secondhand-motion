from pathlib import Path
import json
import loop
R=Path(__file__).resolve().parent
ledger=R/'data/repair-ledger.jsonl'
if not ledger.exists():loop.init_ledger(ledger)
with ledger.open() as f: existing={x['input']['revision'] for x in loop.read_ledger(f)}
for cat in ['cat','dog','horse','rabbit','butterfly','duck','bicycle','windmill','helicopter']:
 meta=json.loads((R/f'subjects/{cat}/source.json').read_text());end=3 if cat=='butterfly' else 2
 for version in range(1,end+1):
  v='v'+str(version)
  if cat+'-'+v in existing:continue
  review_path=f'reviews/{cat}-{v}.json';review=json.loads((R/review_path).read_text())
  gap=review.get('main_gap',review.get('consequential_gap','See review.'))
  if not isinstance(gap,str):gap=json.dumps(gap,ensure_ascii=False)
  record={'revision':cat+'-'+v,'parent':cat+'-v'+str(version-1) if version>1 else None,'claims':['drawing'],'observation_refs':[f'subjects/{cat}/source-keys.png',f'subjects/{cat}/design.png'],'evidence_refs':[review_path,f'subjects/{cat}/revisions/prompt-{v}.txt'],'action':{'type':'redraw_key','details':'Draw four source-related poses in selected identity.' if version==1 else 'Apply the bounded cause-directed repair documented by the previous review; exact instruction retained in prompt.'},'before_refs':[f'subjects/{cat}/revisions/keys-v{version-1}.png' if version>1 else f'subjects/{cat}/design.png'],'after_refs':[f'subjects/{cat}/revisions/keys-{v}.png'],'source':{'identity':meta['source']['clip_id'],'interval':{'start':meta['key_times'][0],'end':meta['key_times'][-1]+.1,'unit':'seconds'}},'source_event_preserved':True if review['verdict']=='bar_met' else 'unknown','drawing_identity_preserved':True if review['verdict']=='bar_met' else 'unknown','train_eligible':False,'critic':{'scope':['stills','drawing','source_comparison'],'verdict':'bar_met' if review['verdict']=='bar_met' else 'bar_not_met' if review['verdict']=='reference_stronger' else 'uncertain','gap':gap,'protected_strengths':review.get('protected_strengths',[]),'independent':True}}
  loop.record(record,ledger)
selection=loop.select(ledger);(R/'data/ledger-selection.json').write_text(json.dumps(selection,indent=2));print('Recorded',len(selection['candidates']),'actual draw/critique episodes; new subjects accepted',sum(x['status']=='accepted' for x in selection['candidates']))
