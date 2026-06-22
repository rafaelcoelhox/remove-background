#!/usr/bin/env python3
"""Remove the background from a NATURAL PHOTO using foreground segmentation (rembg).

Preserves the original pixels: only the alpha channel is computed (the image is
never regenerated). Uses alpha matting with an erosion size that scales with the
image so fine details survive on small images, then optionally cleans the alpha.

Usage:
    python3 remove_bg_photo.py INPUT [OUTPUT] [MODEL]
        [--fg-threshold N] [--bg-threshold N] [--erode N] [--keep-largest] [--no-clean]

The matting thresholds and erode size default to sensible values; override them
when calibrating a stubborn edge (halo, eaten detail) against the preview.

Models:
    birefnet-general-lite  default, best for complex scenes
    isnet-general-use      fast, good for portraits and simple objects
    u2net_human_seg        people only

    The full ``birefnet-general`` model gives marginally cleaner edges but is much
    heavier on RAM; prefer the ``-lite`` variant unless you have ample memory.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image
from rembg import remove, new_session

import common


def main() -> None:
    """Run rembg segmentation for the arguments on the command line."""
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='input image path')
    ap.add_argument('dst', nargs='?', help='output PNG path (default: <input>-sem-fundo.png)')
    ap.add_argument('model', nargs='?', default='birefnet-general-lite',
                    help='rembg model name (default: birefnet-general-lite)')
    ap.add_argument('--fg-threshold', dest='fg', type=int, default=240,
                    help='alpha-matting foreground threshold, 0-255 (higher = stricter core)')
    ap.add_argument('--bg-threshold', dest='bg', type=int, default=10,
                    help='alpha-matting background threshold, 0-255 (lower = stricter background)')
    ap.add_argument('--erode', type=int, default=None,
                    help='alpha-matting erode size in px (default: auto from image size)')
    ap.add_argument('--keep-largest', action='store_true',
                    help='keep only the largest connected component (discard detached distractors)')
    ap.add_argument('--no-clean', action='store_true',
                    help='do not remove small islands (dust) from the alpha channel')
    a = ap.parse_args()

    src = a.src
    dst = a.dst or os.path.splitext(src)[0] + '-sem-fundo.png'
    model = a.model

    img = Image.open(src).convert('RGB')
    W, H = img.size
    # erode_size proportional to size: prevents loss of fine details in small images
    erode = a.erode if a.erode is not None else int(max(2, min(12, round(min(W, H) / 120))))

    out = remove(
        img, session=new_session(model),
        alpha_matting=True,
        alpha_matting_foreground_threshold=a.fg,
        alpha_matting_background_threshold=a.bg,
        alpha_matting_erode_size=erode,
        post_process_mask=True,
    ).convert('RGBA')

    arr = np.asarray(out).copy()
    al = arr[:, :, 3]
    if a.keep_largest:
        al = common.keep_largest_component(al)
    elif not a.no_clean:
        al = common.remove_speckles(al, 0.003)
    arr[:, :, 3] = al
    Image.fromarray(arr, 'RGBA').save(dst)

    m = common.assess_alpha(al)
    print('model:', model, '| input:', src,
          '| fg:', a.fg, '| bg:', a.bg, '| erode:', erode)
    print('saved:', dst, '| size:', (W, H), '| dimensions preserved?', (W, H) == out.size)
    print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
          '| large components:', m['n_components_big'])
    print('flags:', m['flags'] or 'none')


if __name__ == '__main__':
    main()
