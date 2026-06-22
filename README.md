# remove-background

> Remove the background from any image and export a clean, transparent RGBA PNG —
> working on the original pixels, never regenerating or redrawing the image.

Handles photos, illustrations, icons, products, people, and objects. It picks the method
automatically: edge flood-fill for solid backgrounds, AI segmentation (`rembg`) for complex photos.

## Install

```
/plugin marketplace add rafaelcoelhox/remove-background
/plugin install remove-background@rafaelcoelhox
```

Install the Python dependencies once:

```bash
pip3 install pillow numpy scipy rembg onnxruntime
```

Then just ask Claude:

```
Remove the background from logo.png
```

## How it works

| Step | What happens |
| --- | --- |
| **Detect** | Picks edge flood-fill (solid/uniform backgrounds) or AI segmentation (natural photos). |
| **Cut out** | Isolates the subject on the original pixels — keeps resolution, colors, and fine detail. |
| **Validate** | Writes the transparent PNG and opens a checkerboard preview to confirm the result. |

> A watermark baked into the pixels (e.g. Vecteezy) can't be removed — that needs inpainting, which is out of scope.

## Advanced

Run the scripts yourself, or force a method/model from the command line:

```bash
cd skills/remove-background/scripts
python3 run.py image.png          # add --method, --model, --keep-largest, --no-fallback
```

See [`SKILL.md`](skills/remove-background/SKILL.md) for every option, model, and quality flag.

## Contributing & security

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

MIT © Rafael Coelho
