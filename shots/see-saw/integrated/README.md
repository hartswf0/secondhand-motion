# See-saw assembly review

160 rendered frames at 24 fps, nine integrated keys and a synchronized source comparison. The source interval is refined to 9.45–16.1 seconds, excluding an opening exposure fade in the earlier draft selection.

The original Quick, Draw! see-saw `4512834501214208` supplies four strokes. The board is one rigid 3D construction, hinged at a fixed fulcrum and projected from hand-observed source angles. Riders, parallel equipment and the wooded setting are agent drawn source context. Foreground occlusion is explicit.

The available SAM2.1 masks select multiple parallel boards. The snapshot is retained in `sam/` with a visual audit and provenance hashes; it is unsuitable as a single-instance mask-fit target. No numeric source-fit or recognition gate is claimed. No training ran. Playback approval remains pending.

To rebuild, download the video URL in `source.json`, then run from the repository root:

```sh
python shots/see-saw/build_integrated.py --source /path/to/see-saw.mp4
python shots/see-saw/build_integrated_page.py
```

Requires Python with OpenCV, NumPy, SciPy, Pillow, CairoSVG and ffmpeg with libx264. The source SHA-256 is verified. The included SAM snapshot is the default; `--sam-cache` can select another snapshot. Render intermediates use a unique temporary folder; videos are validated before atomic installation.

Three blind reviews were retained. The current v3 meets sampled composition, original doodle identity and hinge-action bars, but the high rider pose still reads as standing; a clearer seated hip and bent knees are the remaining bounded repair. The production loop stopped after three rounds. Normal-speed motion approval remains withheld.
