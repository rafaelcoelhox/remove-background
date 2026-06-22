# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
