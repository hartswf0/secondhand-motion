# Two ants at the rock edge

The integrated review copy is [integrated/index.html](integrated/index.html). It offers the cartoon, matched source excerpt and side-by-side movie, with eight exact source/drawing key pairs. The two-second source interval is 0.200–2.200 clip-relative seconds. The 49-frame output is 480×360 at 24 fps.

Source inspection corrected the original plan: two ants are present throughout the retained event. The opening raw frame belongs to a different shot and is excluded. Both ants use the same complete Quick, Draw! ant key `5421013154136064`: eleven original strokes, three body sections, two antenna strokes and five leg strokes per instance. The left instance reflects the original facing; the right instance retains it. The native fifth-leg simplification is preserved without adding a sixth leg. Native stroke and point counts remain editable in `integrated/shot.json` and `correspondence.json`.

Body positions, antenna reach and unequal lower reaches are keyed from the source event. Interpolation is not a procedural gait. Endpoints are pose estimates; no material foot or antenna-contact identity has been verified. The rock plate is drawn once. Three stationary source-rock templates estimate the small camera drift separately from ant travel. A sparse optical-flow estimate produced a severe false pan and was rejected internally before blind review; its complete earlier media and state remain in `integrated/revisions/technical-camera-v0/`.

The SAM snapshot at commit `88e190d113066292caa735e5f0c86265deb89002` switches from one ant to a merged pair and back. It cannot establish whole-shot two-instance mask fit. Its last nominal sample is 2.0s; 44 of the 49 output timestamps are within its sample range (89.80%, below 95%). The remaining 0.2s is not scored using a reused final mask. No whole-shot IoU is reported. `integrated/sam-audit.jpg` and `sam/provenance.json` retain the limitation. Four independently observed planted intervals are required; zero are verified, so that gate fails. Classifier and actual normal-speed playback approval remain unrun. No training ran, and this is not an accepted training pair.

All separated character keys are traced with `tools/trace_keys.py`; minimum ink recall is 0.997333 and every ink component is retained. Technical integrity and saved-key/movie agreement do not establish artistic or motion approval. Independent raw critiques, their scope and remaining gaps are retained beside the assets and in the append-only `ledger.jsonl`.

Rebuild with local source and cache paths:

```sh
python shots/ant/build_integrated.py --source /path/to/17c403a7-1f5c-5a7d-9bc5-aa1bac026b73.mp4 --mask-cache /path/to/ant-cache
python shots/ant/record_integrated.py
python shots/ant/build_integrated_page.py
python tools/verify_integrated.py ant
```

The third candidate additionally reflects the left instance's original small appendage bends consistently with its reflected body, without changing observed endpoints. Earlier complete v1/v2 assets and raw independent reviews remain in `integrated/revisions/`; the v2 ledger entry was recorded before its snapshot was copied there. The final review is the third and last blind round.

The renderer verifies the pinned raw SHA-256, uses a unique temporary directory, fully decodes all three movies, checks frame counts, and atomically installs completed movies. Reference boards are built after all key writers and tracing finish. The offline phone-layout page uses native video controls; static links and inline script syntax are checked, but actual 390px browser layout inspection is unavailable.

Archive: *Ant City* (1949), Moving Image Archive clip `17c403a7-1f5c-5a7d-9bc5-aa1bac026b73`, source `20af9071-f8f0-545f-83a9-1e3e5e583f3e`. The archive reports `public_domain`; independent rights verification has not run. Source URLs, raw SHA-256 and the corrected/rejected original plan are retained in `integrated/source.json`. Quick, Draw! contributors / Google Creative Lab, CC BY 4.0.
