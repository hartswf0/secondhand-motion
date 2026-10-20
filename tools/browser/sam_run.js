// Stage 1 in the browser, as Giraffe Walks Past did it: Grounding DINO finds the subject, SAM 2.1 masks it,
// on every frame. Run in a browser tab opened on the published site (same origin as the frames), e.g.
// https://hartswf0.github.io/secondhand-motion/pages/pipeline.html, by pasting this into the console
// (or a tool that executes page JavaScript). WebGPU is used when present: about 1.3 s a frame; wasm is ~10 s.
//
//   await SM.load();                       // models: grounding-dino-tiny, sam2.1-hiera-small (transformers.js 4.3.1)
//   await SM.run('dog', 50, fallbackBoxes) // frames ../shots/dog-redraw/frames/f000.jpg ... f049.jpg
//   copy(await SM.pack('dog'))             // gzip + base64 of {frames:[{f, box, from, iou, area, W, H, rle}]}
//
// Then: python3 tools/sam_import.py dog <file with the base64 text>
// The box for each frame is Grounding DINO's best box for "a <category>." (threshold 0.2); when it finds
// nothing, the previous frame's box is reused; before any detection, the agent's fallback box for the
// nearest key. SAM returns three masks; the one with the highest predicted IoU is kept. rle is row-major
// run lengths starting with background.
window.SM = {
  async load() {
    const T = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.1'); this.T = T;
    const dev = (navigator.gpu && await navigator.gpu.requestAdapter()) ? 'webgpu' : 'wasm';
    this.det = await T.pipeline('zero-shot-object-detection', 'onnx-community/grounding-dino-tiny-ONNX', { dtype: 'fp32', device: dev });
    this.sam = await T.Sam2Model.from_pretrained('onnx-community/sam2.1-hiera-small-ONNX', { dtype: 'fp32', device: dev });
    this.proc = await T.AutoProcessor.from_pretrained('onnx-community/sam2.1-hiera-small-ONNX');
    this.out = {}; return dev;
  },
  async run(cat, n, fallback = { keys: [0], boxes: [null] }, label = cat) {
    const res = []; let prev = null; this.out[cat] = { frames: res };
    for (let f = 0; f < n; f++) {
      const img = await this.T.RawImage.fromURL(`../shots/${cat}-redraw/frames/f${String(f).padStart(3, '0')}.jpg`);
      const W = img.width, H = img.height; let box = null, from = '';
      const d = await this.det(img, [`a ${label}.`], { threshold: 0.2 });
      if (d.length) { d.sort((a, b) => b.score - a.score); const b = d[0].box; box = [b.xmin, b.ymin, b.xmax, b.ymax]; from = 'dino ' + d[0].score.toFixed(2); prev = box; }
      else if (prev) { box = prev; from = 'previous box'; }
      else { const k = fallback.keys.reduce((a, kk, i) => Math.abs(kk - f) < Math.abs(fallback.keys[a] - f) ? i : a, 0); box = fallback.boxes[k] || [0, 0, W - 1, H - 1]; from = 'agent box'; }
      const inp = await this.proc(img, { input_boxes: [[box]] }); const o = await this.sam(inp);
      const ms = await this.proc.post_process_masks(o.pred_masks, inp.original_sizes, inp.reshaped_input_sizes);
      const sc = o.iou_scores.data; let bi = 0; for (let i = 1; i < sc.length; i++) if (sc[i] > sc[bi]) bi = i;
      const data = ms[0].data, HW = W * H; const rle = []; let cur = 0, run = 0, area = 0;
      for (let p = 0; p < HW; p++) { const v = data[bi * HW + p] ? 1 : 0; area += v; if (v === cur) run++; else { rle.push(run); run = 1; cur = v; } }
      rle.push(run); res.push({ f, box: box.map(Math.round), from, iou: +sc[bi].toFixed(3), area, W, H, rle });
    }
    return res.length;
  },
  async pack(cat) {
    const cs = new CompressionStream('gzip'); const w = cs.writable.getWriter(); w.write(new TextEncoder().encode(JSON.stringify(this.out[cat]))); w.close();
    const buf = new Uint8Array(await new Response(cs.readable).arrayBuffer()); let b = '';
    for (let i = 0; i < buf.length; i += 8192) b += String.fromCharCode.apply(null, buf.subarray(i, i + 8192)); return btoa(b);
  },
};
