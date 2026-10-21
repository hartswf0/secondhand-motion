"""Reproduce this integrated candidate from pinned native inputs and source bytes."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'tools'))
from integrated_batch import build
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--config',type=Path,default=ROOT/'integrated/config.json');a=p.parse_args();build(ROOT.name,a.config,a.source)
