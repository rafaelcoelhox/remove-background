#!/usr/bin/env python3
"""Remove a UNIFORM background (solid color / flattened transparency checkerboard) of
any color while working on the original pixels. Identify the background from the
EDGES using connected components (not by color alone), generate alpha with
1-2 px antialiasing, and decontaminate the fringe color (without a halo).

Usage: python3 remove_bg_solid.py INPUT [OUTPUT]"""
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
import common


def otsu(values, nbins=256):
    """1D Otsu threshold for separating background (near) from object (far)."""
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


if len(sys.argv) < 2:
    sys.exit('usage: python3 remove_bg_solid.py INPUT [OUTPUT]')
SRC = sys.argv[1]
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(SRC)[0] + '-sem-fundo.png'

im = Image.open(SRC)
print('original mode:', im.mode, '| has real alpha?', 'A' in im.getbands())
rgb = np.asarray(im.convert('RGB')).astype(np.float32)
H, W, _ = rgb.shape

# background color sampled at the edges (shared helper)
bg_color = np.median(common.border_pixels(rgb), axis=0)
print('sampled background color:', bg_color.round(1))

# color distance from background + adaptive thresholds (Otsu)
dist = np.sqrt(((rgb - bg_color) ** 2).sum(2))
T = otsu(dist[dist < np.percentile(dist, 99)])  # ignore extreme outliers
HI = max(T, 12.0)            # above this = solid object
LO = max(T * 0.35, 8.0)      # below this = pure background
print('thresholds: LO=%.1f HI=%.1f (Otsu=%.1f)' % (LO, HI, T))

# background connected to the edges (solid object blocks the flood fill)
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

Image.fromarray(np.dstack([out, alpha]).astype(np.uint8), 'RGBA').save(DST)

m = common.assess_alpha(np.asarray(Image.open(DST))[:, :, 3])
print('--- saved:', DST, '| RGBA', (W, H))
print('corners:', m['corners'], '| %opaque:', m['pct_opaque'], '| %partial:', m['pct_partial'])
print('flags:', m['flags'] or 'none')
