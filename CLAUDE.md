# Claude Code instructions

Follow `AGENTS.md`. They apply unchanged. Use `SKILL.md` as the skill description and quick reference.

- Prefer the existing CLIs (`make_figures.py`, `make_composite.py`, `figmenu.py`, `text_fit.py`, `text_fit_composite_labels.py`, `verify_figures.py`) over ad-hoc plotting code.
- For non-interactive menu work, use `figmenu.py --script FILE` or piped stdin. Both echo a transcript.
- Finish every task by running `bash demo/run_demo.sh` or `python text_fit.py --out OUT && python verify_figures.py --out OUT`, and quote the PASS/FAIL lines.

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
