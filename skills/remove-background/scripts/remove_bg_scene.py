#!/usr/bin/env python3
"""Remove the background from a BACK-LIT SCENE (bright sky over dark silhouettes).

For landscapes and skylines with no single salient subject — sunsets, trees,
poles and wires against a bright sky — the AI segmentation models return an
almost empty mask (``OBJETO_QUASE_VAZIO``): they are trained to find a product/
person/animal, not a whole scene. This script cuts such images by their actual
structure instead, keeping the dark foreground and erasing the bright sky:

- **luma threshold** (with a color cue for clearly blue sky): dark silhouette
  stays opaque, bright sky becomes transparent;
- **horizon line**: everything below it is solid foreground (this keeps the
  road/ground and stops a bright flare on the ground from being punched out);
- **soft radial guard** around a light source (the sun) so its glow is preserved
  instead of eaten as "bright".

It preserves the original pixels: only the alpha channel is computed (the image
is never regenerated).

The geometry is supplied by a caller that can SEE the image: the agent probes
the pixels (see ``analyze.py``), reconciles them with what it visually reads off
the picture, and passes ``--horizon``/``--sun``. There is no blind auto-detection
— without those, the defaults are the no-guess case (no solid band, no protected
light source), which the agent then calibrates against the preview.

Usage:
    python3 remove_bg_scene.py INPUT [OUTPUT]
        [--horizon Y|auto] [--sun X,Y|auto|none] [--sun-radius R]
        [--sky-lo L] [--sky-hi H] [--bluish D] [--no-clean]

Assumes a back-lit scene: bright sky over a darker foreground. It does not apply
to night scenes or to skies darker than the subject.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage

import common


def parse_point(s: str) -> tuple[int, int]:
    """Parse an ``"X,Y"`` string into an integer ``(x, y)`` pixel coordinate."""
    x, y = s.split(',')
    return int(round(float(x))), int(round(float(y)))


def main() -> None:
    """Cut a back-lit scene for the arguments on the command line."""
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='input image path')
    ap.add_argument('dst', nargs='?', help='output PNG path (default: <input>-sem-fundo.png)')
    ap.add_argument('--horizon', type=int, default=None,
                    help='ground line Y below which all stays solid foreground '
                         '(default: none; the caller supplies it after probing)')
    ap.add_argument('--sun', default=None,
                    help="light source to preserve, as 'X,Y' (default: none)")
    ap.add_argument('--sun-radius', type=float, default=0.0,
                    help='glow radius in px to preserve (0 = auto from image size)')
    ap.add_argument('--sky-lo', type=float, default=60.0,
                    help='luma at/below which a pixel is fully opaque silhouette')
    ap.add_argument('--sky-hi', type=float, default=108.0,
                    help='luma at/above which a pixel is fully transparent sky')
    ap.add_argument('--bluish', type=float, default=22.0,
                    help='B-R delta above which a non-dark pixel is treated as pure sky')
    ap.add_argument('--no-clean', action='store_true',
                    help='do not remove small islands (dust) from the alpha channel')
    a = ap.parse_args()

    dst = a.dst or os.path.splitext(a.src)[0] + '-sem-fundo.png'
    rgb = np.asarray(Image.open(a.src).convert('RGB'))
    rgbf = rgb.astype(np.float32)
    H, W, _ = rgbf.shape
    lum = ndimage.gaussian_filter(common.luma(rgbf), 1.0)
    R, B = rgbf[..., 0], rgbf[..., 2]

    # --- scene geometry: supplied by the caller that can SEE the image ---
    # No blind auto-detection. The agent probes the pixels (analyze.py),
    # reconciles them with the visual read, and passes the geometry; the defaults
    # are the no-guess case — no solid band, no protected light source.
    horizon = H if a.horizon is None else max(0, min(H, int(a.horizon)))
    sun_xy = parse_point(a.sun) if a.sun else None
    radius = a.sun_radius or 0.26 * min(H, W)

    # --- alpha: dark silhouette opaque, bright sky transparent ---
    alpha = np.clip((a.sky_hi - lum) / (a.sky_hi - a.sky_lo), 0.0, 1.0)
    alpha[((B - R) > a.bluish) & (lum > a.sky_lo + 30)] = 0.0  # clearly blue sky

    yy, xx = np.mgrid[0:H, 0:W]
    alpha[yy >= horizon] = 1.0  # solid foreground below the horizon

    if sun_xy is not None:
        dist = np.sqrt((xx - sun_xy[0]) ** 2 + (yy - sun_xy[1]) ** 2)
        core = 0.42 * radius
        guard = np.clip((radius - dist) / max(radius - core, 1.0), 0.0, 1.0)
        alpha = np.maximum(alpha, guard)  # glow fades into sky, no hard disc

    alpha = ndimage.gaussian_filter(alpha, 0.8)  # soften the seam
    alpha[yy >= horizon + 1] = 1.0               # re-assert the solid base

    al8 = (np.clip(alpha, 0.0, 1.0) * 255).astype(np.uint8)
    if not a.no_clean:
        al8 = common.remove_speckles(al8, 0.003)
    Image.fromarray(np.dstack([rgb, al8]), 'RGBA').save(dst)

    m = common.assess_alpha(al8)
    print('method: scene | input:', a.src, '| horizon:', horizon, '| sun:', sun_xy or 'none')
    print('saved:', dst, '| size:', (W, H))
    print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
          '| large components:', m['n_components_big'])
    print('flags:', m['flags'] or 'none')


if __name__ == '__main__':
    main()
