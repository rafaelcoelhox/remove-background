#!/usr/bin/env python3
"""Shared helpers for the remove-background skill.

This module centralizes the logic reused by the entry point (``run.py``) and the
individual scripts: edge sampling, background-method selection, alpha-channel
cleanup, cutout quality assessment, and checkerboard preview generation.

It deliberately avoids importing ``rembg`` so it stays lightweight and quick to
import for the steps that do not need AI segmentation.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

#: Thickness, in pixels, of the edge band sampled to characterize the background.
BORDER_K = 6


def load_rgb(path: str) -> np.ndarray:
    """Load an image as a float32 RGB array.

    Args:
        path: Path to the image file.

    Returns:
        The pixels as a float32 array with shape ``(H, W, 3)``.
    """
    return np.asarray(Image.open(path).convert('RGB')).astype(np.float32)


def border_pixels(rgb: np.ndarray, k: int = BORDER_K) -> np.ndarray:
    """Collect the pixels from all four edges of an image.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)``.
        k: Thickness in pixels of the edge band to sample.

    Returns:
        The sampled edge pixels stacked into an ``(N, 3)`` array.
    """
    return np.concatenate([
        rgb[:k].reshape(-1, 3), rgb[-k:].reshape(-1, 3),
        rgb[:, :k].reshape(-1, 3), rgb[:, -k:].reshape(-1, 3),
    ])


def border_stats(rgb: np.ndarray, k: int = BORDER_K) -> tuple[np.ndarray, float, float]:
    """Summarize the background from the image edges.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)``.
        k: Thickness in pixels of the edge band to sample.

    Returns:
        A tuple ``(bg_color, edge_std, near_fraction)``:

        - ``bg_color``: median edge color as a ``(3,)`` array;
        - ``edge_std``: mean per-channel standard deviation of the edge band;
        - ``near_fraction``: fraction of the whole image within color distance 25
          of ``bg_color``.
    """
    b = border_pixels(rgb, k)
    bg = np.median(b, axis=0)
    std = float(b.std(axis=0).mean())
    near = float((np.sqrt(((rgb - bg) ** 2).sum(2)) < 25).mean())
    return bg, std, near


def decide_method(rgb: np.ndarray) -> str:
    """Choose the cutout method for an image.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)``.

    Returns:
        ``'solid'`` when the edges are uniform and a meaningful portion of the
        image matches the background color; otherwise ``'photo'``.
    """
    _, std, near = border_stats(rgb)
    return 'solid' if (std < 18 and near > 0.15) else 'photo'


# ---------- alpha cleanup ----------
def remove_speckles(alpha: np.ndarray, min_frac: float = 0.003) -> np.ndarray:
    """Drop tiny foreground islands from an alpha channel.

    Zeroes every connected foreground island smaller than ``min_frac`` of the
    total foreground area, removing detached dust/residue without touching the
    main subject.

    Args:
        alpha: Alpha channel as an ``(H, W)`` uint8 array.
        min_frac: Minimum island size to keep, as a fraction of the foreground area.

    Returns:
        A copy of ``alpha`` with the small islands set to 0. If there is at most
        one island, the input array is returned unchanged.
    """
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


def keep_largest_component(alpha: np.ndarray) -> np.ndarray:
    """Keep only the largest connected foreground component.

    Useful to discard distractors that are detached from the main subject.

    Args:
        alpha: Alpha channel as an ``(H, W)`` uint8 array.

    Returns:
        A copy of ``alpha`` with everything except the largest component set to
        0. If there is at most one component, the input array is returned unchanged.
    """
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
def assess_alpha(alpha: np.ndarray) -> dict:
    """Compute cutout metrics and actionable quality flags from an alpha channel.

    Args:
        alpha: Alpha channel as an ``(H, W)`` uint8 array.

    Returns:
        A dict describing the cutout. The ``'flags'`` key holds a list of
        problems detected (empty means the automated checks passed):

        - ``CHECAR_CANTOS``: background still touches the image corners;
        - ``OBJETO_QUASE_VAZIO``: the mask is nearly empty (subject lost);
        - ``FUNDO_NAO_REMOVIDO``: almost everything stayed opaque;
        - ``CHECAR_RESIDUO``: a second large detached region remains.

        Other keys: ``WxH``, ``pct_fg``, ``pct_opaque``, ``pct_partial``,
        ``corners``, ``corners_ok``, ``n_components_big``, ``largest_frac``,
        ``second_over_largest``.
    """
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
def checker_bg(H: int, W: int, sq: int = 16, light: int = 235, dark: int = 170) -> np.ndarray:
    """Build a neutral gray checkerboard background.

    The mid-gray tones reveal both light and dark halos around the cutout and do
    not visually clash with green or otherwise colorful subjects.

    Args:
        H: Output height in pixels.
        W: Output width in pixels.
        sq: Size in pixels of each checkerboard square.
        light: Gray value of the light squares.
        dark: Gray value of the dark squares.

    Returns:
        An ``(H, W, 3)`` float32 array holding the checkerboard pattern.
    """
    yy, xx = np.mgrid[0:H, 0:W]
    base = np.where(((yy // sq) + (xx // sq)) % 2 == 0, light, dark).astype(np.float32)
    return np.dstack([base, base, base])


def save_preview(rgba_path: str, out_path: str) -> str:
    """Composite a cutout over a checkerboard and save it for visual inspection.

    Args:
        rgba_path: Path to the RGBA cutout PNG.
        out_path: Path where the composited preview is written.

    Returns:
        ``out_path``, for convenience.
    """
    r = np.asarray(Image.open(rgba_path).convert('RGBA')).astype(np.float32)
    rgb, al = r[:, :, :3], r[:, :, 3:4] / 255.0
    H, W = al.shape[:2]
    comp = rgb * al + checker_bg(H, W) * (1 - al)
    Image.fromarray(comp.astype(np.uint8)).save(out_path)
    return out_path
