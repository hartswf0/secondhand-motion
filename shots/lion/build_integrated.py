"""Rebuild the source-paired native assembly from frozen input files."""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path);a=p.parse_args();plan=json.loads((ROOT/'integrated/input/plan.json').read_text());source=a.source or REPO.parent/'mia-quickdraw-dataset/videos'/(plan['clip_id']+'.mp4');subprocess.run([sys.executable,str(REPO/'tools/integrated_batch.py'),'--subject',ROOT.name,'--config',str(ROOT/'integrated/config.json'),'--source',str(source)],check=True)
