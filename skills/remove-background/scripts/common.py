#!/usr/bin/env python3
"""Shared functions for the remove-background skill.

Consolidates what was duplicated across run.py / analyze.py / remove_bg_*:
edge sampling, method selection, alpha channel cleanup and assessment,
and checkerboard preview generation. Does not import rembg (kept lightweight)."""
import numpy as np
from PIL import Image
from scipy import ndimage

BORDER_K = 6  # thickness (px) of the sampled edge band


def load_rgb(path):
    return np.asarray(Image.open(path).convert('RGB')).astype(np.float32)


def border_pixels(rgb, k=BORDER_K):
    """Pixels from all four edges, stacked as (N, 3)."""
    return np.concatenate([
        rgb[:k].reshape(-1, 3), rgb[-k:].reshape(-1, 3),
        rgb[:, :k].reshape(-1, 3), rgb[:, -k:].reshape(-1, 3),
    ])


def border_stats(rgb, k=BORDER_K):
    """(background_color, edge_std, fraction_of_pixels_near_background)."""
    b = border_pixels(rgb, k)
    bg = np.median(b, axis=0)
    std = float(b.std(axis=0).mean())
    near = float((np.sqrt(((rgb - bg) ** 2).sum(2)) < 25).mean())
    return bg, std, near


def decide_method(rgb):
    """Return 'solid' if the edges are uniform AND a relevant portion is background; otherwise 'photo'."""
    _, std, near = border_stats(rgb)
    return 'solid' if (std < 18 and near > 0.15) else 'photo'


# ---------- alpha cleanup ----------
def remove_speckles(alpha, min_frac=0.003):
    """Zero foreground islands smaller than `min_frac` of the total foreground area.
    Remove detached dust/residue without touching the main object."""
    fg = alpha > 10
    lbl, n = ndimage.label(fg)
    if n <= 1:
        return alpha
    sizes = ndimage.sum(np.ones_like(lbl, np.float64), lbl, np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes >= (min_frac * fg.sum())
    out = alpha.copy()
    out[~keep[lbl]] = 0
    return out


def keep_largest_component(alpha):
    """Keep only the largest connected foreground component (discard distractors)."""
    fg = alpha > 10
    lbl, n = ndimage.label(fg)
    if n <= 1:
        return alpha
    sizes = ndimage.sum(np.ones_like(lbl, np.float64), lbl, np.arange(1, n + 1))
    biggest = int(np.argmax(sizes)) + 1
    out = alpha.copy()
    out[lbl != biggest] = 0
    return out


# ---------- quality assessment ----------
def assess_alpha(alpha):
    """Metrics + actionable cutout flags (alpha: HxW uint8 array)."""
    H, W = alpha.shape
    tot = H * W
    fg = alpha > 10
    pct_fg = 100 * fg.mean()
    corners = [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])]
    corners_ok = all(c == 0 for c in corners)

    lbl, n = ndimage.label(fg)
    largest_frac = second_over_largest = second_abs = 0.0
    n_big = 0
    if n >= 1:
        sizes = np.sort(ndimage.sum(np.ones_like(lbl, np.float64), lbl,
                                    np.arange(1, n + 1)))[::-1]
        largest = sizes[0]
        largest_frac = float(largest / max(fg.sum(), 1))
        n_big = int((sizes >= 0.05 * largest).sum())
        if len(sizes) > 1:
            second_over_largest = float(sizes[1] / largest)
            second_abs = float(sizes[1] / tot)

    flags = []
    if not corners_ok:
        flags.append('CHECAR_CANTOS')          # background remains touching the edges
    if pct_fg < 0.8:
        flags.append('OBJETO_QUASE_VAZIO')      # the object disappeared / empty mask
    if pct_fg > 92:
        flags.append('FUNDO_NAO_REMOVIDO')      # almost everything remained opaque
    if second_over_largest > 0.18 and second_abs > 0.02:
        flags.append('CHECAR_RESIDUO')          # second large component = distractor/residue

    return {
        'WxH': (W, H),
        'pct_fg': round(pct_fg, 1),
        'pct_opaque': round(100 * (alpha >= 250).mean(), 1),
        'pct_partial': round(100 * ((alpha > 10) & (alpha < 250)).mean(), 2),
        'corners': corners, 'corners_ok': corners_ok,
        'n_components_big': n_big,
        'largest_frac': round(largest_frac, 3),
        'second_over_largest': round(second_over_largest, 3),
        'flags': flags,
    }


# ---------- preview ----------
def checker_bg(H, W, sq=16, light=235, dark=170):
    """Neutral checkerboard background: reveals light AND dark halos and does not conceal green objects."""
    yy, xx = np.mgrid[0:H, 0:W]
    base = np.where(((yy // sq) + (xx // sq)) % 2 == 0, light, dark).astype(np.float32)
    return np.dstack([base, base, base])


def save_preview(rgba_path, out_path):
    """Composite the cutout over a checkerboard and save it for visual inspection."""
    r = np.asarray(Image.open(rgba_path).convert('RGBA')).astype(np.float32)
    rgb, al = r[:, :, :3], r[:, :, 3:4] / 255.0
    H, W = al.shape[:2]
    comp = rgb * al + checker_bg(H, W) * (1 - al)
    Image.fromarray(comp.astype(np.uint8)).save(out_path)
    return out_path
