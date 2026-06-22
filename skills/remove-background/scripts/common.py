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


def luma(rgb: np.ndarray) -> np.ndarray:
    """Return the Rec. 601 luma of an RGB array as an ``(H, W)`` float array."""
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


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


# ---------- probe analysis (cross-check pixels against the visual read) ----------
def luminance_profile(rgb: np.ndarray, bands: int = 18
                      ) -> list[tuple[int, int, float, float, float]]:
    """Summarize the vertical luma distribution in horizontal bands.

    Gives a caller that can SEE the image the numbers to reconcile against the
    visual read: where sky, silhouette and ground actually sit in the pixels. A
    blind threshold misreads this — a tall dark subject raises ``pct_dark`` high
    up the frame, but the band *mean* only collapses at the true horizon; only a
    viewer who knows it is a tree (not the ground) can tell the two apart.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)``.
        bands: Number of horizontal bands to split the height into.

    Returns:
        One ``(y0, y1, mean_luma, pct_dark, pct_bright)`` tuple per band, top to
        bottom. ``pct_dark`` counts luma < 60, ``pct_bright`` counts luma > 110.
    """
    H = rgb.shape[0]
    lum = luma(rgb)
    rows = []
    for i in range(bands):
        y0, y1 = i * H // bands, (i + 1) * H // bands
        seg = lum[y0:y1]
        rows.append((y0, y1, float(seg.mean()),
                     float((seg < 60).mean()), float((seg > 110).mean())))
    return rows


def brightest_point(rgb: np.ndarray) -> tuple[int, int, float]:
    """Return ``(x, y, luma)`` of the brightest pixel (e.g. a sun or a specular)."""
    lum = luma(rgb)
    y, x = divmod(int(lum.argmax()), rgb.shape[1])
    return x, y, float(lum[y, x])


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


def _bg_fill(H: int, W: int, bg) -> np.ndarray:
    """Build an ``(H, W, 3)`` preview background.

    Args:
        H: Height in pixels.
        W: Width in pixels.
        bg: ``'checker'`` (neutral gray checkerboard), ``'black'``, ``'white'``,
            or an explicit ``(R, G, B)`` color.

    Returns:
        The background as an ``(H, W, 3)`` float32 array.
    """
    if bg == 'checker':
        return checker_bg(H, W)
    if bg == 'black':
        return np.zeros((H, W, 3), np.float32)
    if bg == 'white':
        return np.full((H, W, 3), 255.0, np.float32)
    return np.broadcast_to(np.asarray(bg, np.float32), (H, W, 3)).copy()


def save_preview(rgba_path: str, out_path: str, bg='checker') -> str:
    """Composite a cutout over a background and save it for visual inspection.

    The default gray checkerboard reveals both light and dark halos, but a light
    (e.g. white-cloud) halo can blend into the bright squares — re-preview over
    ``bg='black'`` to catch it (and ``'white'`` for a dark halo).

    Args:
        rgba_path: Path to the RGBA cutout PNG.
        out_path: Path where the composited preview is written.
        bg: Background to composite over — ``'checker'`` (default), ``'black'``,
            ``'white'``, or an ``(R, G, B)`` color.

    Returns:
        ``out_path``, for convenience.
    """
    r = np.asarray(Image.open(rgba_path).convert('RGBA')).astype(np.float32)
    rgb, al = r[:, :, :3], r[:, :, 3:4] / 255.0
    H, W = al.shape[:2]
    comp = rgb * al + _bg_fill(H, W, bg) * (1 - al)
    Image.fromarray(comp.astype(np.uint8)).save(out_path)
    return out_path


# ---------- channel-difference separability (probe for a color key) ----------
def channel_separability(rgb: np.ndarray, top_frac: float = 0.35) -> list[dict]:
    """Rank channel-difference discriminators by how cleanly they split a TOP band.

    MEASUREMENT ONLY: the viewer labels which region is background and picks the
    channel; nothing is auto-applied. When a single background color cannot key the
    cut (e.g. a blue sky with WHITE clouds sitting between the sky and green
    foliage), a channel *difference* that puts the two regions on opposite sides of
    a threshold often can — this surfaces which one.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)``.
        top_frac: Fraction of the height treated as the top (usually-sky) band.

    Returns:
        One dict per expression (``G-B``, ``B-R``, ``R-B``, ``G-R``, ``2G-R-B``)
        with ``expr``, ``top_mean``, ``rest_mean``, ``gap`` and ``overlap``, sorted
        by ASCENDING overlap (gap as tiebreak). ``overlap`` is the fraction of all
        pixels in the ambiguous zone where the two regions' ``[p10, p90]`` ranges
        intersect — low overlap = a clean split. A big ``gap`` with high
        ``overlap`` is a trap (e.g. ``2G-R-B`` when bright clouds cross over).
    """
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    exprs = {'G-B': G - B, 'B-R': B - R, 'R-B': R - B,
             'G-R': G - R, '2G-R-B': 2 * G - R - B}
    cut = max(1, int(top_frac * rgb.shape[0]))
    rows = []
    for name, v in exprs.items():
        top, rest = v[:cut].ravel(), v[cut:].ravel()
        tlo, thi = np.percentile(top, [10, 90])
        rlo, rhi = np.percentile(rest, [10, 90])
        lo, hi = max(tlo, rlo), min(thi, rhi)
        overlap = float(((v >= lo) & (v <= hi)).mean()) if hi > lo else 0.0
        rows.append({'expr': name, 'top_mean': float(top.mean()),
                     'rest_mean': float(rest.mean()),
                     'gap': float(abs(top.mean() - rest.mean())), 'overlap': overlap})
    rows.sort(key=lambda d: (d['overlap'], -d['gap']))
    return rows


# ---------- fringe decontamination / connectivity gating / geometry ----------
def local_bg_field(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Per-pixel color of the nearest fully-transparent pixel (the LOCAL background).

    Lets a fringe be decontaminated against the actual local background (e.g. a
    white cloud at the canopy edge) instead of one global key color, which is what
    a non-uniform background (blue sky + white clouds) requires.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)``.
        alpha: Alpha channel as an ``(H, W)`` array; ``alpha == 0`` marks background.

    Returns:
        An ``(H, W, 3)`` float32 array; each pixel holds the RGB of its nearest
        ``alpha == 0`` neighbor. Falls back to the global mean color when the cutout
        is all-opaque or all-transparent.
    """
    rgbf = np.asarray(rgb, np.float32)
    bgmask = (np.asarray(alpha) == 0)
    if not bgmask.any() or bgmask.all():
        return np.broadcast_to(rgbf.reshape(-1, 3).mean(0), rgbf.shape).copy()
    idx = ndimage.distance_transform_edt(~bgmask, return_distances=False,
                                         return_indices=True)
    return rgbf[tuple(idx)]


def decontaminate_fringe(rgb: np.ndarray, alpha: np.ndarray, bg,
                         mask: np.ndarray | None = None) -> np.ndarray:
    """Un-mix a background color out of partial-alpha fringe pixels.

    Inverts the over-compositing ``C = a*F + (1 - a)*bg`` to recover the foreground
    color ``F``, removing the colored halo a soft edge keeps from whatever was
    behind it. Works on the ORIGINAL pixels (no generation). Assumes each fringe
    pixel was composited over a near-constant local ``bg`` — true for sky/cloud,
    false for a busy textured background.

    Args:
        rgb: RGB image array of shape ``(H, W, 3)`` (coerced to float32).
        alpha: Alpha channel as an ``(H, W)`` array (0–255).
        bg: The contaminating color — either a single ``(3,)`` color (a uniform
            key) or a per-pixel ``(H, W, 3)`` field (see :func:`local_bg_field` for
            a non-uniform background).
        mask: Optional bool ``(H, W)`` selecting which pixels to correct; defaults
            to the partial-alpha fringe ``(0 < alpha < 255)``.

    Returns:
        A new ``(H, W, 3)`` float32 array with the fringe decontaminated.
    """
    out = np.asarray(rgb, np.float32).copy()
    al = np.asarray(alpha, np.float32)
    fr = mask if mask is not None else ((al > 0) & (al < 255))
    if not fr.any():
        return out
    af = (al[fr] / 255.0)[:, None]
    bgv = np.asarray(bg, np.float32)
    bgf = bgv[fr] if bgv.ndim == 3 else bgv[None, :]
    out[fr] = np.clip((out[fr] - (1.0 - af) * bgf) / np.clip(af, 1e-3, 1.0), 0, 255)
    return out


def gate_partial_to_core(alpha: np.ndarray, core_thresh: int = 250,
                         reach: int = 1) -> np.ndarray:
    """Zero partial-alpha pixels not within ``reach`` of the opaque core.

    Removes DETACHED weak/partial fragments (e.g. stray sky bits) that float free
    of the subject — the connectivity gate GPT used to clean its edge. It does NOT
    touch fringe attached to the core.

    WARNING: it will also erase legitimately detached soft parts (wispy hair,
    smoke, thin wires). Use only when the floating-partial count is high and the
    subject has no such parts; otherwise raise ``reach`` or skip it.

    Args:
        alpha: Alpha channel as an ``(H, W)`` array.
        core_thresh: Alpha at/above which a pixel counts as opaque core.
        reach: Ring distance (in px) from the core within which a partial pixel is
            kept.

    Returns:
        A copy of ``alpha`` with unanchored partial pixels set to 0 (unchanged if
        the core is empty).
    """
    al = np.asarray(alpha)
    core = al >= core_thresh
    if not core.any():
        return alpha
    near = ndimage.binary_dilation(core, iterations=max(1, int(reach)))
    out = al.copy()
    out[(al > 0) & (al < core_thresh) & ~near] = 0
    return out


def horizon_curve(H: int, W: int, spec) -> np.ndarray:
    """Build a per-column ground line from an AGENT-SUPPLIED spec (never auto-fit).

    The points/coefficients are read off the image by the viewer; this only
    interpolates and clamps them. There is no detection of vegetation or a horizon
    from the pixels — that would violate the skill's no-blind-detection contract.

    Args:
        H: Image height (for clamping).
        W: Image width (number of columns to produce).
        spec: Either a number / numeric string (a flat horizon Y) or control points
            ``"x0:y0,x1:y1,..."`` linearly interpolated (end-clamped) across width.

    Returns:
        An int array of length ``W``: the ground line Y for each column.
    """
    if isinstance(spec, (int, float)):
        return np.full(W, int(round(spec)), dtype=int)
    s = str(spec).strip()
    if ':' not in s:
        return np.full(W, int(round(float(s))), dtype=int)
    pts = sorted(tuple(float(v) for v in tok.split(':')) for tok in s.split(','))
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    hy = np.interp(np.arange(W), xs, ys)
    return np.clip(hy.round().astype(int), 0, H)


# ---------- fringe / halo diagnostics (measurement only) ----------
def assess_fringe(rgba: np.ndarray) -> dict:
    """Halo/fringe diagnostics for the REVIEW step (changes nothing).

    These are the two numbers that separate a clean anti-aliased edge from a
    colored halo — ``pct_partial`` alone cannot tell them apart.

    Args:
        rgba: RGBA image array of shape ``(H, W, 4)``.

    Returns:
        A dict with:

        - ``pct_partial_whitish``: percent of PARTIAL-alpha pixels that are bright
          and low-saturation (luma > 180 and channel spread < 25) — a leftover
          light/white halo;
        - ``pct_img_floating``: percent of the IMAGE that is partial-alpha not
          touching the opaque (``>= 250``) core — stray fragments;
        - ``n_partial``: count of partial-alpha pixels.
    """
    arr = np.asarray(rgba)
    rgb = arr[..., :3].astype(np.float32)
    al = arr[..., 3]
    partial = (al > 10) & (al < 250)
    n = int(partial.sum())
    whit = 0.0
    if n:
        fp = rgb[partial]
        lum = 0.299 * fp[:, 0] + 0.587 * fp[:, 1] + 0.114 * fp[:, 2]
        spread = fp.max(1) - fp.min(1)
        whit = 100.0 * float(((lum > 180) & (spread < 25)).mean())
    floating = partial & ~ndimage.binary_dilation(al >= 250, iterations=1)
    return {'pct_partial_whitish': round(whit, 1),
            'pct_img_floating': round(100.0 * float(floating.mean()), 3),
            'n_partial': n}
