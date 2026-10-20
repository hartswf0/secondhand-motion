"""Source-framed Quick, Draw! saucer borrowing a NASA CGI aeroshell attitude.

python shots/flying-saucer/build_integrated.py --source /path/to/flying-saucer.mp4
Input archive URL and required SHA-256 are in source.json. No training runs here.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, io, json, math, os, shutil, subprocess, tempfile
import cv2, numpy as np, cairosvg
from PIL import Image, ImageDraw
from scipy.signal import savgol_filter

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'integrated'; REPO=ROOT.parents[1]
SOURCE=REPO.parent/'wave2-logs/flying-saucer.mp4'
CACHE=REPO.parent/'wave2-track-cache/flying-saucer'
FPS=24; START=2.3356690023; END=4.5378712045; N=math.ceil((END-START)*FPS)
W,H=520,300; KEYS=[0,5,10,20,30,40,48,52]
D=json.loads((ROOT/'design.json').read_text()); ST=[np.column_stack(s).astype(float) for s in D['drawing']]
BG=[[[0,38],[25,27],[54,35],[69,24],[96,37]],[[0,79],[34,65],[59,76],[83,60]],
    [[0,149],[32,133],[55,148],[86,136]],[[0,213],[40,191],[68,207],[111,187]],
    [[232,33],[266,45],[298,35],[339,49],[376,30],[416,45]],
    [[266,88],[294,72],[320,84],[347,67],[377,78],[416,63]],
    [[264,163],[289,143],[323,155],[359,135],[394,149],[416,141]],
    [[257,208],[284,191],[317,205],[349,190],[382,203],[416,184]]]
PAPER='#fffdf7'; INK='#211e1a'
POSES=[]; TRACK=[]; META={}; TIMES=None; CROP=None

def pts(s): return ' '.join(f'{x:.3f},{y:.3f}' for x,y in s)
def line(s,width=1.35,color=INK):
    if np.max(np.ptp(np.asarray(s),axis=0))<.01:
        return f'<circle cx="{s[0][0]:.3f}" cy="{s[0][1]:.3f}" r="{width/2:.3f}" fill="{color}"/>'
    return f'<polyline points="{pts(s)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'

def init():
    global POSES,TRACK,META,TIMES,CROP
    META=json.loads((CACHE/'clip.json').read_text()); TRACK=json.loads((CACHE/'track.json').read_text())['frames']
    raw=[]; crops=[]
    for f in TRACK:
        m=np.repeat(np.arange(len(f['rle']))%2,f['rle']).reshape(f['H'],f['W']).astype(bool)
        ys,xs=np.where(m); assert len(xs)>100
        top=np.array([np.median(xs[ys<ys.min()+3]),ys.min()])*[416/f['W'],240/f['H']]
        cap=np.array([xs.max(),np.median(ys[xs>xs.max()-3])])*[416/f['W'],240/f['H']]
        raw.append(np.r_[top,cap]); crops.append(float(ys.max()>=f['H']-2))
    smoothed=savgol_filter(np.array(raw),5,2,axis=0)
    CROP=np.clip(savgol_filter(np.array(crops),5,2),0,1)
    TIMES=np.array([META['t0']+f['f']/META['fps'] for f in TRACK]); POSES=smoothed

def pose(t):
    a=np.array([np.interp(t,TIMES,POSES[:,i]) for i in range(4)])
    top,cap=a[:2],a[2:]; v=cap-top
    # Source-derived attitude from top and cap anchors. The lower contour is never
    # inferred from a cropped SAM bounding box, which would shrink the shell.
    native_vector=np.array([122*.73,64.7]); scale=np.linalg.norm(v)/np.linalg.norm(native_vector)
    theta=math.atan2(v[1],v[0])+math.atan2(native_vector[1],native_vector[0])
    axis=np.array([math.cos(theta),math.sin(theta)]); normal=np.array([axis[1],-axis[0]])
    center=top+scale*(128*.73*axis+2.1*normal)
    return top,cap,axis,normal,center,scale,theta

def geometry(t):
    top,cap,axis,normal,center,scale,theta=pose(t); mapped=[]
    for i,s in enumerate(ST):
        x,y=s[:,0],s[:,1]
        if i==1:
            # Retain the dome's native angular contour; a depth-dependent loft
            # moves its crown toward the observed cap without opening its base gap.
            loft=np.clip((53-y)/53,0,1)
            long=(x-128-20*loft)*.73; depth=35*.35+(53-y)*.95
        elif i>=2:
            long=(x-128)*.38-15; depth=37+(85-y)*.35
        else:
            long=(x-128)*.73; depth=(88-y)*.35
        mapped.append(center+scale*(long[:,None]*axis+depth[:,None]*normal))
    # Source masks hit the bottom viewport from mid-interval onward. Keep the
    # observed top/cap landmarks fixed, and extend only the lower native contour
    # to retain that observed crop; hidden continuation is explicitly unverified.
    crop_weight=float(np.interp(t,TIMES,CROP)); bottom=max(s[:,1].max() for s in mapped)
    stretch=max(1.,(248-cap[1])/max(1.,bottom-cap[1])); factor=1+crop_weight*(stretch-1)
    for s in mapped:
        lower=s[:,1]>cap[1];s[lower,1]=cap[1]+(s[lower,1]-cap[1])*factor
    return mapped,dict(top=top.tolist(),cap=cap.tolist(),center=center.tolist(),scale=scale,attitude_radians=theta,observed_crop_weight=crop_weight,lower_contour_extension_factor=factor)

def snapshot(t,character=False,mask=False):
    strokes,anchors=geometry(t)
    prefix=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 416 240">'
    if mask:
        glyph=''.join(f'<polygon points="{pts(strokes[i])}" fill="white"/>' for i in [0,1])
        return prefix+'<rect width="416" height="240" fill="black"/>'+glyph+'</svg>',anchors,strokes
    bg='' if character else ''.join(line(s,.7,'#a39b8d') for s in BG)
    # One object cel removes distant cloud lines from its interior. Native outline
    # and specks remain original strokes, not a traced photograph.
    cel=''.join(f'<polygon points="{pts(strokes[i])}" fill="{PAPER}"/>' for i in [0,1])
    glyph=''.join(line(s,1.45 if i<2 else 1.6) for i,s in enumerate(strokes))
    return prefix+f'<rect width="416" height="240" fill="{PAPER}"/>'+bg+cel+glyph+'</svg>',anchors,strokes

def render():
    OUT.mkdir(exist_ok=True); init(); source=json.loads((ROOT/'source.json').read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source['source_sha256']
    cap=cv2.VideoCapture(str(SOURCE)); cv2.setNumThreads(1); sfps=cap.get(cv2.CAP_PROP_FPS)
    assert (int(cap.get(3)),int(cap.get(4)))==(416,240)
    td=Path(tempfile.mkdtemp(prefix='secondhand-motion-saucer-')); frames=[]; fits=[]
    for f in range(N):
        t=START+f/FPS; idx=round(t*sfps); cap.set(cv2.CAP_PROP_POS_FRAMES,idx); ok,bgr=cap.read(); assert ok
        source_im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)).resize((W,H),Image.Resampling.LANCZOS)
        svg,anchors,strokes=snapshot(t); cartoon=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGB')
        cartoon.save(td/f'cartoon-{f:03d}.ppm'); source_im.save(td/f'source-{f:03d}.ppm')
        pair=Image.new('RGB',(2*W,H+24),'#f5f1e8');pair.paste(source_im,(0,24));pair.paste(cartoon,(W,24));pen=ImageDraw.Draw(pair)
        pen.text((10,6),f'NASA CGI ARCHIVE | {t:.3f} s',fill='#171512');pen.text((W+10,6),'ASSEMBLED DOODLE | source-derived attitude',fill='#171512');pair.save(td/f'pair-{f:03d}.ppm')
        q=TRACK[int(np.argmin(np.abs(TIMES-t)))];sam=np.repeat(np.arange(len(q['rle']))%2,q['rle']).reshape(q['H'],q['W']).astype(bool)
        msvg=snapshot(t,mask=True)[0];rig=np.asarray(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=msvg.encode()))).convert('L').resize((q['W'],q['H']),Image.Resampling.NEAREST))>127
        fits.append(float((sam&rig).sum()/max(1,(sam|rig).sum())))
        frames.append(dict(f=f,time=f/FPS,source_time=t,source_frame_index=idx,source_index_time=idx/sfps,anchors=anchors,sam_frame=q['f'],filled_rig_iou=fits[-1]))
        if f in KEYS:
            k=KEYS.index(f)+1;cartoon.save(OUT/f'key-{k:02d}.png');source_im.save(OUT/f'source-{k:02d}.jpg',quality=91);(OUT/f'key-{k:02d}.svg').write_text(svg)
            char=snapshot(t,character=True)[0];(OUT/f'character-key-{k:02d}.svg').write_text(char);cairosvg.svg2png(bytestring=char.encode(),write_to=str(OUT/f'character-key-{k:02d}.png'))
        if f==0:cartoon.save(OUT/'poster.png');pair.save(OUT/'comparison-poster.jpg',quality=91)
    cap.release(); validation={}
    for stem,name in [('cartoon','cartoon.mp4'),('source','source-excerpt.mp4'),('pair','comparison.mp4')]:
        temp=OUT/(name+'.tmp.mp4')
        subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(FPS),'-i',str(td/(stem+'-%03d.ppm')),'-an','-c:v','libx264','-threads','2','-preset','slow','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
        subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(temp),'-f','null','-'],check=True);temp.replace(OUT/name);validation[name]=dict(decoded_frames=N,fps=FPS,complete=True)
    shutil.copy(ROOT/'design.json',OUT/'design.json');shutil.copy(ROOT/'design.png',OUT/'design.png')
    shutil.copy(ROOT/'source-review/selected'/source['source_review'].split('/')[-1],OUT/'source-contact-sheet.jpg')
    (OUT/'background.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 416 240"><rect width="416" height="240" fill="{PAPER}"/>'+''.join(line(s,.7,'#a39b8d') for s in BG)+'</svg>')
    cache=OUT/'source-masks';cache.mkdir(exist_ok=True)
    for name in ['clip.json','track.json']:shutil.copy(CACHE/name,cache/name)
    provenance=dict(branch='wave2-track/flying-saucer',commit='4b1bb49126f9da6319349516b051a1da2e3b55b0',model='facebook/sam2.1-hiera-small',detector='IDEA-Research/grounding-dino-tiny',track_sha256=hashlib.sha256((cache/'track.json').read_bytes()).hexdigest(),predicted_iou_is_not_measured_fit=True,predicted_confidence=dict(field='SAM predicted IoU',minimum=min(f['iou'] for f in TRACK),maximum=max(f['iou'] for f in TRACK),mean=float(np.mean([f['iou'] for f in TRACK])),measured_against_ground_truth=False))
    (cache/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    fit=dict(method='union of filled projected original rim/dome native polygons vs nearest 12fps source SAM mask; original ink specks excluded from silhouette; not model confidence',mean=float(np.mean(fits)),minimum=float(np.min(fits)),bar_mean=.65,bar_minimum=.45,frames=N)
    fit['pass']=fit['mean']>=.65 and fit['minimum']>=.45
    shot=dict(title='A saucer borrows an entry attitude',category='flying saucer',source=source,design=D,revision='integrated-v2',status='assembled_candidate_review_pending',W=W,H=H,fps=FPS,frame_count=N,duration=N/FPS,keys=KEYS,frames=frames,
        xsheet=[dict(f=f,kind='K' if f in KEYS else 'B',note=('Steep entry attitude; preserve native lopsided rim.' if f==0 else 'Source-relative right/down drift.' if f<=20 else 'Lower rim exits the camera crop.' if f<=40 else 'Source-relative left/up return; retain lower crop.') if f in KEYS else '') for f in range(N)],
        source_registration=dict(method='SAM top/cap landmarks per CI frame, five-sample quadratic smoothing, interpolated to24fps; native projection source-derived, no authored spin',hidden_lower_contour='unverified: only the lower native contour extends beyond the viewport when source SAM masks show bottom cropping; top/cap anchors remain fixed',recorded_aspect=[416,240],output_aspect=[W,H]),
        planes=[dict(id='planet-clouds',source='drawn once by agent against NASA CGI source',strokes=BG),dict(id='rim',source_strokes=[0]),dict(id='dome',source_strokes=[1]),dict(id='specks',source_strokes=[2,3,4,5])],
        camera=dict(method='held abstract cloud plate; background motion not measured',parallax='not inferred'),mask_fit=fit,mask_provenance=provenance,
        assembly_summary='The original six-stroke saucer follows a NASA CGI aeroshell’s banked attitude, right/down drift, left/up return and lower-frame crop. No UFO footage or spinning flight is claimed.',review_status='fresh_review_pending',review_note='Lower-frame crop repaired against source masks; fresh source-pose review and normal-speed playback remain pending.',training_ran=False,motion_approved=False,train_eligible=False)
    (OUT/'shot.json').write_text(json.dumps(shot,indent=2)+'\n');(OUT/'mask-fit.json').write_text(json.dumps(fit,indent=2)+'\n')
    (OUT/'correspondence.json').write_text(json.dumps(dict(original_stroke_count=6,parts={'rim':[0],'dome':[1],'specks':[2,3,4,5]},topology='same original stroke point indices throughout',anchors=[dict(source_time=float(t),top=a[:2].tolist(),cap=a[2:].tolist()) for t,a in zip(TIMES,POSES)]),indent=2)+'\n')
    checks=dict(rendered_frames=N,fps=FPS,keys=len(KEYS),full_decode=True,source_sha256_verified=True,original_strokes=6,all_original_strokes_assigned=True,same_topology=True,held_background_geometry=True,source_kind='NASA CGI aeroshell animation; not physical UFO footage',SAM='upstream SAM2.1 snapshots used for observed top/cap landmarks',mask_fit=fit,recognition='not run',independent_playback='not run',planted_contacts_observed=0,foot_slide_gate='not passed; flying subject has no planted contacts',release_approved=False,training_ran=False)
    (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n');(OUT/'video-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('trace_keys',REPO/'tools/trace_keys.py');trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace);tr=[]
    for k in range(1,len(KEYS)+1):
        im=Image.open(OUT/f'character-key-{k:02d}.png');strokes,ink,hw=trace.trace(im);recall,precision,parts=trace.score(strokes,ink,W,H,hw);stats=dict(recall=recall,precision=precision,parts_kept=parts)
        tr.append(dict(key=k,strokes=strokes,**stats))
    (OUT/'traced.json').write_text(json.dumps({'flying-saucer':{'W':W,'H':H,'keys':tr}},indent=2)+'\n')
    checks['trace_fidelity']=dict(min_recall=min(x['recall'] for x in tr),min_parts_kept=min(x['parts_kept'] for x in tr),keys=len(tr));checks['trace_fidelity']['pass']=checks['trace_fidelity']['min_recall']>=.98 and checks['trace_fidelity']['min_parts_kept']==1
    (OUT/'assembly-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    shutil.rmtree(td)
    print(json.dumps(dict(frames=N,keys=len(KEYS),mask_mean=fit['mean'],mask_min=fit['minimum'],trace=checks['trace_fidelity'],output=str(OUT))))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,default=SOURCE);ap.add_argument('--mask-cache',type=Path,default=CACHE)
    args=ap.parse_args();SOURCE=args.source;CACHE=args.mask_cache;render()
