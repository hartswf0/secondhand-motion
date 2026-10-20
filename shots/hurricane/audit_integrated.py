"""Trace all eight isolated effects with the repository's unchanged default tracer."""
from pathlib import Path
import importlib.util,json
from PIL import Image
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'integrated';REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('trace_keys',REPO/'tools/trace_keys.py');trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace)
keys=[]
for path in sorted(OUT.glob('character-key-*.png')):
 im=Image.open(path);st,ink,hw=trace.trace(im);recall,precision,parts=trace.score(st,ink,*im.size,hw)
 keys.append(dict(file=path.name,strokes=st,n_strokes=len(st),recall=recall,precision=precision,parts_kept=parts,half_width=hw))
assert len(keys)==8
result=dict(tool='tools/trace_keys.py, unchanged default parameters',W=480,H=360,keys=keys)
(OUT/'traced.json').write_text(json.dumps(result,indent=2)+'\n')
metrics=dict(keys=len(keys),min_recall=min(k['recall'] for k in keys),min_parts_kept=min(k['parts_kept'] for k in keys),recall_bar=.98,parts_bar=1.0)
metrics['pass']=metrics['min_recall']>=.98 and metrics['min_parts_kept']==1.0
checks=json.loads((OUT/'assembly-checks.json').read_text());checks['trace_fidelity']=metrics
(OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(metrics))
