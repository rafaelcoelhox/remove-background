#!/usr/bin/env python3
"""Validate a cutout RGBA PNG: composite it over a checkerboard for visual inspection and
report metrics + quality flags. Usage: python3 validate.py OUTPUT.png"""
import os
import sys
import numpy as np
from PIL import Image
import common

if len(sys.argv) < 2:
    sys.exit('usage: python3 validate.py OUTPUT.png')
p = sys.argv[1]
preview = '/tmp/validate_' + os.path.splitext(os.path.basename(p))[0] + '.png'
common.save_preview(p, preview)

al = np.asarray(Image.open(p).convert('RGBA'))[:, :, 3]
m = common.assess_alpha(al)
print('preview (open with Read):', preview)
print('dimensions:', m['WxH'])
print('corners:', m['corners'], '| all alpha 0?', m['corners_ok'])
print('%opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
      '| large components:', m['n_components_big'], '| largest fraction:', m['largest_frac'])
print('STATUS:', 'OK' if not m['flags'] else ' '.join(m['flags']))
