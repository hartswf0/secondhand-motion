"""Per-frame RMS radius and centre of the built dragon drawing (the quantities tools/pops.py steps on)."""
import json, numpy as np
S=json.load(open('shots/dragon-gwp/shot.json'))
for i,fr in enumerate(S['cast']['frames']):
    P=np.concatenate([np.array(s,float) for s in fr if len(s)]); c=P.mean(0); R=np.sqrt(((P-c)**2).sum(1).mean())
    print(i, round(R,1), c.round(1))
