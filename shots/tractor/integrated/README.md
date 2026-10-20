# Tractor assembled review copy

The 47-frame, 24 fps render covers clip-relative 0.5–2.45 seconds from *Farmer Miller Goes Into High Gear (Part I)*. Its six keys and comparison movie use the same decoded source indices. The original Quick, Draw! tractor is key `4702418350637056`, credited to Quick, Draw! contributors / Google Creative Lab, CC BY 4.0.

Source download URL and SHA-256 are recorded in [`../source.json`](../source.json), in `video_url` and `source_sha256`. Download the clip from that URL to a local path before rebuilding. The builder verifies its bytes against that recorded SHA-256 and refuses a mismatch.

From the repository root, with Python 3, FFmpeg, NumPy, SciPy, Pillow, OpenCV and CairoSVG installed:

```sh
python shots/tractor/build_integrated.py --source /absolute/path/to/tractor.mp4
python shots/tractor/build_integrated_page.py
```

Alternatively, set `SECONDHAND_MOTION_SOURCE` to the clip path and run the first command without `--source`. The fallback is a sibling `wave2-logs/tractor.mp4` directory beside the repository. Intermediate render frames use a unique operating-system temporary directory. The final assets are written beside this README.

The builder draws one field plate and animates the original five doodle strokes using source-observed part anchors. Driver, trailer, depth-side wheel copies and hub/spoke marks are agent-authored context. Spoke phase is authored, not a measured source RPM.

The independent still review accepts composition, pose and doodle identity. Normal-speed playback approval, SAM, recognition and numeric mask fit remain unrun. No training ran. This is a review copy, not a final-approved release.
