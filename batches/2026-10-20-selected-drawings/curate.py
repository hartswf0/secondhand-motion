from pathlib import Path
import json,shutil
R=Path(__file__).resolve().parent
intervals={'rabbit':[4.8,9.1],'duck':[.1,4.05],'horse':[4.3,8.0],'dog':[.2,4.3],'cat':[10.4,15.55],'butterfly':[9.2,15.7],'bicycle':[1.9,3.6],'windmill':[.3,4.8],'helicopter':[.2,4.0],'giraffe':[0,1.4]}
notes={'rabbit':'Entry, landing, crouch and exit retained; simplified the contour to preserve the blunt doodle identity.','duck':'Restored the near-frontal foreshortened bill in the third key; torso and feet remain planted.','horse':'Restored foreground rail masking while the muzzle descends toward hay.','dog':'Restored rear/left views in the first keys, preserving the angular dog and ground support.','cat':'Retained head-turn poses while simplifying the face to the selected polygon-eye doodle.','butterfly':'Removed invented wing spread and dense cell pattern; kept the folded wings and fingertip contact.','bicycle':'Restored the lower-row front-wheel crop while retaining crank/foot attachment.','windmill':'Retained the four-sail assembly and phase angles; simplified the sails into irregular paddles.','helicopter':'Restored the second key’s close-pass crop before the later recession.','giraffe':'Carried the earlier accepted still-key reconstruction; whole-skull turn remains understated.'}
items=[]
for cat,interval in intervals.items():
 rev='v3' if cat in ['butterfly','giraffe'] else 'v2';review_path=f'reviews/{cat}-{rev}.json';review=json.loads((R/review_path).read_text());assert review['verdict']=='bar_met',(cat,review['verdict'])
 items.append({'category':cat,'selected_revision':rev,'interval':interval,'key_bar':review['verdict'],'review_path':review_path,'note':notes[cat],'hero_key':{'rabbit':2,'duck':0,'horse':3,'dog':1,'cat':3,'butterfly':3,'bicycle':1,'windmill':3,'helicopter':0,'giraffe':2}[cat],'motion_bar':'unreviewed','train_eligible':False,'new_this_run':cat!='giraffe'})
(R/'data/curation.json').write_text(json.dumps({'scope':'Ten curated clips from temporal sample review of 24 candidate clips; not an exhaustive ranking of the archive. Nine new drawing episodes plus one carried giraffe checkpoint.','items':items},indent=2))
shutil.copy2(R.parent/'cartoon-keyframe-loop/loop.py',R/'loop.py');shutil.copy2(R.parent/'cartoon-keyframe-loop/schema.json',R/'schema.json')
print('10 selected subjects; 40 selected keys; stills-only acceptance')
