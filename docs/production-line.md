# Production line

Every subject goes through the same eight steps, one subject at a time. CI does the survey and the tracking for a whole wave in one push; the plan, rig, keys and scene are hand work per subject; the critic is a fresh blind agent per subject. Written by `tools/subject.py status`.

| Subject | survey | plan | track | rig | keys | scene | build | critic | Next | Critic: identity, motion, follows film |
|---|---|---|---|---|---|---|---|---|---|---|
| [bicycle](../pages/bicycle-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [butterfly](../pages/butterfly-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [cat](../pages/cat-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [cow](../pages/cow-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [dog](../pages/dog-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [duck](../pages/duck-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, partly |
| [fan](../pages/fan-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, yes |
| [flying-saucer](../pages/flying-saucer-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, yes |
| [giraffe](../pages/giraffe-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [helicopter](../pages/helicopter-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, yes |
| [horse](../pages/horse-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [hurricane](../pages/hurricane-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [monkey](../pages/monkey-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [mosquito](../pages/mosquito-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, partly |
| [pig](../pages/pig-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [rabbit](../pages/rabbit-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, yes |
| [raccoon](../pages/raccoon-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [rain](../pages/rain-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, jumbled, yes |
| [roller-coaster](../pages/roller-coaster-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, yes |
| [sailboat](../pages/sailboat-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [see-saw](../pages/see-saw-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [sheep](../pages/sheep-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [skateboard](../pages/skateboard-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [spider](../pages/spider-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [tiger](../pages/tiger-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, broken, partly |
| [tornado](../pages/tornado-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, partly |
| [tractor](../pages/tractor-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, yes |
| [windmill](../pages/windmill-gwp.html) | done | done | done | done | done | done | done | done | done | bar_met, smooth, partly |

## The steps

```
1 survey   CI      contact sheet of the whole clip, cut spikes, a bank of 40 real doodles (survey.yml)
  2 plan     agent   choose the continuous interval and one doodle; write shots/<slug>/plan.json
  3 track    CI      frames, SAM 2.1 masks, Depth Anything depth (add the slug to data/track-now.json)
  4 rig      agent   rigs/<slug>_spec.json from the numbered doodle sheet: root, joints, regions, spins
  5 keys     agent   first pass from the silhouettes, then corrected by eye on the grids
  6 scene    agent   rigs/<slug>_scene.json: Quick, Draw! scenery in boxes, planes with z from depth
  7 build    auto    shot.json, tests, critic packet, page
  8 critic   agent   a fresh blind critic per subject; repair the one gap named; repeat at most three times
```
