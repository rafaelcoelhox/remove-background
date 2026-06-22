#!/usr/bin/env python3
"""Remove a UNIFORM background (solid color or flattened transparency checkerboard).

Works on the original pixels. The background is identified from the image EDGES
using connected components (not by color alone), so a solid-colored object is
preserved. Alpha is generated with 1–2 px of antialiasing on the fringe, and the
fringe color is decontaminated so no halo remains.

Usage:
    python3 remove_bg_solid.py INPUT [OUTPUT] [--hi D] [--lo D] [--bg-color R,G,B]

Thresholds default to an Otsu split of the edge-distance histogram; override
``--hi``/``--lo`` (or key a specific ``--bg-color``) when the auto split clips
the object or leaves background — the agent calibrates these against the preview.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage

import common


def otsu(values: np.ndarray, nbins: int = 256) -> float:
    """Compute a 1-D Otsu threshold.

    Finds the value that best separates the background (near the sampled color)
    from the object (far from it) by maximizing the between-class variance of the
    distance histogram.

    Args:
        values: 1-D array of color distances.
        nbins: Number of histogram bins.

    Returns:
        The threshold value, or the mean of ``values`` when the histogram is empty.
    """
    hist, edges = np.histogram(values, bins=nbins)
    centers = (edges[:-1] + edges[1:]) / 2
    total = hist.sum()
    if total == 0:
        return float(values.mean())
    w = np.cumsum(hist).astype(np.float64)
    cum_mean = np.cumsum(hist * centers)
    mu_total = cum_mean[-1]
    wf = total - w
    with np.errstate(divide='ignore', invalid='ignore'):
        mu_b = np.where(w > 0, cum_mean / w, 0)
        mu_f = np.where(wf > 0, (mu_total - cum_mean) / wf, 0)
    between = w * wf * (mu_b - mu_f) ** 2
    return float(centers[np.argmax(between)])


def main() -> None:
    """Cut out a solid background from the image path(s) on the command line."""
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='input image path')
    ap.add_argument('dst', nargs='?', help='output PNG path (default: <input>-sem-fundo.png)')
    ap.add_argument('--hi', type=float,
                    help='color distance above which a pixel is solid object (override Otsu)')
    ap.add_argument('--lo', type=float,
                    help='color distance below which a pixel is pure background (override Otsu)')
    ap.add_argument('--bg-color', dest='bg_color',
                    help="background color 'R,G,B' to key out (default: sampled from edges)")
    a = ap.parse_args()
    src = a.src
    dst = a.dst or os.path.splitext(src)[0] + '-sem-fundo.png'

    im = Image.open(src)
    print('original mode:', im.mode, '| has real alpha?', 'A' in im.getbands())
    rgb = np.asarray(im.convert('RGB')).astype(np.float32)
    H, W, _ = rgb.shape

    # background color: keyed by the caller, or sampled at the edges (shared helper)
    if a.bg_color:
        bg_color = np.array([float(v) for v in a.bg_color.split(',')], dtype=np.float32)
    else:
        bg_color = np.median(common.border_pixels(rgb), axis=0)
    print('background color:', bg_color.round(1), '(given)' if a.bg_color else '(sampled)')

    # color distance from background + thresholds (Otsu default, caller may override)
    dist = np.sqrt(((rgb - bg_color) ** 2).sum(2))
    T = otsu(dist[dist < np.percentile(dist, 99)])  # ignore extreme outliers
    HI = a.hi if a.hi is not None else max(T, 12.0)        # above this = solid object
    LO = a.lo if a.lo is not None else max(T * 0.35, 8.0)  # below this = pure background
    print('thresholds: LO=%.1f HI=%.1f (Otsu=%.1f)' % (LO, HI, T))

    # background connected to the edges (a solid object blocks the flood fill)
    transitable = dist < HI
    lbl, _ = ndimage.label(transitable, structure=np.ones((3, 3)))
    border_labels = np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    region_bg = np.isin(lbl, border_labels)
    print('background px connected to edge: %.2f%%' % (100 * region_bg.mean()))

    # alpha: background 0, object 255, antialiasing ramp only on the adjacent fringe
    ramp = np.clip((dist - LO) / (HI - LO), 0.0, 1.0)
    obj = ~region_bg
    band = ndimage.binary_dilation(obj, iterations=2) & region_bg
    alpha = np.zeros((H, W), dtype=np.float32)
    alpha[obj] = 255.0
    alpha[band] = ramp[band] * 255.0

    # fringe color decontamination (remove background-color halo)
    out = rgb.copy()
    a = alpha / 255.0
    fringe = (alpha > 0) & (alpha < 255)
    af = a[fringe][:, None]
    F = (out[fringe] - (1.0 - af) * bg_color[None, :]) / np.clip(af, 1e-3, 1.0)
    out[fringe] = np.clip(F, 0, 255)

    # remove detached islands (background residue not connected to the edges)
    alpha = common.remove_speckles(alpha.astype(np.uint8), 0.003).astype(np.float32)

    Image.fromarray(np.dstack([out, alpha]).astype(np.uint8), 'RGBA').save(dst)

    m = common.assess_alpha(np.asarray(Image.open(dst))[:, :, 3])
    print('--- saved:', dst, '| RGBA', (W, H))
    print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'])
    print('flags:', m['flags'] or 'none')


if __name__ == '__main__':
    main()
