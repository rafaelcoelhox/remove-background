# Security Policy

## Supported versions

Security fixes are applied to the latest version only (the newest tagged release and the
`main` branch).

| Version | Supported |
|---|---|
| latest (`main` / newest tag) | ✅ |
| older | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately through one of:

- **GitHub** — use the repository's
  [Security advisories → "Report a vulnerability"](https://github.com/rafaelcoelhox/remove-background/security/advisories/new)
  (private to the maintainer).
- **Email** — `r-delorean@proton.me`.

Please include:

- a description of the issue and its impact;
- steps to reproduce (and a sample input, if relevant);
- the plugin version and your OS / Python version.

You can expect an acknowledgement within a few days. Once a fix is ready it will be released and
the advisory published, with credit to you unless you prefer to remain anonymous.

## Security model & considerations

Understanding what this plugin does helps you assess the risk:

- **Runs locally.** All processing happens on your machine via Python scripts invoked by Claude
  Code. **Images are never uploaded**, and there is **no telemetry or data collection.**
- **Executes code.** Like any Claude Code plugin, it runs scripts on your machine with your user
  privileges. Only install it from a source you trust, and review the code before use.
- **Third-party model downloads.** For photos, [`rembg`](https://github.com/danielgatis/rembg)
  downloads ML model files (e.g. `birefnet-general-lite`) to `~/.u2net/` on first use, fetched
  from `rembg`'s upstream sources. These are third-party artifacts not controlled by this project.
- **Dependencies.** The plugin relies on `pillow`, `numpy`, `scipy`, `rembg`, and `onnxruntime`.
  Keep them updated; vulnerabilities in those libraries are handled upstream.
- **File writes.** Output PNGs are written next to the input (or to the path you specify), and
  preview images go to your system temp directory (`/tmp/`). No other files are modified.

## Scope

**In scope:** issues in this plugin's own code (its scripts, manifest, or skill instructions)
that could harm a user who runs it.

**Out of scope:** vulnerabilities in upstream dependencies (report those to the respective
projects), and the inability to remove a watermark baked into image pixels — that is a
documented limitation, not a security issue.
