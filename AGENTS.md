# Agent instructions (Codex and other coding agents)

Read `SKILL.md` first. It covers when to use the kit, the commands, and the figure spec. The full spec is in `docs/FIGURE_STYLE_SPEC.md`.

- Setup: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`. Arial Bold must be installed.
- Self-test after any change: `bash demo/run_demo.sh` must end with `DEMO OK` (exit 0).
- Input data directories are read-only. Do not edit, move or delete raw files. Write outputs to a separate `--out` directory.
- Keep the layers separate:
  - `plot_figures.py` holds the science: data reading, transforms, provenance.
  - `paper_style.py` and `paper.mplstyle` hold the style: layout and export.
  - `figure_config.py` holds the user axis overrides.
- Do not add plot titles. Do not crop the canvas (`bbox_inches="tight"` is forbidden). Do not downsample images or heatmaps. Export TIFF only.
- Type sizes are fixed by the spec (12 pt labels, 10 pt ticks/legends/annotations, 14 pt composite panel labels (a), (b) ... at final size). If text collides or clips, adjust margins, canvas height or tick density, never the font size. Check with `python text_fit.py --out OUT` and `python text_fit_composite_labels.py --out OUT`.
- Report measured evidence from `verify_figures.py`, `text_fit.py` and the `qa/*.json` files. Mark anything you could not verify as unverified.
- Never commit secrets, generated outputs (`demo_out/`, `out*/`) or local `figure_configs/`.
