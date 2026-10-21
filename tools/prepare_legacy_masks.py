"""Expose pinned legacy SAM polygon exports as explicitly lossy mask proxies.

These filled contour approximations are not the original binary SAM masks.
No drawing-fit, identity, contact or playback gate is approved by this conversion.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
import cv2
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent.parent
cv2.setNumThreads(1)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def convert(slug,commit):
 src=ROOT/'shots'/f'{slug}-sam';out=ROOT/'shots/wave2-segmentation/data'/slug;out.mkdir(parents=True,exist_ok=True);(out/'frames').mkdir(exist_ok=True)
 clip=json.loads((src/'clip.json').read_text());polygons=json.loads((src/'masks.json').read_text());meta=json.loads((src/'mask_meta.json').read_text());rows={int(r['f']):r for r in meta['frames']};W,H=clip['W'],clip['H'];frames=[]
 for i in range(clip['n']):
  mask=np.zeros((H,W),np.uint8);ps=polygons.get(str(i),[])
  if ps:cv2.fillPoly(mask,[np.asarray(p,np.int32) for p in ps],1)
  flat=mask.ravel();cuts=np.r_[0,np.flatnonzero(np.diff(flat.astype(np.int8)))+1,len(flat)];runs=np.diff(cuts).tolist()
  if flat[0]:runs=[0]+runs
  assert sum(runs)==W*H
  row=rows.get(i,{});frames.append({'f':i,'W':W,'H':H,'rle':runs,'area':int(mask.sum()),'box':row.get('box'),'iou':row.get('iou',0),'from':row.get('from','legacy SAM export'),'representation':'Filled exported contours; lossy proxy, not original binary SAM mask'})
  shutil.copy2(src/'frames'/f'f{i:03d}.jpg',out/'frames'/f'f{i:03d}.jpg')
 (out/'clip.json').write_text(json.dumps(clip,indent=2)+'\n');(out/'track.json').write_text(json.dumps({'mask_representation':'polygon-derived proxy','frames':frames},separators=(',',':'))+'\n')
 provenance={'branch':'main (legacy SAM polygon export)','commit':commit,'track_sha256':sha(out/'track.json'),'legacy_polygon_sha256':sha(src/'masks.json'),'legacy_meta_sha256':sha(src/'mask_meta.json'),'legacy_frame_clock':'approximate clip.t0 + frame / clip.fps; original decoded CI PTS and input-video hash unavailable','mask_representation':'Filled exported SAM contours. Export simplified boundaries and discarded small components; original binary masks cannot be recovered.','legacy_method_reported':meta['method'],'legacy_source_paths':[f'shots/{slug}-sam/{n}' for n in ['clip.json','masks.json','mask_meta.json']]}
 (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');return clip,frames
def sheet(slugs,output):
 sheet=Image.new('RGB',(1536,len(slugs)*174),'#f5f1e8');draw=ImageDraw.Draw(sheet)
 for r,s in enumerate(slugs):
  folder=ROOT/'shots/wave2-segmentation/data'/s;c=json.loads((folder/'clip.json').read_text());frames=json.loads((folder/'track.json').read_text())['frames'];indices=[0,round((c['n']-1)/3),round(2*(c['n']-1)/3),c['n']-1]
  for col,i in enumerate(indices):
   im=Image.open(folder/'frames'/f'f{i:03d}.jpg').convert('RGB');f=frames[i];flat=np.zeros(f['W']*f['H'],np.uint8);pos=0;bit=0
   for n in f['rle']:
    if bit:flat[pos:pos+n]=1
    pos+=n;bit=1-bit
   pixels=np.asarray(im).copy();mask=flat.reshape(f['H'],f['W']).astype(bool);pixels[mask]=(pixels[mask]*.55+np.array([255,25,35])*.45).astype(np.uint8);x=col*384;y=r*174
   draw.text((x+4,y+4),f'{s} | sample {i} | nominal {c["t0"]+i/c["fps"]:.3f}s',fill='#171512');sheet.paste(im.resize((192,144)),(x,y+25));sheet.paste(Image.fromarray(pixels).resize((192,144)),(x+192,y+25))
 output.parent.mkdir(parents=True,exist_ok=True);sheet.save(output,quality=94)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('subjects',nargs='+');p.add_argument('--sheets',type=Path);a=p.parse_args();commit=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip()
 for s in a.subjects:
  c,f=convert(s,commit);print(s,len(f))
 if a.sheets:
  for i in range(0,len(a.subjects),5):sheet(a.subjects[i:i+5],a.sheets/f'legacy-audit-{i//5+1}.jpg')
