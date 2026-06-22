---
name: remove-background
description: Remove the background from ANY image (photo, illustration, render, icon, product, person, animal, object), leaving it transparent in an RGBA PNG while working on the ORIGINAL pixels — without generating, recreating, or redrawing the image. Use when the user asks to "remove the background," "remove the bg," "cut out," "make transparent," or "isolate the object" in an image. Independently chooses between edge-based flood fill (uniform background/solid color/flattened checkerboard) and AI segmentation (natural photo with a complex background).
allowed-tools: Bash(python3 *), Read
---

# Remove an image background

## Communication (IMPORTANT — read before acting)
Be DISCREET. DO NOT narrate the internal process:
- DO NOT say which script, model, method, or technique you are using (nothing like "I'll use
  AI segmentation," "birefnet," "flood fill," "analyze.py," or "remove_bg_photo.py").
- DO NOT write "Step 1 / Step 2 / Step 3" or describe the pipeline.
- Do not use decorative emojis or give long explanations of the process.
- Use at most one short sentence before acting (e.g., "Removing the background...").
- Final response = brief: the path to the finished PNG + one confirmation line.
  Only provide technical details (method/model) if the user asks.

## How to run
A single command does everything (choose method + cut out + clean + validate). Run it and nothing else:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/run.py INPUT [OUTPUT]
```
`${CLAUDE_SKILL_DIR}` is provided by Claude Code and resolves to this skill's directory on any
machine, so the path works regardless of where the plugin is installed or the current directory.
It prints 3 lines: `final path`, `PREVIEW <path>`, `STATUS WxH`.
Default output: `<input>-sem-fundo.png`. For photos, it switches models automatically if the
result looks poor (fallback) and automatically removes detached islands.

`STATUS` is `OK` or one or more flags:
- `CHECAR_CANTOS` — some background remains touching the edges.
- `CHECAR_RESIDUO` — there is a second large detached region (likely residue/distractor).
- `OBJETO_QUASE_VAZIO` — the mask is nearly empty (the object disappeared).
- `FUNDO_NAO_REMOVIDO` — almost everything remained opaque (the background was not removed).

Useful flags: `--model NAME` (forces a model), `--method solid|photo|auto`,
`--keep-largest` (keeps only the largest piece — discards detached distractors),
`--no-fallback`.

**ALWAYS open the `PREVIEW` with the Read tool** and inspect it visually (complete
object, no halo/residue, transparent corners). `OK` only means that the automated
checks passed — **it is not a guarantee**. In particular, a distractor **attached**
to the object (a figure printed on a panel/banner behind it, another person touching
it, a reflection) becomes a single piece and **does not trigger a flag**: only visual
inspection will catch it. If there is a flag or the preview shows a problem, see "Fine-tuning."

## Expected result / rules
- Work on the original pixels (no generation/inpainting). RGBA PNG, real alpha.
- Preserve resolution, dimensions, texture, colors, internal shadows, and fine details.
- A **watermark embedded in the pixels** (e.g., Vecteezy) is NOT removed by the cutout — explain
  that removing it would require inpainting (out of scope). State this briefly.

## Fine-tuning (only if the result has problems)
Internal scripts (in `${CLAUDE_SKILL_DIR}/scripts/`) that can be called directly:
`analyze.py` (diagnostics), `remove_bg_solid.py`,
`remove_bg_photo.py INPUT OUTPUT [MODEL] [--keep-largest]`,
`validate.py` (checkerboard preview + metrics/flags). `common.py` contains the helpers.
Prefix each with `python3 ${CLAUDE_SKILL_DIR}/scripts/` when calling them.

Escalate from the least to the most expensive option:

1. **Switch models.** `birefnet-general-lite` (default), `isnet-general-use`
   (fast; sometimes captures *less* background, useful against distractors), `u2net_human_seg`
   (people only — excellent for portraits). DO NOT use `birefnet-general` — it exhausts RAM.
2. **DETACHED distractor/residue** (regions separate from the object): `--keep-largest`
   keeps only the largest component. (`run.py` already removes small islands automatically.)
3. **Distractor ATTACHED to the object** (a figure printed on the panel behind it, another
   person touching it, a reflection): no model separates it automatically — it becomes a single piece. Then:
   - **Focus/sharpness**: the real object is usually sharp and the background is blurred.
     Use a smoothed `|Laplacian|` (`scipy.ndimage`) as a sharpness map and
     keep only the sharp region. ⚠️ Smooth interiors (a shirt, a solid-color wall)
     are also "less sharp" — combine with `binary_opening`/largest component and
     dilate it back to avoid creating holes in the object.
   - **Geometric cut**: when the boundary is clear, cut out a polygon
     (`PIL.ImageDraw`) along the object's edge and set alpha to zero outside it. Inspect it on
     a coordinate grid and iterate using the preview.
   - **GrabCut (`cv2`) rarely helps here**: if the distractor has a color similar
     to the object (e.g., skin tone), the color model classifies it as
     foreground and brings it back.
4. Always recheck the `PREVIEW` (Read) after every attempt.

Even while debugging, keep communication with the user discreet.
