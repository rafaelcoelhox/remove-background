#!/usr/bin/env python3
"""Inspect an image and recommend a background removal method.
Usage: python3 analyze.py INPUT"""
import sys
import numpy as np
from PIL import Image
import common

if len(sys.argv) < 2:
    sys.exit('usage: python3 analyze.py INPUT')

im = Image.open(sys.argv[1])
W, H = im.size
real_alpha = False
if 'A' in im.getbands():
    real_alpha = bool(np.asarray(im)[:, :, 3].min() < 250)  # already contains transparency

rgb = np.asarray(im.convert('RGB')).astype(np.float32)
bg, std, near = common.border_stats(rgb)
rec = common.decide_method(rgb)

print('size:', (W, H), '| already has real alpha:', real_alpha)
print('background color (edges):', bg.round(1), '| edge std:', round(std, 1))
print('fraction near the background color:', round(near, 2))
print('RECOMMENDATION:', rec,
      '->', 'remove_bg_solid.py' if rec == 'solid' else 'remove_bg_photo.py')
if real_alpha:
    print('NOTE: the image already has an alpha channel with transparency; confirm whether it needs reprocessing.')
