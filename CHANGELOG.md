# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
