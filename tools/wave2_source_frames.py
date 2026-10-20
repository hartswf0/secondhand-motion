"""Bounded source-frame extraction. Produces reference photos, never artwork or approvals.
Run per subject with an immutable repository ref. Public assets only, no credentials.
"""
import argparse, base64, hashlib, io, json, math, re, tempfile, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse, quote
import cv2
from PIL import Image, ImageDraw, ImageOps

MEDIA_HOST = 'pub-075ff01374c04555b51c9bc50f258b42.r2.dev'
MAX_BYTES = 80 * 1024 * 1024
def fetch(url, limit=MAX_BYTES):
    req = Request(url, headers={'User-Agent':'Mozilla/5.0 SecondhandMotion/1.0',
                                'Referer':'https://www.movingimagearchive.com/'})
    started=time.monotonic()
    with urlopen(req, timeout=30) as response:
        parts=[]; total=0
        while True:
            b=response.read(512*1024)
            if not b: break
            total+=len(b)
            if total>limit or time.monotonic()-started>150: raise ValueError('download bound exceeded')
            parts.append(b)
        return b''.join(parts)
def emit_asset(asset_id, content, mime):
    encoded=base64.b64encode(content).decode()
    n=math.ceil(len(encoded)/12000)
    print('WAVE2_ASSET '+json.dumps({'asset_id':asset_id,'mime':mime,'bytes':len(content),
          'sha256':hashlib.sha256(content).hexdigest(),'chunks':n}), flush=True)
    for i in range(n):
        print('WAVE2_CHUNK '+json.dumps({'asset_id':asset_id,'i':i,'data':encoded[i*12000:(i+1)*12000]}),flush=True)

def emit_design_bank(category, slug, request):
    url='https://storage.googleapis.com/quickdraw_dataset/full/simplified/'+quote(category)+'.ndjson'
    req=Request(url,headers={'Range':'bytes=0-499999','User-Agent':'SecondhandMotion/1.0'})
    with urlopen(req,timeout=30) as response: prefix=response.read(500000)
    selected=[]; chosen=None
    for line in prefix.splitlines()[:-1]:
        try: row=json.loads(line)
        except Exception: continue
        if str(row.get('key_id'))==str(request.get('design_key_id')): chosen=row
        if row.get('recognized') and 4<=len(row['drawing'])<=16 and len(selected)<12:
            selected.append({'key_id':str(row['key_id']),'word':row['word'],'recognized':True,'drawing':row['drawing']})
    if not selected: raise ValueError('no bounded doodle bank')
    sheet=Image.new('RGB',(1024,3*270),'white'); draw=ImageDraw.Draw(sheet)
    for i,row in enumerate(selected):
        x=(i%4)*256;y=(i//4)*270
        draw.text((x+5,y+4),str(i+1)+' | '+row['key_id'],fill='black')
        for stroke in row['drawing']:
            pts=[(x+18+float(a)*.83,y+30+float(b)*.83) for a,b in zip(stroke[0],stroke[1])]
            if len(pts)>1: draw.line(pts,fill='black',width=3,joint='curve')
        draw.text((x+5,y+250),'REAL QUICKDRAW | CC BY 4.0',fill='black')
    data=io.BytesIO();sheet.save(data,format='JPEG',quality=86,optimize=True)
    emit_asset(slug+'/design-bank.jpg',data.getvalue(),'image/jpeg')
    emit_asset(slug+'/design-bank.json',json.dumps({'category':category,'source_url':url,
               'credit':'Quick, Draw! contributors / Google Creative Lab; CC BY 4.0',
               'recognized_is_not_classifier_confidence':True,'drawings':selected}).encode(),'application/json')

    if request.get('design_key_id'):
        if chosen is None: raise ValueError('chosen key_id not in bounded original data')
        im=Image.new('RGB',(512,512),'white'); pen=ImageDraw.Draw(im)
        mirrored=request.get('design_transform')=='mirror_x'
        for stroke in chosen['drawing']:
            pts=[(28+(255-float(x) if mirrored else float(x))*1.78,28+float(y)*1.78) for x,y in zip(stroke[0],stroke[1])]
            if len(pts)>1: pen.line(pts,fill='black',width=4,joint='curve')
        b=io.BytesIO(); im.save(b,format='PNG')
        emit_asset(slug+'/selected-design.png',b.getvalue(),'image/png')
        emit_asset(slug+'/selected-design.json',json.dumps({'key_id':str(chosen['key_id']),'word':chosen['word'],
            'drawing':chosen['drawing'],'recognized':chosen['recognized'],'transform':request.get('design_transform','none'),
            'source_url':url,'credit':'Quick, Draw! contributors / Google Creative Lab; CC BY 4.0',
            'recognized_is_not_classifier_confidence':True}).encode(),'application/json')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--slug',required=True)
    ap.add_argument('--ref',required=True)
    a=ap.parse_args()
    if not re.fullmatch(r'[a-z-]+',a.slug) or not re.fullmatch(r'[0-9a-f]{40}',a.ref):
        raise ValueError('invalid slug/ref')
    root='https://raw.githubusercontent.com/hartswf0/secondhand-motion/'+a.ref+'/'
    folder='shots/'+a.slug+'/'
    manifest=json.loads(fetch(root+folder+'candidates.json',2*1024*1024))
    request=json.loads(fetch(root+folder+'source-review-request.json',100000))
    ids=request['clip_ids']
    if not 1<=len(ids)<=4 or len(ids)!=len(set(ids)): raise ValueError('one to four unique candidates required')
    candidates={c['clip_id']:c for c in manifest['clips']}
    if any(cid not in candidates for cid in ids): raise ValueError('candidate not in subject manifest')
    try:
        emit_design_bank(manifest['category'],a.slug,request)
    except Exception as exc:
        print('WAVE2_BANK_ERROR '+json.dumps({'slug':a.slug,'error':str(exc)}),flush=True)
    try:
        import cairosvg
        svg=fetch(root+folder+'doodle.svg',500000)
        png=cairosvg.svg2png(bytestring=svg,output_width=512,output_height=512,background_color='white')
        item=json.loads(fetch(root+folder+'item.json',100000))
        emit_asset(a.slug+'/design-reference.png',png,'image/png')
        print('WAVE2_DESIGN '+json.dumps({'slug':a.slug,'svg_ref':root+folder+'doodle.svg',
              'credit':item.get('cover_credit'),'kind':'existing_quickdraw_reference_not_new_art'}),flush=True)
    except Exception as exc:
        print('WAVE2_DESIGN_ERROR '+json.dumps({'slug':a.slug,'error':str(exc)}),flush=True)
    successes=0
    for cid in ids:
        c=candidates[cid]
        try:
            u=urlparse(c['video_url'])
            if u.scheme!='https' or u.netloc!=MEDIA_HOST or not u.path.endswith('.mp4'):
                raise ValueError('unapproved media origin')
            video=fetch(c['video_url'])
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'source.mp4';path.write_bytes(video)
                cap=cv2.VideoCapture(str(path))
                fps=cap.get(cv2.CAP_PROP_FPS); count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if not cap.isOpened() or not fps>0 or count<16: raise ValueError('insufficient decodable frames')
                duration=count/fps
                start=float(request.get('intervals',{}).get(cid,[0,duration])[0])
                end=float(request.get('intervals',{}).get(cid,[0,duration])[1])
                if not 0<=start<end<=duration+.05: raise ValueError('invalid requested interval')
                sheet=Image.new('RGB',(1024,4*218+48),'white');draw=ImageDraw.Draw(sheet)
                draw.text((8,6),a.slug+' | '+cid,fill='black')
                draw.text((8,24),'SOURCE PHOTOS ONLY | '+c['source_title'][:105],fill='black')
                frames=[]
                for i in range(16):
                    target=start+(end-start)*(.015+.97*i/15)
                    index=min(count-1,max(0,round(target*fps)))
                    cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,frame=cap.read()
                    if not ok: raise ValueError('decode failed at '+str(index))
                    reported=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
                    im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                    im=ImageOps.pad(im,(256,192),color='black')
                    x=(i%4)*256;y=48+(i//4)*218
                    sheet.paste(im,(x,y));draw.text((x+4,y+195),str(i+1)+' | '+format(index/fps,'.3f')+'s',fill='black')
                    frames.append({'target_time':target,'frame_index':index,'index_time':index/fps,
                                   'decoder_reported_time':reported})

                key_frames=[]
                times=request.get('key_times',{}).get(cid,[])
                if times:
                    if len(times)!=6 or any(not start-.05<=t<=end+.05 for t in times): raise ValueError('invalid six key times')
                    six=Image.new('RGB',(768,3*314),'white'); lab=ImageDraw.Draw(six)
                    for k,target in enumerate(times):
                        idx=min(count-1,max(0,round(target*fps)))
                        cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,frame=cap.read()
                        if not ok: raise ValueError('six-key reference decode failed')
                        photo=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                        photo=ImageOps.pad(photo,(384,288),color='black')
                        x=(k%2)*384;y=(k//2)*314;six.paste(photo,(x,y))
                        lab.text((x+5,y+291),'K'+str(k+1)+' | '+format(idx/fps,'.6f')+'s',fill='black')
                        key_frames.append({'key':k+1,'frame_index':idx,'index_time':idx/fps})
                    b=io.BytesIO();six.save(b,format='JPEG',quality=88,optimize=True)
                    emit_asset(a.slug+'/'+cid+'-sixkeys.jpg',b.getvalue(),'image/jpeg')

                cap.release()
                if len({f['frame_index'] for f in frames})<12: raise ValueError('fewer than 12 distinct sampled frames')
            asset=a.slug+'/'+cid+'-16frames.jpg'
            data=io.BytesIO();sheet.save(data,format='JPEG',quality=82,optimize=True)
            emit_asset(asset,data.getvalue(),'image/jpeg')
            print('WAVE2_RECORD '+json.dumps({'slug':a.slug,'clip_id':cid,'source':c,
                  'source_sha256':hashlib.sha256(video).hexdigest(),'downloaded_bytes':len(video),
                  'fps':fps,'frame_count':count,'duration_seconds':duration,
                  'sampled_interval':[start,end],'frames':frames,'key_reference_frames':key_frames,'contact_sheet_asset':asset,
                  'inspected':False,'source_approved':False,'motion_approved':False,
                  'train_eligible':False,'status':'reference_extraction_only'}),flush=True)
            successes+=1
        except Exception as exc:
            print('WAVE2_ERROR '+json.dumps({'slug':a.slug,'clip_id':cid,'error':str(exc)}),flush=True)
    if not successes: raise SystemExit('No source photos could be extracted')
if __name__=='__main__':main()
