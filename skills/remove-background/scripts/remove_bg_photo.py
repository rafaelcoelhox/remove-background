#!/usr/bin/env python3
"""Remove the background from a NATURAL PHOTO using foreground segmentation (rembg).

Preserves the original pixels: only the alpha channel is computed (the image is
never regenerated). Uses alpha matting with an erosion size that scales with the
image so fine details survive on small images, then optionally cleans the alpha.

Usage:
    python3 remove_bg_photo.py INPUT [OUTPUT] [MODEL] [--keep-largest] [--no-clean]

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
    erode = int(max(2, min(12, round(min(W, H) / 120))))

    out = remove(
        img, session=new_session(model),
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
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
    print('model:', model, '| input:', src, '| erode:', erode)
    print('saved:', dst, '| size:', (W, H), '| dimensions preserved?', (W, H) == out.size)
    print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
          '| large components:', m['n_components_big'])
    print('flags:', m['flags'] or 'none')


if __name__ == '__main__':
    main()
