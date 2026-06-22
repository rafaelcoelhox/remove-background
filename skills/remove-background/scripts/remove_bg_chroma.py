#!/usr/bin/env python3
"""Remove the background by a CHANNEL-DIFFERENCE color key (partial-background cut).

For the case no other method handles: a colored background (a blue sky, a green
screen) must go, while a salient subject AND a co-equal region (the ground a
product sits on, the grass under a tree) must STAY. Segmentation (`remove_bg_photo`)
keeps one and drops the other; an edge flood fill (`remove_bg_solid`) keying ONE
color fails when a barrier color sits between the background and the foreground
(white clouds between a blue sky and green foliage are far from both); a luma cut
(`remove_bg_scene`) erases thin mid-tone parts like a trunk.

This keys on a channel DIFFERENCE the agent picks after probing (`analyze.py`
prints which difference splits a top band most cleanly): e.g. G-B puts blue sky
(negative) and green vegetation (positive) on opposite sides of a threshold, which
no distance-from-one-color can do. The cut works on the ORIGINAL pixels (only the
alpha channel is computed).

Geometry and the key are supplied by a caller that can SEE the image — there is no
auto-detection:

- ``--channel`` + ``--lo``/``--hi``: the soft alpha ramp on the chosen difference;
- ``--keep-below``: an agent-drawn ground line (flat Y or control points) below
  which everything stays solid — the structural prior for a continuous ground;
- ``--decontam local``: un-mix the LOCAL background color out of the fringe (kills
  a white-cloud / blue-sky halo the soft edge keeps);
- ``--gate``: drop partial-alpha fragments not connected to the opaque core.

Usage:
    python3 remove_bg_chroma.py INPUT [OUTPUT]
        --channel g-b|b-r|r-b|g-r|2g-r-b|"a,b,c"
        [--lo L] [--hi H] [--invert]
        [--keep-below "Y" | "x0:y0,x1:y1,..."]
        [--decontam off|local|"R,G,B"] [--gate] [--gate-reach N] [--no-clean]
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image

import common

#: Named channel differences as ``(R, G, B)`` coefficients of ``a*R + b*G + c*B``.
CHANNELS = {
    'g-b': (0.0, 1.0, -1.0), 'b-r': (-1.0, 0.0, 1.0), 'r-b': (1.0, 0.0, -1.0),
    'g-r': (-1.0, 1.0, 0.0), '2g-r-b': (-1.0, 2.0, -1.0),
}


def parse_channel(spec: str) -> tuple[float, float, float]:
    """Return the ``(R, G, B)`` coefficients for a named or custom channel.

    Args:
        spec: A named difference (``'g-b'`` …) or a custom ``'a,b,c'`` triple.

    Returns:
        The three signed float coefficients. Parsed without ``eval``.
    """
    key = spec.strip().lower()
    if key in CHANNELS:
        return CHANNELS[key]
    parts = [float(v) for v in spec.split(',')]
    if len(parts) != 3:
        raise SystemExit("--channel must be a name (g-b, b-r, ...) or 'a,b,c'")
    return tuple(parts)  # type: ignore[return-value]


def main() -> None:
    """Cut a partial background by a channel-difference key for the CLI arguments."""
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='input image path')
    ap.add_argument('dst', nargs='?', help='output PNG path (default: <input>-sem-fundo.png)')
    ap.add_argument('--channel', required=True,
                    help="channel difference to key on: g-b|b-r|r-b|g-r|2g-r-b or 'a,b,c'")
    ap.add_argument('--lo', type=float, default=0.0,
                    help='channel value at/below which a pixel is pure background (default: 0)')
    ap.add_argument('--hi', type=float, default=16.0,
                    help='channel value at/above which a pixel is solid object (default: 16)')
    ap.add_argument('--invert', action='store_true',
                    help='object is the LOW side of the channel (background is the high side)')
    ap.add_argument('--keep-below', dest='keep_below', default=None,
                    help="ground line below which all stays solid: flat 'Y' or 'x0:y0,x1:y1,...'")
    ap.add_argument('--decontam', default='off',
                    help="fringe decontamination: off | local | 'R,G,B' (default: off)")
    ap.add_argument('--gate', action='store_true',
                    help='drop partial-alpha fragments not connected to the opaque core')
    ap.add_argument('--gate-reach', dest='gate_reach', type=int, default=1,
                    help='ring distance in px for --gate (default: 1)')
    ap.add_argument('--no-clean', action='store_true',
                    help='do not remove small detached islands')
    a = ap.parse_args()

    dst = a.dst or os.path.splitext(a.src)[0] + '-sem-fundo.png'
    rgb = np.asarray(Image.open(a.src).convert('RGB')).astype(np.float32)
    H, W, _ = rgb.shape

    cr, cg, cb = parse_channel(a.channel)
    v = cr * rgb[..., 0] + cg * rgb[..., 1] + cb * rgb[..., 2]

    # soft alpha ramp: object on the high side of the channel (or low if --invert)
    span = max(a.hi - a.lo, 1e-6)
    alpha = np.clip((v - a.lo) / span, 0.0, 1.0)
    if a.invert:
        alpha = 1.0 - alpha

    # structural prior: agent-drawn ground line, below which everything is solid
    if a.keep_below is not None:
        hy = common.horizon_curve(H, W, a.keep_below)
        yy = np.mgrid[0:H, 0:W][0]
        alpha[yy >= hy[None, :]] = 1.0

    al8 = (alpha * 255).astype(np.uint8)

    # decontaminate the fringe (kills a colored halo the soft edge keeps)
    out = rgb
    if a.decontam != 'off':
        if a.decontam == 'local':
            bg = common.local_bg_field(rgb, al8)
        else:
            bg = np.array([float(x) for x in a.decontam.split(',')], dtype=np.float32)
        out = common.decontaminate_fringe(rgb, al8, bg)

    if a.gate:
        al8 = common.gate_partial_to_core(al8, reach=a.gate_reach)
    if not a.no_clean:
        al8 = common.remove_speckles(al8, 0.003)

    Image.fromarray(np.dstack([out, al8]).astype(np.uint8), 'RGBA').save(dst)

    # report: channel value distribution (to calibrate lo/hi) + cut metrics
    p5, p50, p95 = (float(x) for x in np.percentile(v, [5, 50, 95]))
    m = common.assess_alpha(al8)
    fr = common.assess_fringe(np.dstack([out, al8]).astype(np.uint8))
    print('method: chroma | channel:', a.channel, '(%.0f,%.0f,%.0f)' % (cr, cg, cb),
          '| lo/hi: %.1f/%.1f' % (a.lo, a.hi), '| invert:', a.invert)
    print('channel value p5/p50/p95: %.1f / %.1f / %.1f' % (p5, p50, p95),
          '| keep-below:', a.keep_below or 'none', '| decontam:', a.decontam, '| gate:', a.gate)
    print('saved:', dst, '| size:', (W, H))
    print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'],
          '| large components:', m['n_components_big'])
    print('fringe: %partial whitish:', fr['pct_partial_whitish'],
          '| %img floating:', fr['pct_img_floating'])
    print('flags:', m['flags'] or 'none')


if __name__ == '__main__':
    main()
