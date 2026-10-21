# Drawn keys: the studio brief for every shot

This brief adapts SCION · refined (the studio prompt in the CRASH LAB docs, `bolas/docs/prompts/11-scion-refined.txt`)
and the handmade-film method (key poses by hand, figures over unaltered archive plates, fresh blind critics) to
Secondhand Motion. It replaces "more critic rounds on the rig" with drawing.

## Thesis

A Quick, Draw! doodle performs the archive film's own event: the same action, at the same moments, in the same
place in the frame, drawn by the same anonymous hand in every frame. The viewer should recognise the film's event
first and the doodle second, and never see the drawing jump, double or slide where the film does not.

The competent-but-forgettable version, which the rig pass mostly produced: the doodle placed over the subject and
carried along, keyed every few frames at even spacing, bending at a few joints, with the film's main event (a turn,
a chew, a bow stroke) missing because the rig has no way to draw it.

## The line

Each shot has one beat it exists to deliver (after "I need the line", `08-the-line.txt`): the pig turning to face us,
the swan's neck coming up, the speedboat hitting the water. It is planned first, keyed first, given an anticipation
before and a hold or settle after. Everything else in the shot is plainer.

## Keys that matter

- Chosen from every frame of the clip (`tools/draw_key.py frames`): extremes, contacts, turns, the line.
- Drawn over the frame (`tools/draw_key.py key` / `check`): the doodle's own strokes moved into the new pose or the
  new view; a turn is redrawn for the new angle, not squeezed. Extra strokes only for a part the doodle never drew
  and the event needs, in the doodle's hand.
- In-betweened by `tools/drawn.py`: the rig carries the motion, the drawn changes are eased from key to key; holds
  keep a drawing while the rig moves it.

## Reference and bar

The reference for every shot is its own footage at the same frames. The critic (fresh, blind, still frames only,
and it says so) first describes what the animation shows, then what the film shows, then returns:

    VERDICT ...... bar met | reference stronger | inconclusive
    EVIDENCE ..... frame numbers and what is in them
    PRIMARY GAP .. the single most consequential weakness
    CLOSES WHEN .. the observable change that would close it
    PROTECT ...... what a repair must keep

plus the earlier fields (motion score, identity verdict, broken frames) so results compare with earlier rounds.
The bar does not move. The builder never awards the pass.

## Proof passage first

The method is proved on the hardest shot before it is run on all 53: the pig, which the rig could never turn to
face the camera (score 2 in four rounds).

## Repair and inquiry

A repair fixes the cause, not the critic's literal suggestion. When two repairs fail the same way (as the broom's
did), the next step is an inquiry, written in five lines (observed; current explanation; the assumption it rests
on; an alternative that would imply a different repair; a test that tells them apart), and the test is built and
looked at before any further repair.
