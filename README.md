# remove-background

A **Claude Code plugin** that removes the background from any image and makes it
transparent in an RGBA PNG. It works on the **original** pixels — it does not generate,
recreate, or redraw the image (no generative AI / inpainting).

It works with photos, illustrations, renders, icons, products, people, animals, and
objects, and independently chooses between two methods based on the background type:
edge-based flood fill (uniform/solid backgrounds) or AI segmentation (complex photos).

## Requirements

- **Python 3** with `pillow numpy scipy rembg onnxruntime`:
  ```bash
  pip3 install -r requirements.txt
  # or: pip3 install pillow numpy scipy rembg onnxruntime
  ```
- The `rembg` models are downloaded automatically to `~/.u2net/` on first use.
- ~6 GB of free RAM recommended (avoid the large `birefnet-general` model; use the `-lite` variant).

## Install

This repository is also its own [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).
Inside Claude Code:

```text
/plugin marketplace add rafaelcoelhox/remove-background
/plugin install remove-background@rafaelcoelhox
```

Then install the Python dependencies (see [Requirements](#requirements)).

## How Claude uses it

Just ask in natural language — the skill triggers automatically:

> "remove the bg from this image" · "cut this out" · "make the background transparent"

Claude follows the **analyze → cut out → validate** workflow and delivers the final PNG,
opening a checkerboard preview to confirm the result visually.

## Manual use (command line)

The scripts live in `skills/remove-background/scripts/`. Inside a Claude Code skill, reference
them with the `${CLAUDE_SKILL_DIR}` variable (it resolves to the installed skill directory on any
machine). To run them in a plain terminal, point `$S` at that folder.

**Primary approach — a single command** (chooses the method, cuts out, cleans, and validates):

```bash
S="${CLAUDE_SKILL_DIR}/scripts"   # inside Claude Code
# S=/path/to/remove-background/skills/remove-background/scripts   # standalone terminal

python3 "$S/run.py" image.png [output.png] \
                  [--method auto|solid|photo] [--model NAME] \
                  [--keep-largest] [--no-fallback]
```
Prints the final path, the preview (in `/tmp/`), and the `STATUS` (`OK` or flags).
If `output.png` is omitted, saves it as `<input>-sem-fundo.png`. For photos, it
switches models automatically when the result looks poor and removes detached islands.

**Quality flags** in `STATUS`: `CHECAR_CANTOS` (background at the edges),
`CHECAR_RESIDUO` (second large detached region), `OBJETO_QUASE_VAZIO` (empty mask),
`FUNDO_NAO_REMOVIDO` (almost everything is opaque). `OK` = automated checks passed;
it is **not** a guarantee — a distractor *attached* to the object does not trigger a flag; inspect the preview.

**Individual scripts** (for debugging or forcing a method/model):

```bash
python3 "$S/analyze.py" image.png                                  # background diagnostics
python3 "$S/remove_bg_solid.py" image.png [output.png]             # uniform background/solid color
python3 "$S/remove_bg_photo.py" image.png [output.png] [model] [--keep-largest]
python3 "$S/validate.py" output.png                                # checkerboard preview + metrics/flags
```

## Scripts

| Script | Function | Technique |
|---|---|---|
| `run.py` | **Single entry point**: chooses the method, cuts out, cleans, validates, and falls back to another model | Orchestrates the other scripts with minimal output |
| `common.py` | Shared helpers | Edge sampling, method selection, alpha cleanup and assessment, checkerboard preview |
| `analyze.py` | Inspects the image and recommends `solid` or `photo` | Edge uniformity + color distance |
| `remove_bg_solid.py` | Uniform background of any color | Component flood fill from the edges + Otsu + 1–2 px antialiasing + decontamination + island removal |
| `remove_bg_photo.py` | Natural photo / complex background | `rembg` segmentation + alpha matting (adaptive erosion) + alpha cleanup |
| `validate.py` | Checks the result | Checkerboard composition + alpha metrics/flags |

## Models (`remove_bg_photo.py` only)

| Model | When to use |
|---|---|
| `birefnet-general-lite` **(default)** | Best overall; complex scenes, objects with thin/metallic parts |
| `isnet-general-use` | Fast; portraits and simple objects |
| `u2net_human_seg` | People only |

⚠️ **Do not** use `birefnet-general` (large model): it exhausts the RAM in this environment (~6 GB free). Use the `-lite` variant.

## Guarantees and limitations

- Preserves resolution, dimensions, colors, texture, internal shadows, and fine details.
- Transparency is stored in the **real alpha channel** (never a drawn checkerboard); all 4 corners have alpha 0.
- A **watermark embedded in the pixels** (e.g., Vecteezy) is NOT removed by the cutout — removing it would require inpainting, which is out of scope.

## License

[MIT](LICENSE) © Rafael Coelho
