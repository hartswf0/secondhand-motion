"""Rebuild the frozen source-paired native review; no training."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'tools'))
from integrated_batch import build
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--config',type=Path,default=ROOT/'integrated/config.json');a=p.parse_args();build(ROOT.name,a.config,a.source)
