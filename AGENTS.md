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

## Selectable palettes

Name a palette and the series colours of the line figures switch to it: per-figure config `"palette": "nature-6c-2"`, CLI `--palette NAME` (`make_figures.py`, `figmenu.py`), or figure-menu key `P`. If no palette is named, the bundled figures keep their spec colours. Overflow (more series than colours) cycles the colours, advances the linestyle (solid -> dashed -> dotted -> dashdot) and prints a `WARNING` that is also recorded in the style JSON. Heatmaps and colour bars keep their colormaps. Full hex table: `USAGE.md`; preview: `docs/nature_palettes_preview.png`; test: `python demo/test_palettes.py`.

Source of the 36 `nature-*` palettes: [论文配色：跟着顶刊学配色（Nature篇）](https://www.163.com/dy/article/J70K7HOA0511CJ6T.html), hex transcribed from printed labels (36 palettes, 270 hex values, order kept). `okabe-ito` is colour-blind friendly. All 37 ids (n = number of colours):

- n=8: `okabe-ito`
- n=3: `nature-3c-1`, `nature-3c-2`, `nature-3c-3`, `nature-3c-4`
- n=4: `nature-4c-1`, `nature-4c-2`, `nature-4c-3`, `nature-4c-4`, `nature-4c-5`, `nature-4c-6`, `nature-4c-7`, `nature-4c-8`, `nature-4c-9`
- n=5: `nature-5c-1`, `nature-5c-2`, `nature-5c-3`
- n=6: `nature-6c-1`, `nature-6c-2`, `nature-6c-3`, `nature-6c-4`, `nature-6c-5`, `nature-6c-6`, `nature-6c-7`, `nature-6c-8`, `nature-6c-9`
- n=10: `nature-10c-1`, `nature-10c-2`, `nature-10c-3`, `nature-10c-4`, `nature-10c-5`
- n=12: `nature-12c-1`, `nature-12c-2`
- n=15: `nature-15c-1`
- n=20: `nature-20c-1`, `nature-20c-2`
- n=24: `nature-24c-1`
