---
name: nature-figure-kit
description: Render, compose, adjust and verify Nature-size publication figures (89 mm / 183 mm RGB LZW TIFF with sRGB ICC, Arial Bold, fixed canvas) from raw IR, XRD, TPC, PL-image and in-situ PL data. Use when asked to make or fix manuscript figures, multi-panel composites, axis ticks/limits, or to audit figure TIFFs against the house spec.
---

# nature-figure-kit

## When to use
- Making or re-making any of the ten house figures (01_IR ... 10_in_situ_PL_normalized_mean_spectrum).
- Building a multi-panel figure from data panels and/or TIFF, PNG, PDF artwork.
- Changing an axis (visibility, major/minor ticks, step, min/max) without editing code.
- Checking that exported TIFFs meet the spec (size, dpi, LZW, sRGB ICC, fonts, strokes, pixels).

Do not use it for interactive dashboards, statistics, or data cleaning. The tool never changes the data: no smoothing, re-normalization, fitting or dropping of observations.

## Commands
```sh
pip install -r requirements.txt                       # plus Arial Bold installed for Matplotlib
python make_figures.py --data DATA --manifest MAN.json --out OUT [--double-column] [--only 01_IR,05_PL_image] [--no-config]
python figmenu.py --data DATA --manifest MAN.json [--config-dir DIR] [--script keys.txt --transcript t.txt]
python make_composite.py --data DATA --manifest MAN.json --out fig.tiff --panels 01_IR a.tiff b.png c.pdf [--double-column] [--cols N] [--artwork-scale fit|native] [--label-format '(a)'] [--label-pt 14]
python make_composite.py ... --layout auto [--span a=row] [--span b=2x1] [--empty-cells legend --legend-entry 'A=#2166AC:solid'] [--force]   # auto grid <= 247 mm
python make_composite.py ... --shared-legend [--legend-cell 2,2] [--span d=row]   # one legend from the panel lines, panel legends off
python run_composites.py --data DATA --manifest MAN.json --out OUT/composite   # example composites, 89 + 183 mm
python run_composites.py ... --out OUT/composite --layout-acceptance          # auto layout / span / legend acceptance cases
python text_fit.py --out OUT                          # text overlap / tick collision / clipping at final size
python verify_figures.py --out OUT                    # exit 0 = all checks pass
python text_fit_composite_labels.py --out OUT         # composite panel labels: fit, font, size
bash demo/run_demo.sh                                 # end-to-end self-test on bundled data
```
Exit codes for `make_figures.py`: 0 ok, 2 input hash mismatch (nothing rendered), 3 Arial Bold missing, 1 other. `make_composite.py`: 0 ok, 1 render checks failed, 2 usage/input error, 4 no auto layout fits (no TIFF). Details: `USAGE.md`.

## Figure spec (summary; full text in docs/FIGURE_STYLE_SPEC.md)
- **Canvas:** 89 mm wide by default (starts at 60 mm tall); `--double-column` gives 183 mm (starts at 105 mm). Height grows in 1 mm steps when a 12 pt vertical label would be longer than its data box. The canvas is a fixed, uncropped full bleed with 1-2 mm ink clearance, placed at final size without scaling.
- **Export:** RGB TIFF, LZW, ≥ 600 dpi, embedded sRGB ICC. TIFF is the only figure format.
- **Text:** Arial Bold for every glyph. Axis labels and colour-bar titles 12 pt; tick labels, scientific offsets, legends and annotations 10 pt; composite panel labels (a), (b) ... 14 pt; all at final placement size. Use true superscripts (cm^-1), halfwidth hyphens and parentheses. No titles.
- **Strokes:**

  | Element | Width |
  |---|---|
  | Data lines and legend samples | 1.5 pt (1.25 pt for 07 and 10) |
  | Spines and colour-bar outlines | 1.25 pt |
  | Ticks | 1.0 pt |

- **Spectra:** all four spines visible; no ticks or labels on the top/right.
- **Figure-specific:**
  - 01: about 2 % x padding, descending axis.
  - 03: decay window 0-10 µs, solid and dashed traces.
  - 04: blue #2166AC and dark orange #B35806 with distinct dashes.
  - 05: right-hand colour bar; whole device pixels per native pixel; upper origin; full field.
  - 06/08/09: every native cell is resolved at the measured wavelengths. 06 uses its full linear range; 08/09 use a shared 0-1 scale.
- **Composites:** labels (a), (b), (c) ... in Arial Bold 14 pt (configurable via figmenu `c`, `composite.json`, `--label-format`/`--label-pt`) outside each top-left corner at one offset; fit is solved by margins/gaps/height, never by shrinking text; aligned box edges, uniform gaps. Default grid: 1 column at 89 mm, 2 at 183 mm (12 pt labels need the width). Imported artwork is placed whole at one uniform scale; `--artwork-scale native` keeps it at scale 1.0 so baked-in type stays 12/10 pt (render artwork at the cell width). PDFs are rasterized at ≥ 600 dpi at placement size. A `<file>.evidence.json` sidecar lets the QA map the artwork's text boxes.
- **Composite layout:** `--layout auto` searches columns x rows and qualifies each candidate on measured overhangs, minimum box size, label fit, native pixels, artwork scale, legend cell and height <= 247 mm. It then renders the first passing grid and re-checks it with the full text fit. Auto keeps (a) 14 pt labels and 12/10 pt text; it never shrinks text. When nothing fits, it prints a `WARNING` with the reason and a suggestion (183 mm or two figures) and exits 4 with no TIFF; `--force` publishes a fallback that is marked in the JSON. `--span a=row` / `b=2x1` (input-order letters) packs spans in reading order. Empty cells stay blank or take one legend (`--empty-cells legend --legend-entry ...`, last empty cell or `--legend-cell R,C`). The same keys can be saved in `composite.json` (CLI flags win; `--span none` clears).

## Rules for agents
- Treat input data as read-only. The tool verifies SHA-256 against the manifest before and after rendering.
- Change styling in `paper.mplstyle` and `paper_style.py`, and the science in `plot_figures.py`. Never silently substitute fonts.
- Save per-figure overrides with `figmenu.py` or as JSON in the config directory; `make_figures.py` loads them automatically.
- After any change, run `text_fit.py` and `verify_figures.py` (or `demo/run_demo.sh`) and report the measured results, not assumed ones. Keep the spec type sizes; fix fit problems with margins, height or tick density.

## Labels, legends, time axes (Batch 6)
- Per-figure JSON keys (all optional; old configs stay valid): `labels.{xlabel,ylabel,cbar_label}.{name,unit}` (mathtext or `cm⁻¹`; `"unit": ""` = no unit), `axes.<x|y|colorbar>.tick_labels: false` (hide tick numbers and offset only), `legend.labels` (03/04, one per line), `heatmap.{interval_s,start_s}` (06/08/09: x = Time (s), or Time (min) above 300 s, first tick = start).
- figmenu: axis submenu `l` label name/unit, `h` hide tick numbers only; figure menu `g` legend text, `i` interval; composite menu `h` shared legend. `auto` restores a default; `s` save, `l` reload, `d` reset.
- `make_composite.py --shared-legend` (or `composite.json` `"shared_legend": true`): one legend from the panel line handles in an empty cell, panel legends suppressed; `--legend-entry 'Label=color[:style[:marker]]'` mismatches print `WARNING`s. Y labels align per column; colour-bar pad 6 pt, clearance measured by the text fit.
- A label longer than its span prints `WARNING: label too long: <figure> <axis> ...`; keep 12/10/14 pt and shorten the label or widen the panel.
