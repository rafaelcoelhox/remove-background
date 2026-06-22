#!/usr/bin/env python3
"""Remove the background from a NATURAL PHOTO using foreground segmentation (rembg).
Preserve the original pixels; only calculate the alpha channel (do not generate a new image).

Usage: python3 remove_bg_photo.py INPUT [OUTPUT] [MODEL] [--keep-largest] [--no-clean]
  MODEL  birefnet-general-lite (default, best for complex scenes)
         | isnet-general-use (fast, portrait) | u2net_human_seg (people only)
         DO NOT use birefnet-general (large) -> exhausts RAM.
  --keep-largest  keep only the largest connected component (discard detached distractors)
  --no-clean      do not remove small islands (dust) from the alpha channel"""
import argparse
import os
import numpy as np
from PIL import Image
from rembg import remove, new_session
import common

ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('dst', nargs='?')
ap.add_argument('model', nargs='?', default='birefnet-general-lite')
ap.add_argument('--keep-largest', action='store_true')
ap.add_argument('--no-clean', action='store_true')
a = ap.parse_args()

SRC = a.src
DST = a.dst or os.path.splitext(SRC)[0] + '-sem-fundo.png'
MODEL = a.model

src = Image.open(SRC).convert('RGB')
W, H = src.size
# erode_size proportional to size: prevents loss of fine details in small images
erode = int(max(2, min(12, round(min(W, H) / 120))))

out = remove(
    src, session=new_session(MODEL),
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
Image.fromarray(arr, 'RGBA').save(DST)

m = common.assess_alpha(al)
print('model:', MODEL, '| input:', SRC, '| erode:', erode)
print('saved:', DST, '| size:', (W, H), '| dimensions preserved?', (W, H) == out.size)
print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
      '| large components:', m['n_components_big'])
print('flags:', m['flags'] or 'none')
