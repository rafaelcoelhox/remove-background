#!/usr/bin/env python3
"""Validate a cutout RGBA PNG.

Composites the cutout over a checkerboard AND a black background for visual
inspection (a light/white halo blends into the bright checker and only shows on
black), and prints the alpha-channel metrics, fringe/halo diagnostics, and
quality flags.

Usage:
    python3 validate.py OUTPUT.png [--bg checker|black|white] [--keep-ground]

``--keep-ground`` tells the check that the ground is intentionally kept to the
bottom edge, so filled BOTTOM corners are reported as expected instead of
tripping CHECAR_CANTOS (the top corners are still checked).
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image

import common


def main() -> None:
    """Validate the cutout PNG given on the command line."""
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='cutout RGBA PNG to validate')
    ap.add_argument('--bg', default='checker',
                    help='primary preview background: checker|black|white (default: checker)')
    ap.add_argument('--keep-ground', action='store_true',
                    help='ground is intentionally kept: do not flag filled bottom corners')
    a = ap.parse_args()

    p = a.src
    base = os.path.splitext(os.path.basename(p))[0]
    preview = '/tmp/validate_' + base + '.png'
    preview_black = '/tmp/validate_' + base + '_black.png'
    common.save_preview(p, preview, a.bg)
    common.save_preview(p, preview_black, 'black')

    rgba = np.asarray(Image.open(p).convert('RGBA'))
    al = rgba[:, :, 3]
    m = common.assess_alpha(al)
    fr = common.assess_fringe(rgba)

    flags = list(m['flags'])
    top_clear = m['corners'][0] == 0 and m['corners'][1] == 0
    if a.keep_ground and 'CHECAR_CANTOS' in flags and top_clear:
        flags.remove('CHECAR_CANTOS')  # bottom corners are intended ground
    # advisory halo flag (a 'go look at the black preview' hint, not a hard fail).
    # Keyed on the WHITISH fringe — the reliable leftover-background-halo signal;
    # floating-partial is printed as info only (foliage anti-aliasing floats too).
    if fr['pct_partial_whitish'] > 10.0 and fr['n_partial'] > max(50, 0.001 * al.size):
        flags.append('CHECAR_HALO')

    print('preview (open with Read):', preview)
    print('preview on black:', preview_black)
    print('dimensions:', m['WxH'])
    print('corners top:', m['corners'][:2], '| bottom:', m['corners'][2:],
          '| all alpha 0?', m['corners_ok'])
    print('%opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
          '| large components:', m['n_components_big'], '| largest fraction:', m['largest_frac'])
    print('fringe: %partial whitish:', fr['pct_partial_whitish'],
          '| %img floating:', fr['pct_img_floating'])
    print('STATUS:', 'OK' if not flags else ' '.join(flags))


if __name__ == '__main__':
    main()
