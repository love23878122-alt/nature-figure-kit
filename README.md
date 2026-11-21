# nature-figure-kit

Publication figures at final Nature size, straight from raw data. The kit includes:

- **`make_figures.py`** renders ten house-style figures (IR, XRD, TPC, PL image, in-situ PL heatmaps and spectra). Each one is a fixed-canvas RGB TIFF: 89 mm wide (single column) or 183 mm (`--double-column`), at ≥ 600 dpi, LZW-compressed, with an embedded sRGB ICC profile.
- **`make_composite.py`** builds multi-panel figures from data panels and/or existing TIFF, PNG or PDF files. It aligns the axes, keeps the gaps uniform, labels the panels (a), (b), (c) in 14 pt Arial Bold (format and size configurable) and exports one TIFF. `--layout auto` picks the grid itself (height <= 247 mm, no text shrinking), `--span` lets a panel cover a full row or several cells, and an empty cell can hold a shared legend.
- **`figmenu.py`** is a plain terminal menu (works in the VS Code terminal) for per-figure axis settings: visibility, major/minor ticks, tick step, min/max, plus the composite panel-label format and size. Settings are saved as JSON and loaded automatically on later runs.
- **`verify_figures.py`** is the QA tool. It reads back each TIFF's size, dpi, compression and ICC; records the fonts and stroke widths actually used; checks every heatmap cell and the image pixels; and builds a final-size overview sheet.

The full style rules are in [`docs/FIGURE_STYLE_SPEC.md`](docs/FIGURE_STYLE_SPEC.md); option-by-option usage, including automatic composite layout, spans and legends, is in [`USAGE.md`](USAGE.md). In short:

| Element | Rule |
|---|---|
| Text | Arial Bold everywhere at final size: 12 pt axis and colour-bar labels; 10 pt ticks, offsets, legends and annotations; composite panel labels (a), (b) ... 14 pt |
| Data lines | 1.5 pt (1.25 pt for dense spectra) |
| Spines | 1.25 pt |
| Ticks | 1.0 pt |
| Frame | No titles; top/right spines visible without ticks |
| Images | Native pixels and heatmap cells drawn without smoothing or downsampling |

## Installation

```sh
python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Arial Bold** must be installed and visible to Matplotlib. Check with `fc-list | grep -i arial`; after installing it, delete `~/.cache/matplotlib`. The tool refuses to fall back silently: it exits with code 3 unless you pass `--font-substitute FAMILY`, and output made that way is flagged as non-compliant.

## Quick start (bundled demo data)

> **First run: regenerate the demo data.** The two binary demo inputs, `demo/data/XRD.xls` and `demo/data/in situ PL.xlsx`, are not stored in this repository. Before `bash demo/run_demo.sh`, run `python demo/make_demo_data.py`. It rebuilds all six synthetic files in `demo/data/` and rewrites `demo/data_manifest.json` to match them.

```sh
bash demo/run_demo.sh              # figures, double column, scripted menu, composites, verification
```

Outputs go to `demo_out/`. The script exits 0 only when every check passes.

**Demo data are synthetic.** All demo and example data in `demo/data/` are synthetic. `demo/make_demo_data.py` generates them with NumPy from a fixed seed (20261120), and they contain no measured data. The generator reads no input files. It writes plausible IR bands, XRD peaks, TPC decays, a small 221 x 221 PL map and 100 time-drifting in situ PL spectra in the same file formats the loaders expect. To rebuild them, together with `demo/data_manifest.json` (SHA-256, `"synthetic": true`, generator and seed), run `python demo/make_demo_data.py`. The output is byte-reproducible for a given NumPy/openpyxl install. The `.xlsx` zip bytes can differ between openpyxl versions, but the cell values stay the same, and the manifest is rewritten each time.

To use your own data, put the six inputs in one directory: `IR.csv`, `XRD.xls`, `TPC 1.txt`, `TPC 2.txt`, `PL_Image_Data.CSV`, `in situ PL.xlsx`. Record their hashes in a manifest (`{"source_sha256": {"IR.csv": "<sha256>", ...}}`), then run:

```sh
python make_figures.py --data DATA --manifest DATA_MANIFEST.json --out out            # all ten, 89 mm
python make_figures.py --data DATA --manifest DATA_MANIFEST.json --out out_wide --double-column --only 06_in_situ_PL_heatmap
```

`--only` takes comma-separated basenames from this list:

- `01_IR`, `02_XRD`, `03_TPC_overlay`, `04_TPC_overlay_logtime`
- `05_PL_image`
- `06_in_situ_PL_heatmap`, `07_in_situ_PL_mean_spectrum`, `08_in_situ_PL_normalized_global`, `09_in_situ_PL_normalized_per_scan`, `10_in_situ_PL_normalized_mean_spectrum`

`--dpi` is a minimum: image and heatmap figures raise it automatically to resolve every native pixel or cell. Each run writes `out/qa/data_manifest.json` (hashes before/after, versions, applied overrides) and `out/qa/<name>.style.json` (artist evidence).

## Terminal menu

```sh
python figmenu.py --data DATA --manifest DATA_MANIFEST.json            # interactive
python figmenu.py ... --script keys.txt --transcript session.txt       # scripted
printf '1\nx\nm\nt\n500\nb\ns\nr\nb\nq\n' | python figmenu.py ...     # piped stdin
```

| Level | Keys |
|---|---|
| Main | `1`-`10` pick a figure · `c` composite labels, layout and spans · `q` quit |
| Figure | `x` / `y` / `c` x axis, y axis, colour bar · `r` render · `s` save · `l` reload saved · `d` reset to defaults · `p` print · `b` back |
| Axis | `v` show/hide · `M` major ticks · `m` minor ticks · `t` step · `n` min · `x` max (`auto` clears) · `b` back |
| Composite | `f` format `(a)` `a` `a)` `a.` `(A)` `A` `A)` `A.` · `z` size 6-24 pt (`auto` = default (a) / 14 pt) · `a` layout manual/auto · `g` spans (`a=row`, `b=2x1`, `a=`, `none`) · `e` empty cells blank/legend · `k` legend cell · `o` legend entries · `r` render preview (`--composite-panels`) · `s` save · `l` reload · `d` defaults · `p` print · `b` back |

Values are validated against the axis scale (log bounds > 0, whole-decade log steps, `min < max`) and rejected values leave the setting unchanged. Axis direction is preserved; for example, the IR wavenumber axis stays descending.

**Config location:** `--config-dir`, else `$FIGSTYLE_CONFIG_DIR`, else `figure_configs/` next to the tool. Each figure gets its own `<figure>.json`; composite label settings go to `composite.json` (`{"composite": {"label_format": "(a)", "label_pt": 14.0}}`). `make_figures.py` and `make_composite.py` load these files automatically. Pass `--no-config` to render spec defaults.

## Composite figures

```sh
python make_composite.py --data DATA --manifest DATA_MANIFEST.json --out fig1.tiff \
    --panels 01_IR 03_TPC_overlay other_panel.tiff photo.png scheme.pdf#1 [--double-column] [--cols 2] [--gap-mm 3] \
    [--label-format '(a)'] [--label-pt 14] [--layout manual|auto] [--span a=row] [--span b=2x1] \
    [--empty-cells blank|legend] [--legend-entry 'Label=color[:style]'] [--legend-cell auto|ROW,COL] [--force]
```

- **Panels:** basenames are re-rendered through the figure pipeline at their final size, with the same style, overrides and fidelity rules. TIFF and PNG files are placed whole at a uniform scale. PDFs are rasterized by PyMuPDF at the final placement size (≥ 600 dpi).
- **Labels:** (a), (b), (c) ... in Arial Bold 14 pt at final size, at one offset outside each top-left corner. `--label-format` / `--label-pt` override; otherwise the saved `composite.json` applies (ignored with `--no-config`); otherwise the defaults. Other text keeps 12/10 pt; the label band grows the figure height, never shrinks text.
- **Grid:** `--layout manual` (default): `--cols` defaults to 1 at 89 mm and 2 at 183 mm, because 12 pt vertical labels need tall boxes; data boxes are made at least as tall as their y label. `--layout auto` searches 1, 2, 3 ... columns and qualifies each candidate on measured overhangs, minimum box size, label fit, native pixel density, imported-artwork scale, legend cell and total height <= 247 mm. It renders the first passing grid, re-checks it with the full text fit, and records the grid and the selection reason in the JSON. `--cols N` limits auto to N columns. Auto keeps (a) / 14 pt labels and 12/10 pt text, and never shrinks text. If nothing fits, a `WARNING` names the limiting reasons and suggests 183 mm or two figures; no TIFF is written and the exit status is 4. `--force` publishes a marked fallback.
- **Spans:** `--span a=row` (full row) or `--span b=2x1` (columns x rows), by input-order letter. Panels pack in reading order without overlap. `--span none` clears saved spans.
- **Empty cells:** blank, or `--empty-cells legend` with `--legend-entry` items (10 pt Arial Bold, 1.5 pt samples) in the last empty cell or `--legend-cell ROW,COL`.
- **Imported artwork:** `--artwork-scale fit` (default) scales every TIFF/PNG/PDF uniformly to the column width; `--artwork-scale native` places each at scale 1.0 so baked-in 12/10 pt type keeps its size. A sidecar `<file>.evidence.json` (renderer record) lets `text_fit.py` and `verify_figures.py` check that artwork's text.
- **Alignment and spacing:** box edges align across rows and columns, and the gaps between cells are uniform.
- **Density:** raised as needed so the PL image keeps whole device pixels per native pixel and heatmap cells stay resolved.
- **Record:** `fig1.json` holds the layout, the measured alignment, checks, per-panel evidence, resolved positions/spans/empty cells, the legend's text boxes and (auto) every candidate with its criteria.
- **Saved settings:** `composite.json` may also hold `layout`, `spans`, `empty_cells`, `legend_cell` and `legend_entries`. Explicit CLI flags win; label-only files stay valid. See [`USAGE.md`](USAGE.md) for the CLI/JSON equivalents and how to reset.

`run_composites.py --data DATA --manifest MAN.json --out OUT/composite` reproduces two example sets at both widths: data panels 01, 03, 04, 05; and TIFF + PNG + PDF artwork rendered at the exact cell width into `OUT/composite/test_inputs/` and placed at scale 1.0. Saved menu overrides are ignored unless `--config-dir` is given. `--layout-acceptance` instead runs the auto-layout, span, legend, `--force` and invalid-input cases through the real CLI, and writes `layout_acceptance.json` and `layout_acceptance.md`.

## Labels, legends and time axes (Batch 6)

- Axis and colour-bar labels are config, not code: `labels.xlabel|ylabel|cbar_label` = `{"name", "unit"}`
  per figure (menu `l` in each axis submenu; mathtext and `cm⁻¹` accepted; `auto` restores the default).
  A label longer than its span gives `WARNING: label too long: <figure> <axis> ...`; text is never shrunk.
- `axes.<axis>.tick_labels: false` (menu `h`, "hide tick numbers only") hides the numbers and the offset, keeps
  the ticks and the label.
- Legend text for 03/04 (`legend.labels`, menu `g`); heatmap acquisition interval for 06/08/09
  (`heatmap.interval_s`, menu `i`) gives `Time (s)` or `Time (min)` (> 300 s), first tick = start.
- Composites: `--shared-legend` / `"shared_legend": true` (composite menu `h`) puts one legend built from the
  panel line handles into an empty cell and suppresses the panel legends; mismatching `--legend-entry` values
  are reported as `WARNING`s. Y labels align per column; the colour-bar pad is 6 pt and its clearance to
  the next panel is measured by `text_fit.py`.
- Details and config examples: `USAGE.md`, "Labels, legend text, heatmap time axis and shared legends".
  Demo: `demo/menu_b6.keys`, step 11 of `bash demo/run_demo.sh`.

## QA

```sh
python text_fit.py --out OUT          # text/tick collisions, clipping, crop and edge clearance at final size
python verify_figures.py --out OUT    # size, dpi, LZW, sRGB ICC, fonts, point sizes, strokes, pixels
python text_fit_composite_labels.py --out OUT   # panel labels: overlap/clipping, Arial Bold 14 pt read-back, pixel re-render
```

`OUT` uses the demo layout: figures in `OUT/`, plus `double_column/`, `composite/` and `qa/{before,after,menu_renders}/`. They write `OUT/qa/text_fit.json`, `OUT/qa/verify_figures.json`, `OUT/qa/overview_final_size.tiff` and downscaled previews in `OUT/qa/preview/`, and exit 0 when everything passes.

## Files

| File | Role |
|---|---|
| `make_figures.py`, `make_composite.py`, `figmenu.py`, `run_composites.py`, `text_fit.py`, `text_fit_composite_labels.py`, `verify_figures.py` | CLI entry points |
| `verify_core.py` | shared verification helpers (TIFF facts, evidence checks, overview) |
| `plot_figures.py` | data reading, transforms, provenance (no styling) |
| `paper_style.py`, `paper.mplstyle` | font resolution, fixed-canvas layout, legend/tick collision handling, TIFF export, evidence |
| `figure_config.py` | axis-override schema, validation, load/save/apply |
| `palettes.py`, `palettes/nature_palettes.json` | selectable series palettes (36 Nature palettes + `okabe-ito`): catalog, `list_palettes`, `get_palette`, `assign_series` |
| `docs/nature_palettes_preview.png` | preview of the 36 Nature palettes (copied from the verified transcription preview) |
| `demo/test_palettes.py` | synthetic palette self-test (nature-6c-2 render, overflow, unknown id, okabe-ito) |
| `qa_helpers.py` | colour LUT and heatmap-cell audit helpers used by `verify_figures.py` |
| `docs/FIGURE_STYLE_SPEC.md` | the figure specification |
| `USAGE.md` | detailed usage: composite layout modes, spans, legends, saved settings, menu keys |
| `demo/menu_layout.keys` | scripted composite layout/span/legend menu session used by the demo |
| `demo/demo_config/02_XRD.json` | demo-only default XRD config for `run_demo.sh` step 1 (`axes.y.tick_labels: false`, y label `Intensity (a.u.)`) |
| `SKILL.md`, `AGENTS.md`, `CLAUDE.md` | instructions for coding agents |

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
