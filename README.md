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
| `qa_helpers.py` | colour LUT and heatmap-cell audit helpers used by `verify_figures.py` |
| `docs/FIGURE_STYLE_SPEC.md` | the figure specification |
| `USAGE.md` | detailed usage: composite layout modes, spans, legends, saved settings, menu keys |
| `demo/menu_layout.keys` | scripted composite layout/span/legend menu session used by the demo |
| `demo/demo_config/02_XRD.json` | demo-only default XRD config for `run_demo.sh` step 1 (`axes.y.tick_labels: false`, y label `Intensity (a.u.)`) |
| `SKILL.md`, `AGENTS.md`, `CLAUDE.md` | instructions for coding agents |
