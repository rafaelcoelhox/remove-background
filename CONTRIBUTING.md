# Contributing to remove-background

Thanks for your interest in improving this plugin! This guide covers how to report issues,
set up a development environment, and submit changes.

## Ways to contribute

- **Report a bug** — open a [GitHub issue](https://github.com/rafaelcoelhox/remove-background/issues)
  with the input image (or a description), the prompt/command you used, the `STATUS` output,
  and what you expected to happen.
- **Request a feature** — open an issue describing the use case.
- **Submit a fix or improvement** — see [Submitting a pull request](#submitting-a-pull-request).

## Development setup

1. Fork and clone:
   ```bash
   git clone https://github.com/<your-user>/remove-background.git
   cd remove-background
   ```
2. (Recommended) create a virtual environment, then install the dependencies:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip3 install -r requirements.txt
   ```

## Project layout

```
.claude-plugin/
  plugin.json          # plugin manifest
  marketplace.json     # self-hosted marketplace entry
skills/remove-background/
  SKILL.md             # instructions Claude loads when the skill runs
  scripts/             # the Python implementation
    run.py               # single entry point (orchestrator)
    common.py            # shared helpers
    analyze.py           # background diagnostics
    remove_bg_solid.py   # uniform / solid-color background
    remove_bg_photo.py   # rembg segmentation
    validate.py          # preview + quality flags
```

## Testing your changes

There is no unit-test suite; validation is manual plus the plugin validator.

1. **Run the scripts** on a few representative images (a solid-background icon, a portrait, a
   complex photo):
   ```bash
   cd skills/remove-background/scripts
   python3 run.py sample.png
   ```
   Open the printed preview and check: complete subject, transparent corners, no halo/residue.

2. **Validate the plugin manifest:**
   ```bash
   claude plugin validate . --strict
   ```

3. **Test it live in Claude Code** by loading your working copy:
   ```bash
   claude --plugin-dir .
   ```
   Then try a natural-language prompt or `/remove-background:remove-background`.

## Coding guidelines

- **Keep paths portable.** In `SKILL.md`, reference scripts via `${CLAUDE_SKILL_DIR}/scripts/...`;
  in Python, resolve sibling scripts from `__file__`. Never hardcode an absolute path.
- **Work on the original pixels.** This plugin must never generate, inpaint, or redraw image
  content — it only computes an alpha channel.
- **No new heavy dependencies** without a good reason. The current stack is `pillow`, `numpy`,
  `scipy`, `rembg`, and `onnxruntime`.
- **Match the existing style** — small, focused functions, and keep `run.py` output minimal
  (the three lines: output path / `PREVIEW` / `STATUS`).
- Keep the existing `STATUS` flags and their meanings consistent.

## Submitting a pull request

1. Create a branch: `git checkout -b fix/short-description`.
2. Make your change and test it (see above).
3. If you change public behavior, update `README.md` and add an entry to `CHANGELOG.md`.
4. Bump the `version` in `.claude-plugin/plugin.json` following [SemVer](https://semver.org):
   patch = fix, minor = new feature, major = breaking change.
5. Open the PR with a clear description. Before/after preview images are very welcome.

## Release & distribution note

This repository doubles as its own marketplace and is mirrored into the Claude community
catalog. The community catalog pins a specific commit SHA and updates automatically as new
commits land on `main`, so please keep `main` in a releasable state.

## Code of conduct

Be respectful and constructive. Assume good intent, keep discussions on topic, and help keep
this a welcoming project for everyone.
