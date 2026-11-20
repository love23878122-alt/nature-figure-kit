# Claude Code instructions

Follow `AGENTS.md`. They apply unchanged. Use `SKILL.md` as the skill description and quick reference.

- Prefer the existing CLIs (`make_figures.py`, `make_composite.py`, `figmenu.py`, `text_fit.py`, `text_fit_composite_labels.py`, `verify_figures.py`) over ad-hoc plotting code.
- For non-interactive menu work, use `figmenu.py --script FILE` or piped stdin. Both echo a transcript.
- Finish every task by running `bash demo/run_demo.sh` or `python text_fit.py --out OUT && python verify_figures.py --out OUT`, and quote the PASS/FAIL lines.
