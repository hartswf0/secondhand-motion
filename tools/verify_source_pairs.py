"""Check saved source photographs and movie panels against pinned raw video.

Unlike internal movie/key checks, this independently checks the external source,
nearest decoded PTS, viewport size and common crop. It does not approve motion.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
import cv2,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
JPEG_MAE_LIMIT=5.0
MOVIE_MAE_LIMIT=3.0
cv2.setNumThreads(1)
def capture(path):
 return cv2.VideoCapture(str(path),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]) if hasattr(cv2,'CAP_PROP_N_THREADS') else cv2.VideoCapture(str(path))
def expected_image(bgr,W,H,crop):
 image=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));scale=min(W/image.width,H/image.height);image=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
 result=Image.new('RGB',(W,H),'#fffdf7');result.paste(image,((W-image.width)//2,(H-image.height)//2))
 if crop:result=result.crop(tuple(crop)).resize((W,H),Image.Resampling.LANCZOS)
 return np.asarray(result)
def check(subject,sources):
 base=ROOT/'shots'/subject/'integrated';shot=json.loads((base/'shot.json').read_text());config=json.loads((base/'config.json').read_text());record=json.loads((base/'source.json').read_text());raw=sources/(record['clip_id']+'.mp4');assert hashlib.sha256(raw.read_bytes()).hexdigest()==record['source_sha256']
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(raw)],text=True));pts=[float(f['best_effort_timestamp_time'])for f in probe['frames']];need={shot['frames'][k]['source_frame_index']for k in shot['keys']};frames={};cap=capture(raw);i=0
 while True:
  ok,bgr=cap.read()
  if not ok:break
  if i in need:frames[i]=bgr
  i+=1
 cap.release();assert need<=set(frames)
 panel_frames={};cap=capture(base/'comparison.mp4');i=0
 while True:
  ok,bgr=cap.read()
  if not ok:break
  if i in shot['keys']:panel_frames[i]=cv2.cvtColor(bgr[24:,:shot['W']],cv2.COLOR_BGR2RGB)
  i+=1
 cap.release();rows=[]
 for ordinal,k in enumerate(shot['keys'],1):
  frame=shot['frames'][k];idx=frame['source_frame_index'];assert abs(pts[idx]-frame['source_index_time'])<1e-5;assert idx==int(np.argmin(np.abs(np.asarray(pts)-frame['source_time']))),'Not nearest actual source PTS'
  expected=expected_image(frames[idx],shot['W'],shot['H'],config.get('crop'));photo=np.asarray(Image.open(base/f'source-{ordinal:02d}.jpg').convert('RGB'));movie=panel_frames[k];assert expected.shape==photo.shape==movie.shape
  photo_error=float(np.abs(expected.astype(float)-photo).mean());movie_error=float(np.abs(expected.astype(float)-movie).mean());assert photo_error<JPEG_MAE_LIMIT,(subject,ordinal,'source photograph',photo_error);assert movie_error<MOVIE_MAE_LIMIT,(subject,ordinal,'source movie panel',movie_error)
  rows.append({'key':ordinal,'render_frame':k,'actual_source_index':idx,'actual_source_pts':pts[idx],'photo_rgb_mae':round(photo_error,6),'movie_panel_rgb_mae':round(movie_error,6)})
 return {'subject':subject,'source_pair_integrity':True,'raw_source_sha256':record['source_sha256'],'keys_checked':len(rows),'checks':rows,'scope':'Source bytes, nearest decoded PTS and image viewport only. No artistic or motion approval.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('subjects',nargs='+');p.add_argument('--sources',type=Path,default=ROOT.parent/'mia-quickdraw-dataset/videos');args=p.parse_args();print(json.dumps([check(s,args.sources)for s in args.subjects],indent=2,allow_nan=False))
