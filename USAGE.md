# nature-figure-kit - usage

Style rules: [`docs/FIGURE_STYLE_SPEC.md`](docs/FIGURE_STYLE_SPEC.md). Overview and installation: [`README.md`](README.md). Agent quick reference: [`SKILL.md`](SKILL.md).

All paths below are relative to the kit folder. `DATA` is a directory with the six inputs and `MAN.json` its SHA-256 manifest (`demo/data` and `demo/data_manifest.json` for the bundled synthetic data).

## Commands

```sh
python make_figures.py   --data DATA --manifest MAN.json --out OUT [--double-column] [--only NAMES] [--no-config]
python make_composite.py --data DATA --manifest MAN.json --out FIG.tiff --panels P1 P2 ... [options below]
python figmenu.py        --data DATA --manifest MAN.json [--config-dir DIR] [--script keys.txt --transcript t.txt]
python run_composites.py --data DATA --manifest MAN.json --out OUT/composite [--layout-acceptance]
python text_fit.py --out OUT ; python text_fit_composite_labels.py --out OUT ; python verify_figures.py --out OUT
bash demo/run_demo.sh                                  # end-to-end self-test, must end with DEMO OK
```

## Composite layout

```sh
python make_composite.py --data DATA --manifest MAN.json --out FIG.tiff --panels 01_IR 03_TPC_overlay a.tiff \
    [--double-column] [--layout manual|auto] [--cols N] [--span a=row] [--span b=2x1] \
    [--empty-cells blank|legend] [--legend-entry 'Label=color[:style]'] [--legend-cell auto|ROW,COL] \
    [--force] [--max-height-mm 247] [--min-box-mm 20] [--max-dpi 2400] \
    [--label-format '(a)'] [--label-pt 14] [--config-dir DIR | --no-config]
```

### Layout modes

- **`--layout manual`** (default): `--cols` columns (default 1 at 89 mm, 2 at 183 mm), rows as needed. This is the unchanged earlier behaviour; custom label format and size are honoured.
- **`--layout auto`**: the tool searches columns x rows deterministically: 1, 2, 3 ... columns, with the rows following from the panel count and the spans. Every candidate is qualified before rendering with:
  - the renderer's measured ink overhangs (probe render of every data panel);
  - a minimum box width (`--min-box-mm`, 20 mm);
  - the x-axis label fitting its cell, and the PL image labels fitting its square box;
  - spanning data boxes keeping height/width >= 0.25;
  - the density needed for native pixels and heatmap cells (<= `--max-dpi`);
  - imported artwork at >= 600 dpi effective, with baked-in text never shrunk below 10 pt (from its evidence sidecar);
  - a free cell for the legend (if requested) that is large enough;
  - the full height, including labels, margins, gaps and spans, <= `--max-height-mm` (247 mm).

  The first passing candidate (fewest columns, so the largest panels) is rendered at final size and checked again: render checks, final height, and the full composite text fit (`text_fit.py` `composite_fit`). If that fails, the next candidate is tried. `FIG.json` records `grid` and `auto_layout` (every candidate's criteria and reason, `selected_grid`, `selection_reason`, `forced`, `failed_criteria`).
- **`--cols` with auto** restricts the search to exactly that column count; rows still follow from the panels and spans. Use it to request a geometry, for example `--cols 2 --span a=row` = a full-width first row plus a 2-column body.
- **Labels in auto** are fixed at (a), (b) ... 14 pt Arial Bold; axis and colour-bar labels stay 12 pt and ticks/legends 10 pt. Text is never shrunk to make a candidate fit. Conflicting label settings:
  - a differing **saved** label setting (`composite.json`) is ignored, and `label.settings_source` in the JSON says so;
  - a differing **explicit** `--label-format` / `--label-pt` is an error (exit 2): use `--layout manual` for custom labels.

### No fit and `--force`

When no auto candidate fits, the tool prints `WARNING: no auto layout fits ...` with the limiting reason of each candidate and a suggestion. At 89 mm it suggests `--double-column` or splitting into two figures; at 183 mm it suggests splitting. It writes `FIG.nofit.json` with the requested geometry and the candidates, publishes **no TIFF**, and exits **4**.

With `--force` it renders a fallback instead: the lowest candidate that fails only the height limit, otherwise the one with the fewest failed criteria (then the lowest height). The output is published with `auto_layout.forced = true` and `auto_layout.failed_criteria` in `FIG.json`, and the run exits 0 when its render checks pass. Text sizes are unchanged. Input errors (unknown panel, malformed span, hash mismatch, legend problems) and render errors still stop the run with a non-zero exit status, with or without `--force`.

Exit status: 0 ok · 1 render checks failed · 2 usage/input error (`ERROR: ...` on stderr) · 4 no auto layout fits.

### Spans

`--span ID=row` (full grid width, one row) or `--span ID=COLSxROWS` (for example `2x1` = two columns by one row, `1x2` = one column by two rows). The option is repeatable and works in both layout modes.

- **ID** is the lowercase letter of the panel's input position (a = first `--panels` item), whatever the label format; with `(A)` labels the first panel is still `a`.
- **Packing:** panels are placed in reading order. Each starts at the first free cell at or after the previous panel's start, so the order is kept, rectangles never overlap, and skipped cells become empty cells.
- **Geometry:** a spanning box runs from the first spanned column's box edge to the last one's (rows likewise), so edges stay aligned. A one-row span keeps the row height of an ordinary panel; a multi-row span covers its rows (the last row grows if the box needs more).
- **Limits:** `05_PL_image` keeps its exact square box and cannot span.
- **Errors (exit 2):** malformed values (`a=3`), duplicate IDs, IDs without a panel, a span wider than the manual grid, and a 05 span. In auto, a span wider than a candidate grid simply disqualifies that candidate.
- **Clearing:** `--span none` clears spans saved in `composite.json`.

`FIG.json` records `spans`, `positions` (row, col, col_span, row_span and cell for every panel) and `empty_cells` (`use`, `cells_rc`, `legend_cell_rc`, `blank_cells_rc`; 0-based, plus `cells_rc_1based`).

### Empty cells and the shared legend

- `--empty-cells blank` (default) leaves unused cells white.
- `--empty-cells legend` puts one shared legend in an empty cell. The legend is **supplied** as repeatable `--legend-entry 'Label=color[:style]'` items (any Matplotlib colour; style `solid`, `dashed`, `dotted` or `dashdot`). It is drawn with 1.5 pt line samples and 10 pt Arial Bold text, without a frame.
- **Target cell:** `--legend-cell auto` (default) selects the **last empty cell in reading order**; `--legend-cell ROW,COL` (1-based) names one, and it must be empty. The legend sits at the cell's box-aligned top-left corner, or at the cell corner if it would not fit there.
- **Errors:** legend without entries, no free cell, an occupied requested cell, or a legend larger than its cell. These are exit 2 in manual mode and a failed criterion for that candidate in auto.
- **QA:** the legend's renderer text boxes are stored in `FIG.json` (`legend.texts`). `text_fit.py` and `text_fit_composite_labels.py` include them in the overlap checks, require them inside the legend cell, and check them at 10 pt Arial Bold.

### Settings precedence and saved config

The precedence is the same for every key: explicit CLI flag > saved `<config-dir>/composite.json` > default. `--no-config` ignores the saved file (and the saved axis overrides). Spans are a single key: any `--span` replaces the saved spans, and `--span none` means "no spans".

The equivalent CLI and JSON forms:

```sh
python make_composite.py ... --layout auto --span a=row --span c=1x2 \
    --empty-cells legend --legend-cell auto \
    --legend-entry 'Sample 1=#2166AC:solid' --legend-entry 'Sample 2=#B35806:dashed'
```

```json
{"composite": {"layout": "auto", "spans": {"a": "row", "c": "1x2"},
               "empty_cells": "legend", "legend_cell": "auto",
               "legend_entries": ["Sample 1=#2166AC:solid", "Sample 2=#B35806:dashed"]}}
```

A label-only file such as `{"composite": {"label_format": "(a)", "label_pt": 14.0}}` stays valid. Every key is optional.

- **Reset spans:** delete the `spans` key (or set `{}`), pass `--span none` for one run, or use the menu's `g` -> `none` and then `s`.
- **Reset everything:** delete `composite.json`, use `--no-config`, or use the menu's `d` (reset, unsaved) and then `s`.

### Menu (`figmenu.py`, main level `c`)

| Key | Action |
|---|---|
| `f` / `z` | label format / size (`auto` = default) |
| `a` | layout `manual` / `auto` (`default` = manual) |
| `g` | span: `a=row`, `b=2x1` add/replace · `a=` removes · `none` clears all |
| `e` | empty cells `blank` / `legend` |
| `k` | legend cell `auto` or `ROW,COL` |
| `o` | legend entries `Label=color[:style]; Label2=...` or `none` |
| `r` | render preview of `--composite-panels` (with `--double-column` for 183 mm): TIFF + JSON + `.preview.png`; the grid, positions, empty cells and auto selection reason are printed |
| `s` / `l` / `d` / `p` / `b` | save / reload / reset to defaults (unsaved) / print / back |

- **Validation:** invalid values are rejected with the validation message, and the previous settings are kept. This includes span IDs without a preview panel, malformed spans, and a legend without entries.
- **Render:** `r` passes every displayed value explicitly (`--layout`, labels, `--span ...` or `--span none`, `--empty-cells`, `--legend-cell`, `--legend-entry`). An unsaved reset therefore renders the displayed defaults even when an older `composite.json` is on disk.
- **Failures:** a failed render (no fit, occupied legend cell) is reported in the transcript, and the menu stays open.

Scripted example: `demo/menu_layout.keys`.

## Labels, legend text, heatmap time axis and shared legends (Batch 6)

All of these are per-figure keys in the existing `<config-dir>/<figure>.json` (written by
`figmenu.py`, read automatically by `make_figures.py`, `make_composite.py` and
`run_composites.py --config-dir`). Every key is optional. Older configs that only hold
`"axes"` still load unchanged and render the defaults below. `--no-config` ignores them.

```json
{"figure": "02_XRD",
 "axes": {"y": {"tick_labels": false}},
 "labels": {"ylabel": {"name": "Intensity", "unit": "a.u."}}}
{"figure": "04_TPC_overlay_logtime",
 "axes": {"x": {"max": 100}},
 "legend": {"labels": ["Control", "Target"]}}
{"figure": "06_in_situ_PL_heatmap",
 "heatmap": {"interval_s": 1.0, "start_s": 0.0},
 "labels": {"cbar_label": {"name": "PL intensity", "unit": "cts s$^{\\text{-1}}$"}}}
```

### Axis and colour-bar labels (`labels`: `xlabel`, `ylabel`, `cbar_label`)
- The label is rendered as `name (unit)`, or `name` when the unit is empty. Each part
  falls back to the default when it is not set. `"unit": ""` removes the unit.
- Defaults (in `figure_config.DEFAULT_LABELS`; the plotting code no longer hard-codes labels):

  | Figure | xlabel | ylabel | cbar_label |
  |---|---|---|---|
  | 01 | Wavenumber (cm$^{\text{-1}}$) | Transmittance (%) | - |
  | 02 | 2θ (°) | Intensity (a.u.) | - |
  | 03, 04 | Time (µs) | Normalized current | - |
  | 05 | Column index (pixel) | Row index (pixel) | Intensity (source units) |
  | 06 | Acquisition number (Time (s/min) with an interval) | Wavelength (nm) | PL intensity (counts) |
  | 07 | Wavelength (nm) | Mean PL intensity (counts) | - |
  | 08, 09 | as 06 | Wavelength (nm) | Normalized PL intensity |
  | 10 | Wavelength (nm) | Normalized mean PL intensity | - |

- Mathtext is accepted: `cm$^{-1}$`, `2$\theta$`, `x$_{2}$`. Unicode superscripts and
  subscripts are converted to true scripts: `cm⁻¹` (U+207B U+00B9) becomes `cm$^{-1}$`.
  The minus inside math (`-`, U+207B, U+2212) is set as the spec halfwidth hyphen
  (`\text{-1}`). Unbalanced `$` or invalid mathtext is rejected with a message.
  The limit is 80 characters per part.
- Fit: each final label is measured against its span (x label: data-box width; y label:
  data-box height; colour-bar label: bar length). If the label is longer, the tool
  prints `WARNING: label too long: <figure> <axis> label '<text>' is A mm, longer than its
  B mm available span` (also in the composite JSON `label_warnings` and in the menu).
  The font size is never reduced. The evidence is in `qa/<figure>.style.json` →
  `layout.label_fit`.

### Hide tick numbers only (`axes.<x|y|colorbar>.tick_labels: false`)
The tick numbers are hidden, and so is the numeric offset (`x10^n`, `+c`) when there is
one. The tick marks and the axis label stay. Evidence: `layout.tick_numbers_hidden`
(`offset_visible: false`, `tick_marks_visible`, `label_visible`).

### Legend text (`legend.labels`, figures 03 and 04)
There is one label per plotted line (default `TPC 1 (D1-1)`, `TPC 2 (D2-1)`). The text is
set on the plotted lines, so the standalone legend and the composite line handles use the
same names. `null` or `"auto"` for one line keeps its default.

### Heatmap acquisition interval (`heatmap.interval_s`, `heatmap.start_s`; 06, 08, 09)
- Without an interval, x is the acquisition number (default).
- With an interval, x becomes the elapsed time `start_s + (k - 1) * interval_s`. It is
  labelled `Time (s)`, or `Time (min)` when the span exceeds 300 s. The first major
  tick always shows the starting value (0 or `start_s`).
- The native-cell density check (≥ 1.1 device px per cell) uses the plotted coordinate.
  The coordinate is stored in `source_data/in_situ_PL.npz` (key such as
  `x_06_elapsed_s`), and the raster verification reads it through the record's `raster.x_key`.

### Shared composite legend (`composite.json` `shared_legend`, `--shared-legend`)
```json
{"composite": {"shared_legend": true, "spans": {"d": "row"}, "legend_cell": "2,2"}}
```
- `true` places one legend for the whole figure in an empty cell (chosen with
  `legend_cell`, `auto` = last empty cell). It also suppresses every per-panel legend.
  `empty_cells` is then `legend` automatically. `--no-shared-legend` overrides a saved `true`.
- Entries default to the panel line handles: label, colour, marker, linestyle and width,
  in reading order, with duplicates merged. They follow the legend-text overrides.
- Supplied `legend_entries` (`'Label=color[:style[:marker]]'`, marker `none o s ^ v D x + * .`)
  replace them. Each count or style (colour, linestyle, marker) mismatch against the
  handles prints `WARNING: shared legend ...` and is recorded in the composite JSON
  (`legend.mismatch_warnings`).
- The legend size is part of the layout measurement (cell fit, auto criteria), and its
  10 pt texts are part of the text-fit evidence.
- Example with no blank cell: 4 panels at 183 mm, `--cols 2`, `d=row`, legend at `2,2`.
  The heatmap keeps its normal box (aspect ≈ 0.68).

### Composite y-label alignment and colour-bar pad
- The y labels of data panels that start in the same column share one left edge, the
  leftmost natural position. Each panel is rendered separately, so the target is fed back
  into the panel render. It is measured on the composed sheet:
  `alignment.ylabel_alignment_per_column` and check `ylabels_aligned_per_column` (spread ≤ 1 px).
- The colour-bar pad was increased in `paper_style.py`: `COLORBAR_GAP_PT` 5 → 6 pt (box to
  bar) and `COLORBAR_LABELPAD_PT` 3 → 4 pt (ticks to label). The overhang measurement
  includes them. The text-fit composite record `colorbar_label_clearance` gives the
  clearance in mm from each colour-bar label to the axis label (and nearest text) of the
  panel to its right. A collision fails the text fit.

### Menu keys (`figmenu.py`)
Axis submenus (x, y, colour bar):

| Key | Action |
|---|---|
| `l` | Edit the label: name, then unit. Each prompt takes text, `auto` (default) or a blank line in interactive use (keep). The unit also takes `none` (no unit). |
| `h` | `hide tick numbers only` (toggle). |

Figure menu:

| Key | Action |
|---|---|
| `g` | Legend text (03/04): `Control; Target`, or `auto`. |
| `i` | Acquisition interval in s (06/08/09): `1`, `5 start=10`, or `auto` (acquisition number). |

Composite menu (main level `c`):

| Key | Action |
|---|---|
| `h` | Shared legend `on` / `off` / `default`. |
| `o` | Legend entries; `none` = use the panel handles. |

`s` saves, `l` reloads the saved file and `d` resets to the defaults without saving.
`auto` in any prompt restores the default for that value. The scripted example is
`demo/menu_b6.keys`, and `bash demo/run_demo.sh` step 11 checks it.

## Batch 5 acceptance

`python run_composites.py --data DATA --manifest MAN.json --out OUT/composite --layout-acceptance [--qa-dir Q] [--preview-dir P]` runs `make_composite.py` through its CLI. It covers auto layouts for 4, 6, 7 (requested `--cols 2 --span a=row`) and 8 panels at 89 and 183 mm, `--force`, a multi-row span, legends in auto and manual layouts, and the invalid-input cases.

It writes `layout_acceptance.json` and `layout_acceptance.md`: one row per case, with case, width, n, grid, spans, height_mm, fits, warning, text_fit pass, exit status and an evidence link. It also writes PNG previews and per-case logs. Exit status is 0 only when every case behaves as expected:

- published outputs pass the TIFF-tag checks and the label/text-fit checks;
- no-fit cases warn, exit 4 and publish no TIFF;
- invalid input exits 2.

## Selectable palettes

- Config JSON (per figure, saved by `figmenu.py` or written by hand): `{"figure": "04_TPC_overlay_logtime", "axes": {}, "palette": "nature-6c-2"}`. The name is validated; an unknown id is rejected with a short list of valid ids.
- CLI: `python make_figures.py ... --palette nature-6c-2` or `python figmenu.py ... --palette nature-6c-2`. This is the session choice for every line figure whose config has no `palette` key.
- Menu: in a line-figure menu (01, 02, 03, 04, 07, 10) press `P`, then type an id (`list` prints every id with its hex, `none` clears the figure's palette). The chosen id and its hex list are printed; `s` saves it.
- Naming a palette switches the series colours directly. Single-series figures take the first colour; 03/04 take the first two and keep their solid/dashed pair. Heatmaps, the PL image and colour bars stay on their colormaps (`viridis`).
- If no palette is named, the bundled figures keep their spec colours (#2166AC, and #2166AC / #B35806 solid/dashed for 03/04).
- Overflow: with more series than the palette holds, the colours cycle and the linestyle advances once per cycle (solid -> dashed -> dotted -> dashdot, then repeat). A `WARNING: palette ... has N colours but M series were requested ...` goes to stderr and into the evidence / `qa/<figure>.style.json` (`palette.warning`). Nothing crashes.
- Evidence: a figure rendered with a palette records `palette`, `palette_hex_used` and `line_handles` in `qa/<figure>.style.json` and the full assignment under `evidence.palette`.
- Python: `import palettes; palettes.list_palettes(); palettes.get_palette("nature-6c-2"); palettes.assign_series(8, "nature-6c-2")`. `python palettes.py` prints the catalog; data in `palettes/nature_palettes.json`.
- Preview of all 36 Nature palettes: [`docs/nature_palettes_preview.png`](docs/nature_palettes_preview.png) (copied unchanged from the verified transcription preview of the source article; binary PNG). The PNG is kept in the local kit but is not stored in the GitHub repository, because the text-only upload cannot carry binaries; the hex table below and `python palettes.py` list every palette.
- Self-test (synthetic data only): `python demo/test_palettes.py --out demo_out/palette_test` (also step 12 of `bash demo/run_demo.sh`).

Source of the 36 `nature-*` palettes: [论文配色：跟着顶刊学配色（Nature篇）](https://www.163.com/dy/article/J70K7HOA0511CJ6T.html), hex transcribed from printed labels (36 palettes, 270 hex values, order kept). `okabe-ito` (colour-blind friendly) is shipped as a separately named palette.

All 37 ids:

| id | n | hex (series order) |
|---|---:|---|
| `okabe-ito` | 8 | #0072B2 #D55E00 #009E73 #CC79A7 #56B4E9 #E69F00 #F0E442 #000000 |
| `nature-3c-1` | 3 | #BF1D2D #262626 #293890 |
| `nature-3c-2` | 3 | #F1B656 #397FC7 #040676 |
| `nature-3c-3` | 3 | #6F6F6F #F6631C #6D65A3 |
| `nature-3c-4` | 3 | #FF9A9B #9998FF #C99BFF |
| `nature-4c-1` | 4 | #DE582B #1868B2 #018A67 #F3A332 |
| `nature-4c-2` | 4 | #069DFF #808080 #A4E048 #010101 |
| `nature-4c-3` | 4 | #BABABA #0001A1 #037F77 #C5272D |
| `nature-4c-4` | 4 | #32037D #7C1A97 #C94E65 #D9995B |
| `nature-4c-5` | 4 | #015493 #019092 #999999 #F4A99B |
| `nature-4c-6` | 4 | #909090 #0095FF #019092 #6FDCB5 |
| `nature-4c-7` | 4 | #2F2D54 #9193B4 #BD9AAD #E8D2B3 |
| `nature-4c-8` | 4 | #D6D6D6 #9CB0C3 #7C9D97 #EAB080 |
| `nature-4c-9` | 4 | #4FBD81 #ADE0B4 #5DBFE9 #E7E6D4 |
| `nature-5c-1` | 5 | #808080 #F94141 #F3B169 #589FF3 #37AB78 |
| `nature-5c-2` | 5 | #60966D #5B3660 #FFC839 #E90F44 #63ADEE |
| `nature-5c-3` | 5 | #ABC6E4 #C39398 #FCDABA #A7D2BA #D0CADE |
| `nature-6c-1` | 6 | #C72228 #F98F34 #0C4E9B #F5867F #FFBC80 #6B98C4 |
| `nature-6c-2` | 6 | #3B549D #D3272B #6BBC46 #9EAAD1 #F29091 #B4DEA2 |
| `nature-6c-3` | 6 | #23B2E0 #000000 #EF2C2B #C2C2C2 #A5CC5B #EEBEC0 |
| `nature-6c-4` | 6 | #000000 #5CA400 #8BCF02 #338FEB #E7308B #B31761 |
| `nature-6c-5` | 6 | #C55645 #354898 #73ABCF #972D36 #FAAE5F #6B6B6B |
| `nature-6c-6` | 6 | #27447C #4871B3 #E73C36 #991F22 #B88640 #168676 |
| `nature-6c-7` | 6 | #3E6790 #6483A4 #646774 #858892 #AF873E #BD9E64 |
| `nature-6c-8` | 6 | #91CDC8 #6FB9D0 #5499BD #3981AF #386195 #324C63 |
| `nature-6c-9` | 6 | #FBB463 #80B1D3 #F47F72 #BDBADB #FBF8B4 #8DD1C6 |
| `nature-10c-1` | 10 | #F49568 #ED746A #DEAE8F #DBAA77 #82C61E #77DCDD #66C999 #638DEE #AA66EB #E0A4DD |
| `nature-10c-2` | 10 | #D2D2D2 #F5AB5E #947959 #5F97C6 #F09496 #9C9BE9 #AFC778 #EFDBB9 #A3CDEA #F4DFDD |
| `nature-10c-3` | 10 | #C2900F #BDC314 #656D14 #6AAF2D #FFC0F3 #E6D3A0 #E5E7A2 #C2C5A4 #C5E0AB #FFE6FA |
| `nature-10c-4` | 10 | #DEECF6 #AFC8E2 #E2F2CD #B6DAA7 #F9D5D5 #EF98A1 #FBE3C0 #FBC99A #E8E0EF #C2B1D7 |
| `nature-10c-5` | 10 | #A5D1B0 #CE8A8D #FFF7C1 #E0F3FF #ADD3F4 #F7C9CF #FEE4E8 #7CA3B8 #BFB8D6 #FCCB8E |
| `nature-12c-1` | 12 | #B7DAFE #7BB1E3 #00C892 #038766 #396251 #E8DC6C #F4A63A #CFBCD4 #A77D9A #DF562C #8A4B43 #1963B3 |
| `nature-12c-2` | 12 | #B12222 #FF4400 #FEA600 #FFE100 #DEB887 #F5E7BC #2E8A57 #9BCD31 #20B3AA #B0E1E7 #789CF2 #3B63E6 |
| `nature-15c-1` | 15 | #C0E2FD #FEC0C1 #CDC6FF #FDC0F7 #F3D8F1 #D6EBBF #E1CAF7 #BFDCE2 #F8F0BE #BEEFBF #F8C9C8 #C0E2D2 #E9BFC0 #E3E3E3 #BFBFBF |
| `nature-20c-1` | 20 | #D92B03 #F1997B #F38B2F #A5405E #F4C288 #088C00 #025939 #214EA7 #8B511F #DB6C76 #03C08B #7552A7 #DCA0DD #F2E851 #F1B543 #BF7533 #A38277 #592E13 #F2CDCF #6E86A5 |
| `nature-20c-2` | 20 | #C6DCB9 #B6E2DC #B8FABF #98F4E0 #8DECF5 #8FDBF3 #A2C4F1 #CEBAF0 #C6C3E1 #EEC2E5 #FFCFD1 #FBE3CD #F9F9CA #FAA09C #F9B29C #F9C89B #FBDF9D #E9E4AF #C6DCB9 #B6E2DC |
| `nature-24c-1` | 24 | #2279B0 #68BF69 #D2DC38 #F5B16E #F38F3C #CE9FCA #707070 #A9CCDE #734E9C #F7D1E3 #415C42 #FAE93B #8BB8D6 #F7BF6C #C0845C #61B673 #F37F76 #C3B0D2 #90D0C2 #0C0C0C #C6C2DF #BCD896 #EE9094 #D4242A |
