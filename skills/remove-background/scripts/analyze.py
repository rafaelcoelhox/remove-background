#!/usr/bin/env python3
"""Probe an image: the pixel half of the loop.

This is the measurement step an agent runs *after* looking at the image and
*before* choosing a method and calibrating it. It emits the numbers to reconcile
against the visual read — so "that dark mass is a tree, not the ground" is a
decision the viewer makes, not a threshold guesses. It reports the image size and
any existing alpha, the edge background color and its variation, region color
samples, the brightest point (a sun/specular), global contrast, the vertical
luminance profile (where sky / silhouette / ground sit), and which method
``run.py`` would route to as a starting point.

Usage:
    python3 analyze.py INPUT
"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image

import common


def main() -> None:
    """Probe the image path given on the command line."""
    args = sys.argv[1:]
    top_frac = 0.35
    if '--top' in args:                       # aim the sky band the viewer sees
        i = args.index('--top')
        top_frac = float(args[i + 1])
        del args[i:i + 2]
    if not args:
        sys.exit('usage: python3 analyze.py INPUT [--top FRAC]')

    im = Image.open(args[0])
    W, H = im.size
    real_alpha = 'A' in im.getbands() and bool(np.asarray(im)[:, :, 3].min() < 250)

    rgb = np.asarray(im.convert('RGB')).astype(np.float32)
    bg, std, near = common.border_stats(rgb)
    rec = common.decide_method(rgb)
    bx, by, bl = common.brightest_point(rgb)
    contrast = float(common.luma(rgb).std())

    print('size:', (W, H), '| already has real alpha:', real_alpha)
    print('background color (edges):', bg.round(1), '| edge std:', round(std, 1),
          '| fraction near it:', round(near, 2))
    print('global contrast (luma std):', round(contrast, 1),
          '| brightest px: (%d,%d)=%.0f at %d%%,%d%% of W,H'
          % (bx, by, bl, round(100 * bx / W), round(100 * by / H)))

    # region color samples — match these against the visual read (e.g. blue sky)
    def sample(x0: float, x1: float, y0: float, y1: float) -> np.ndarray:
        patch = rgb[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
        return patch.reshape(-1, 3).mean(0).round().astype(int)

    print('region RGB  TL:%s TR:%s mid:%s BL:%s BR:%s'
          % (sample(0, .2, 0, .2), sample(.8, 1, 0, .2), sample(.4, .6, .4, .6),
             sample(0, .2, .8, 1), sample(.8, 1, .8, 1)))

    # channel-difference separability — which color key cleanly splits a top
    # (usually-sky) band from the rest. Ranked by OVERLAP (not gap): a wide gap
    # with high overlap is a trap (e.g. 2G-R-B when clouds cross over). The viewer
    # labels the regions and picks the channel; nothing is auto-applied.
    print('channel split (top %d%% vs rest)   expr   top   rest    gap  overlap'
          % round(100 * top_frac))
    for i, r in enumerate(common.channel_separability(rgb, top_frac=top_frac)):
        print('  %6s  %5.0f  %5.0f  %5.0f   %4.1f%%   %s'
              % (r['expr'], r['top_mean'], r['rest_mean'], r['gap'],
                 100 * r['overlap'], '<- cleanest split' if i == 0 else ''))
    print('  (reconcile with region RGB: a tall subject inside the top band skews '
          'this; re-aim with --top FRAC)')

    # vertical luminance profile — where sky / silhouette / ground sit
    print('luminance profile (top->bottom):  y%   mean  %dark  %bright')
    for y0, _y1, mean, dark, bright in common.luminance_profile(rgb, bands=14):
        print('  %3d%%  %5.0f  %4.0f%%  %4.0f%%   %s'
              % (round(100 * y0 / H), mean, 100 * dark, 100 * bright, '#' * int(dark * 18)))

    print('RECOMMENDATION:', rec, '->',
          'remove_bg_solid.py' if rec == 'solid' else 'remove_bg_photo.py',
          '(back-lit scene with no salient subject -> remove_bg_scene.py)')
    if real_alpha:
        print('NOTE: image already has transparency; confirm whether it needs reprocessing.')


if __name__ == '__main__':
    main()
