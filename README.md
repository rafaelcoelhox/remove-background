# remove-background

> A Claude Code plugin that erases the background of any image and saves it as a
> transparent PNG — working on the **original pixels**, with no AI generation or redrawing.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`remove-background` cuts out the subject of an image and makes everything else transparent.
It handles photos, illustrations, renders, icons, products, people, animals, and objects, and
picks the right technique automatically:

- **Edge flood fill** — for uniform / solid-color backgrounds (clean antialiasing, no halo).
- **AI segmentation** (`rembg`) — for natural photos and complex backgrounds.

It never invents pixels: resolution, colors, texture, internal shadows, and fine details are
preserved, and the transparency lives in a real alpha channel.

## Features

- Works on any image type — automatically chooses the best method.
- Real RGBA alpha output (not a drawn checkerboard).
- Automatic model fallback + quality validation with actionable flags.
- Checkerboard preview so you can inspect the cutout visually.
- 100% local — your images never leave your machine.

## Quick start

1. **Install the plugin** inside Claude Code:
   ```text
   /plugin marketplace add rafaelcoelhox/remove-background
   /plugin install remove-background@rafaelcoelhox
   ```

2. **Install the Python dependencies** (one time):
   ```bash
   pip3 install -r requirements.txt
   # or: pip3 install pillow numpy scipy rembg onnxruntime
   ```

3. **Just ask** — in natural language:
   > "remove the background from this image" · "cut this out" · "make it transparent"

   Claude runs the **analyze → cut out → validate** workflow, hands back the finished PNG,
   and opens a checkerboard preview so you can confirm the result.

## Requirements

- **Python 3** with: `pillow`, `numpy`, `scipy`, `rembg`, `onnxruntime`.
- For photos, `rembg` downloads its model to `~/.u2net/` automatically on first use.
- **Memory:** the default `birefnet-general-lite` model is lightweight. The full
  `birefnet-general` model gives slightly cleaner edges but needs more RAM — use it only on
  machines with memory to spare.

## How it works

1. **Analyze** — samples the image edges to decide between a uniform background (*solid*) and
   a complex one (*photo*).
2. **Cut out**
   - *Solid:* flood-fills the background from the edges (connected components + Otsu
     threshold), adds 1–2 px antialiasing, and decontaminates the color fringe so there's no halo.
   - *Photo:* runs `rembg` segmentation with alpha matting, then cleans the alpha channel.
3. **Validate** — composites the result over a checkerboard and reports metrics + quality flags.

## Command-line use (optional / advanced)

You normally never run the scripts yourself — Claude does it for you. But they also work
standalone, which is handy for debugging or batch jobs. They live in
`skills/remove-background/scripts/`:

```bash
cd skills/remove-background/scripts
python3 run.py input.png [output.png]
```

`run.py` is the single entry point: it chooses the method, cuts out, cleans, validates, and
(for photos) falls back to another model if the result looks poor. If you omit the output path
it saves `<input>-sem-fundo.png`. It prints three lines: the output path, the preview path
(in `/tmp/`), and a `STATUS`.

**Options:**

| Option | Effect |
|---|---|
| `--method auto\|solid\|photo` | Force the technique (default: `auto`). |
| `--model NAME` | Force a specific photo model. |
| `--keep-largest` | Keep only the largest piece — discards detached distractors. |
| `--no-fallback` | Don't try other models for photos. |

**`STATUS` values** — `OK`, or one or more flags:

| Flag | Meaning |
|---|---|
| `CHECAR_CANTOS` | Background still touches the edges. |
| `CHECAR_RESIDUO` | A second large detached region remains (likely residue/distractor). |
| `OBJETO_QUASE_VAZIO` | The mask is nearly empty (subject disappeared). |
| `FUNDO_NAO_REMOVIDO` | Almost everything stayed opaque (background not removed). |

> `OK` means the automated checks passed — it is **not** a guarantee. A distractor *attached*
> to the subject won't raise a flag; always inspect the preview.

<details>
<summary>Individual scripts (deep debugging)</summary>

```bash
python3 analyze.py input.png                              # diagnose the background, recommend a method
python3 remove_bg_solid.py input.png [output.png]         # uniform / solid-color background
python3 remove_bg_photo.py input.png [output.png] [model] # natural photo (rembg)
python3 validate.py output.png                            # checkerboard preview + metrics/flags
```

`common.py` holds the shared helpers (edge sampling, method selection, alpha cleanup, preview).
</details>

## Models (photos only)

| Model | When to use |
|---|---|
| `birefnet-general-lite` **(default)** | Best overall; complex scenes, thin/metallic parts. |
| `isnet-general-use` | Fast; portraits and simple objects. |
| `u2net_human_seg` | People only. |

## Limitations

- A **watermark baked into the pixels** (e.g. Vecteezy) is *not* removed — that would require
  inpainting (redrawing pixels), which is out of scope.
- A distractor **physically attached** to the subject (a figure printed on a panel behind it,
  a reflection) becomes a single piece and isn't auto-separated — inspect the preview and use
  `--keep-largest` or a manual touch-up.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup, how to
test, and the pull-request process.

## Security

The plugin runs locally and processes images on your machine (no uploads, no telemetry). To
report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Rafael Coelho
