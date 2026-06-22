---
name: remove-background
description: Remove the background from ANY image (photo, illustration, render, icon, product, person, animal, object), leaving it transparent in an RGBA PNG while working on the ORIGINAL pixels — without generating, recreating, or redrawing the image. Use when the user asks to "remove the background," "remove the bg," "cut out," "make transparent," or "isolate the object" in an image. Independently chooses between edge-based flood fill (uniform background/solid color/flattened checkerboard), AI segmentation (natural photo with a complex background), and a luma-based scene cut for back-lit landscapes/silhouettes against a bright sky where segmentation finds no salient subject.
allowed-tools: Bash(python3 *), Read
---

# Remove an image background

You are the vision half of this tool. Each cutout is a short loop: you read the
scene, measure the pixels, reconcile the two, calibrate the scripts, and review
the result. The scripts cut and measure — **you decide**. Don't hand the decision
to a one-shot command.

## Communication (IMPORTANT — read before acting)
Be DISCREET in the **user-facing answer**. The loop below is your internal process
(tool calls), not something to narrate:
- DO NOT say which script, model, method, or technique you are using (nothing like
  "I'll use AI segmentation," "birefnet," "flood fill," "analyze.py").
- DO NOT write "Step 1 / Step 2 / Step 3" or describe the pipeline.
- No decorative emojis or long process explanations.
- At most one short sentence before acting (e.g., "Removing the background...").
- Final response = brief: the path to the finished PNG + one confirmation line.
  Only give technical details (method/model/parameters) if the user asks.

## The loop (default path)
Prefix every script with `python3 ${CLAUDE_SKILL_DIR}/scripts/`. `${CLAUDE_SKILL_DIR}`
is provided by Claude Code and resolves to this skill's directory on any machine.

1. **Look.** Open the image with Read. Name the subject, the background, the light
   source, and roughly where the horizon/edges sit — the context only a viewer has.
2. **Probe.** `analyze.py INPUT` prints the pixel half: size/alpha, edge background
   color, region color samples, brightest point, the vertical luminance profile,
   and a recommended method.
3. **Reconcile.** Cross-check your visual read against the numbers and resolve any
   gap. (A blind threshold can't tell a tall tree from the ground; you can — so a
   dark band high in the profile is the subject, not the horizon.)
4. **Cut & calibrate.** Pick the method and run it with parameters set from steps
   1–3 (see "Methods & knobs"). Output defaults to `<input>-sem-fundo.png`.
5. **Review.** Open the printed `PREVIEW` with Read: complete subject, no
   halo/residue, transparent corners. Read the `STATUS` line too.
6. **Iterate.** If the preview or a flag shows a problem, adjust the parameters (or
   switch method) and re-run. Repeat until it's right.

An easy image converges on the first pass. `run.py INPUT [OUTPUT]` is a shortcut
that auto-picks solid/photo and runs steps 4–5 in one go — fine for obvious cases,
but it does **not** calibrate, so drop back into the loop whenever a flag fires or
the preview looks off.

`STATUS` is `OK` or one or more flags:
- `CHECAR_CANTOS` — some background remains touching the edges.
- `CHECAR_RESIDUO` — a second large detached region (likely residue/distractor).
- `OBJETO_QUASE_VAZIO` — the mask is nearly empty (no salient subject; consider `scene`).
- `FUNDO_NAO_REMOVIDO` — almost everything stayed opaque (background not removed).

`OK` only means the automated checks passed — **it is not a guarantee**. A distractor
**attached** to the subject (a figure printed on a panel behind it, another person
touching it, a reflection) becomes one piece and trips no flag: only the preview
(step 5) catches it.

## Methods & knobs
All three preserve the original pixels (no generation/inpainting) and print metrics
you calibrate against the preview.

- **`remove_bg_solid.py INPUT [OUTPUT]`** — uniform/solid-color background, by edge
  flood fill. Knobs: `--hi`/`--lo` (color-distance thresholds; override the Otsu
  split when it clips the object or leaves background), `--bg-color R,G,B` (key a
  specific color).
- **`remove_bg_photo.py INPUT [OUTPUT] [MODEL]`** — natural photo with a salient
  subject, by segmentation. Models: `birefnet-general-lite` (default), `isnet-general-use`
  (fast; sometimes captures *less* background, useful against distractors),
  `u2net_human_seg` (people only). The full `birefnet-general` gives slightly cleaner
  edges but is heavy on RAM. Knobs: `--fg-threshold`/`--bg-threshold`/`--erode`
  (matting), `--keep-largest` (keep only the biggest component — discards detached
  distractors).
- **`remove_bg_scene.py INPUT [OUTPUT]`** — back-lit landscape/silhouette against a
  bright sky, where segmentation returns `OBJETO_QUASE_VAZIO`. Keeps the dark
  foreground, erases the bright sky. **You supply the geometry** you read off the
  picture — there is no auto-detection: `--horizon Y` (ground line; below it stays
  solid, keeping the road and stopping a flare from punching through), `--sun X,Y`
  (light source whose glow to preserve). Split knobs: `--sky-lo`/`--sky-hi` (luma)
  and `--bluish`. Place `--horizon` using the luminance profile from `analyze.py`
  (the row where the band mean collapses, not the first dark band). Assumes bright
  sky over a darker foreground — not for night scenes.

## Rules
- Work on the original pixels. RGBA PNG, real alpha. Preserve resolution, texture,
  colors, internal shadows, and fine detail.
- A **watermark baked into the pixels** (e.g. Vecteezy) is NOT removed by a cutout —
  say so briefly (removing it needs inpainting, which is out of scope).

## Harder cases
- **DETACHED distractor/residue** (separate from the subject): `--keep-largest`.
  (Small islands are already dropped automatically.)
- **ATTACHED distractor** (printed on a panel behind it, someone touching it, a
  reflection): no model separates it. Then:
  - **Focus/sharpness**: the real subject is usually sharp, the background blurred.
    Use a smoothed `|Laplacian|` (`scipy.ndimage`) as a sharpness map and keep the
    sharp region. ⚠️ Smooth interiors (a shirt, a flat wall) read as "less sharp" too
    — combine with `binary_opening`/largest component and dilate back to avoid holes.
  - **Geometric cut**: when the boundary is clear, cut a polygon (`PIL.ImageDraw`)
    along the edge and zero the alpha outside it. Iterate on the preview.
  - **GrabCut (`cv2`) rarely helps**: if the distractor shares the subject's color
    (e.g. skin tone), the color model brings it back.

`validate.py OUTPUT.png` re-runs the checkerboard preview + metrics on any cutout.
Recheck the `PREVIEW` after every attempt — and even while iterating, keep the
user-facing answer discreet.
