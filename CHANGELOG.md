# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`chroma` cutout method** (`remove_bg_chroma.py`) for PARTIAL backgrounds —
  remove a colored background (blue sky, green screen) while keeping BOTH a subject
  and a co-equal region (the ground it stands on), the case none of `solid`/`photo`/
  `scene` handles. Keys on an agent-chosen channel DIFFERENCE (`--channel G-B`…)
  with a soft ramp, an agent-drawn `--keep-below` ground line (flat or curved control
  points) for the structural prior, LOCAL fringe decontamination (`--decontam local`),
  and connectivity gating (`--gate`/`--gate-reach`).
- **Channel-separability probe in `analyze.py`**: ranks `G-B`/`B-R`/`R-B`/`G-R`/
  `2G-R-B` by how cleanly each splits a top band from the rest (sorted by OVERLAP,
  not gap, so a wide-but-noisy split like `2G-R-B` over clouds is not mistaken for a
  clean one). New `common.channel_separability`.
- **Halo-aware review**: `validate.py` always also writes a BLACK preview (a white
  halo hides on the gray checker) and reports `%partial whitish` / `%img floating`
  via new `common.assess_fringe`; advisory `CHECAR_HALO` flag; `--bg` and
  `--keep-ground` knobs (the latter stops a deliberately-kept ground from tripping
  `CHECAR_CANTOS`). `common.save_preview` gains a `bg` argument.
- **Shared helpers in `common.py`**: `decontaminate_fringe` (fringe un-mixing,
  extracted from `remove_bg_solid.py` so every keep-path can reuse it), `local_bg_field`
  (per-pixel nearest-background color for non-uniform backgrounds), `gate_partial_to_core`
  (connectivity gating), and `horizon_curve` (agent-supplied flat/curved ground line).

### Changed
- `remove_bg_solid.py` now calls `common.decontaminate_fringe` (behavior unchanged).

## [1.1.0] - 2026-06-22

### Added
- **`scene` cutout method** (`remove_bg_scene.py`) for back-lit landscapes and
  silhouettes against a bright sky — sunsets, trees, poles and wires — where
  segmentation finds no salient subject and returns an empty mask. Keeps the dark
  foreground and erases the bright sky via a luma/color split, a `--horizon` line
  below which everything stays solid, and a soft radial `--sun` guard that
  preserves a light source's glow instead of eating it as "bright".
- **`analyze.py` is now a full probe**: vertical luminance profile, brightest
  point, region color samples, and global contrast — the pixel-side numbers to
  cross-check against the visual read before choosing and calibrating a method.
  New `common.luminance_profile` / `common.brightest_point` helpers.
- **Calibration knobs on every method**: `remove_bg_solid.py` gains `--hi`/`--lo`/
  `--bg-color`; `remove_bg_photo.py` gains `--fg-threshold`/`--bg-threshold`/
  `--erode`; `remove_bg_scene.py` takes `--horizon`/`--sun`/`--sky-lo`/`--sky-hi`/
  `--bluish`.

### Changed
- **The guided loop is the default path** (see `SKILL.md`): look → probe →
  reconcile → cut & calibrate → review → iterate. The agent reads the scene and
  the pixels and drives the calibration; `run.py` is documented as a one-shot
  shortcut for easy images. An empty mask is reported, not guessed around — no
  blind scene auto-detection; the agent supplies the geometry it reads off the
  image.

## [1.0.0] - 2026-06-22

### Added
- Initial release as a Claude Code plugin.
- `remove-background` skill: auto-selects edge-based flood fill (uniform/solid
  backgrounds) or AI segmentation via `rembg` (complex photos).
- Single entry point `run.py` with automatic model fallback, detached-island
  removal, and quality validation (`OK` / `CHECAR_CANTOS` / `CHECAR_RESIDUO` /
  `OBJETO_QUASE_VAZIO` / `FUNDO_NAO_REMOVIDO`).
- Checkerboard preview for visual inspection of the cutout.
- Portable script paths via `${CLAUDE_SKILL_DIR}` (works on any install location).
