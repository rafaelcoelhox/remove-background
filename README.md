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
| **Look + probe** | Reads the image and measures the pixels (edge background, luminance profile, brightest point) to choose the right method. |
| **Cut + calibrate** | Edge flood-fill, AI segmentation, or a luma scene cut — tuned to the image, on the original pixels (keeps resolution, colors, detail). |
| **Review** | Writes the transparent PNG and checks a checkerboard preview, refining until the cutout is clean. |

> A watermark baked into the pixels (e.g. Vecteezy) can't be removed — that needs inpainting, which is out of scope.

## Advanced

The scripts are a small toolkit you can drive directly:

```bash
cd skills/remove-background/scripts
python3 analyze.py image.png       # probe: luminance profile, brightest point, recommended method
python3 run.py image.png           # one-shot shortcut (auto-picks solid/photo)
# …or a method directly, with calibration knobs:
python3 remove_bg_photo.py image.png out.png --fg-threshold 250 --erode 4
python3 remove_bg_scene.py image.png out.png --horizon 345 --sun 262,320
```

See [`SKILL.md`](skills/remove-background/SKILL.md) for the full loop, every method, knob, and quality flag.

## Contributing & security

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

MIT © Rafael Coelho
