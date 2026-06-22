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
   which channel-difference (G-B, B-R, …) most cleanly splits a top band (for a
   color key), and a recommended method.
3. **Reconcile.** Cross-check your visual read against the numbers and resolve any
   gap. (A blind threshold can't tell a tall tree from the ground; you can — so a
   dark band high in the profile is the subject, not the horizon.)
4. **Cut & calibrate.** Pick the method and run it with parameters set from steps
   1–3 (see "Methods & knobs"). Output defaults to `<input>-sem-fundo.png`.
5. **Review.** Open the printed `PREVIEW` with Read: complete subject, no
   halo/residue, transparent corners. Read the `STATUS` line too. A light/white
   halo can hide on the gray checker — `validate.py` also writes a BLACK preview;
   open it and check `%partial whitish` whenever the edge meets a bright background.
6. **Iterate.** If the preview or a flag shows a problem, adjust the parameters (or
   switch method) and re-run. Repeat until it's right.

An easy image converges on the first pass. `run.py INPUT [OUTPUT]` is a shortcut
that auto-picks solid/photo and runs steps 4–5 in one go — fine for obvious cases,
but it does **not** calibrate, so drop back into the loop whenever a flag fires or
the preview looks off.

`STATUS` is `OK` or one or more flags:
- `CHECAR_CANTOS` — some background remains touching the edges. (Expected when you
  intentionally keep the ground to the bottom edge — silence it with
  `validate.py --keep-ground`, which still checks the top corners.)
- `CHECAR_RESIDUO` — a second large detached region (likely residue/distractor).
- `OBJETO_QUASE_VAZIO` — the mask is nearly empty (no salient subject; consider `scene`).
- `FUNDO_NAO_REMOVIDO` — almost everything stayed opaque (background not removed).
- `CHECAR_HALO` — the partial-alpha edge is bright/low-saturation: a leftover
  background-color halo. Decontaminate the fringe against the color you SEE bleeding
  in (on a blue-sky-plus-white-cloud background that's the CLOUD color, not the
  channel you keyed), then confirm on the BLACK preview.

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
- **`remove_bg_chroma.py INPUT [OUTPUT] --channel G-B`** — PARTIAL background: a
  colored background (blue sky, green screen) must go while a subject AND a co-equal
  region (the ground it stands on) STAY. Keys on a channel DIFFERENCE you pick from
  `analyze.py`'s split table — e.g. `G-B` puts blue sky negative and green vegetation
  positive, which no distance-from-one-color can separate when white clouds sit
  between them. Knobs: `--lo`/`--hi` (soft ramp on the channel), `--invert`,
  `--keep-below` (an agent-drawn ground line — flat `Y` or `x0:y0,x1:y1,...` control
  points — below which all stays solid), `--decontam local` (un-mix the LOCAL
  background out of the fringe; kills a white-cloud/blue-sky halo), `--gate` /
  `--gate-reach` (drop partial fragments not connected to the opaque core; raise the
  reach if it thins a narrow bridge like a trunk).

## Rules
- Work on the original pixels. RGBA PNG, real alpha. Preserve resolution, texture,
  colors, internal shadows, and fine detail.
- A **watermark baked into the pixels** (e.g. Vecteezy) is NOT removed by a cutout —
  say so briefly (removing it needs inpainting, which is out of scope).

## Harder cases
- **PARTIAL background — keep the ground (sky over a scene).** First the semantic
  question only a viewer can answer: is a visible region (the sky, a backdrop) the
  ONLY background, while another large region (the ground, a surface the product
  sits on) is foreground? If so, do NOT segment — `remove_bg_photo` scores for one
  cohesive blob and will keep the subject but drop the ground. Then, in order:
  1. **Find a color key, not a single color.** A single `--bg-color` fails when a
     barrier color sits between background and foreground (white clouds are far from
     both blue sky and green foliage; raising `--hi` to reach the clouds also starts
     eating the foliage). Read `analyze.py`'s channel-split table and key the
     lowest-OVERLAP difference with `remove_bg_chroma.py --channel`. Trap: a wide gap
     with high overlap (e.g. `2G-R-B` when clouds cross positive) is noisier than a
     cleaner `G-B` — and a tall subject inside the top band skews the table, so
     reconcile it against the region samples.
  2. **Keep the continuous region structurally, not by color.** The ground is
     reliable as a shape: pass `--keep-below` a line you draw (curve the control
     points to a hill) below which everything stays solid, so shadows and grass
     variation don't punch holes.
  3. **Kill the halo with LOCAL decontamination.** A soft edge keeps the color of
     whatever was behind it; on a two-color background the halo is the CLOUD color,
     not the key. `--decontam local` un-mixes the nearest background per pixel; then
     `--gate` away detached fragments (raise `--gate-reach` if it thins a trunk).
  4. **Review on BLACK** (`validate.py` writes it) and watch `%partial whitish`;
     filled bottom corners are expected (`--keep-ground`).

  The lesson generalizes: identify which image properties are actually reliable
  (ground continuity, a smooth horizon you can draw, a clean channel split) and
  choose the algorithm from that — don't start from a fixed method.
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

`validate.py OUTPUT.png [--bg checker|black|white] [--keep-ground]` re-runs the
preview + metrics on any cutout — it always also writes a BLACK preview and reports
`%partial whitish` / `%img floating` so a halo can't hide on the gray checker.
Recheck the previews after every attempt — and even while iterating, keep the
user-facing answer discreet.
