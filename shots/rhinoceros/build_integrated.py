"""Rebuild this source-paired native review from its frozen inputs."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'tools'))
from integrated_batch import build
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path);p.add_argument('--config',type=Path,default=ROOT/'integrated/config.json');a=p.parse_args()
clip=json.loads((ROOT/'integrated/input/clip.json').read_text())
source=a.source or REPO.parent/'mia-quickdraw-dataset/videos'/(clip['clip_id']+'.mp4')
build(ROOT.name,a.config,source)
