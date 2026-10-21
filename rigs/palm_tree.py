"""palm_tree rig: the chosen doodle itself (rigs/palm_tree_spec.json), bent by pose points. See template_rig.py."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from template_rig import TemplateRig
_R = TemplateRig(Path(__file__).parent / 'palm_tree_spec.json')
POINTS = _R.POINTS


def draw(pose, prm=None): return _R.draw(pose, prm)
