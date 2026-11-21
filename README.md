# nature-figure-kit

繁體中文 / English: 本文件逐節中英對照，每節先列繁體中文，再列英文原文。指令、參數、檔名與色票代號一律保留英文。
This document is bilingual, section by section: Traditional Chinese (zh-TW) first, then English. Commands, flags, file names and palette ids stay in English.

## Overview / 概覽

直接從原始數據產生 Nature 最終尺寸的出版圖表。本工具組包含：

- **`make_figures.py`** 繪製十張固定風格（house style）的圖表（IR、XRD、TPC、PL 影像、in-situ PL 熱圖與光譜）。每張都是固定畫布的 RGB TIFF：寬 89 mm（單欄）或 183 mm（`--double-column`），≥ 600 dpi，LZW 壓縮，並內嵌 sRGB ICC 色彩描述檔。
- **`make_composite.py`** 由數據面板和/或現有的 TIFF、PNG 或 PDF 檔案組成多面板圖。它會對齊座標軸、保持間距一致、以 14 pt Arial Bold 標上面板標籤 (a)、(b)、(c)（格式與大小可設定），並輸出一個 TIFF。`--layout auto` 會自動選擇網格（高度 <= 247 mm，不縮小文字），`--span` 讓一個面板佔滿整列或多個格子，空格子可放共用圖例。
- **`figmenu.py`** 是純文字終端機選單（可在 VS Code 終端機使用），用於逐張圖設定座標軸：顯示/隱藏、主/次刻度、刻度間距、最小/最大值，以及組合圖面板標籤的格式與大小。設定存成 JSON，之後執行時會自動載入。
- **`verify_figures.py`** 是 QA 工具。它讀回每個 TIFF 的尺寸、dpi、壓縮與 ICC；記錄實際使用的字型與線寬；檢查每個熱圖格子與影像像素；並產生最終尺寸的總覽頁。

完整風格規則見 [`docs/FIGURE_STYLE_SPEC.md`](docs/FIGURE_STYLE_SPEC.md)；逐項選項用法（包括組合圖自動版面、跨格與圖例）見 [`USAGE.md`](USAGE.md)。摘要如下表。

Publication figures at final Nature size, straight from raw data. The kit includes:

- **`make_figures.py`** renders ten house-style figures (IR, XRD, TPC, PL image, in-situ PL heatmaps and spectra). Each one is a fixed-canvas RGB TIFF: 89 mm wide (single column) or 183 mm (`--double-column`), at ≥ 600 dpi, LZW-compressed, with an embedded sRGB ICC profile.
- **`make_composite.py`** builds multi-panel figures from data panels and/or existing TIFF, PNG or PDF files. It aligns the axes, keeps the gaps uniform, labels the panels (a), (b), (c) in 14 pt Arial Bold (format and size configurable) and exports one TIFF. `--layout auto` picks the grid itself (height <= 247 mm, no text shrinking), `--span` lets a panel cover a full row or several cells, and an empty cell can hold a shared legend.
- **`figmenu.py`** is a plain terminal menu (works in the VS Code terminal) for per-figure axis settings: visibility, major/minor ticks, tick step, min/max, plus the composite panel-label format and size. Settings are saved as JSON and loaded automatically on later runs.
- **`verify_figures.py`** is the QA tool. It reads back each TIFF's size, dpi, compression and ICC; records the fonts and stroke widths actually used; checks every heatmap cell and the image pixels; and builds a final-size overview sheet.

The full style rules are in [`docs/FIGURE_STYLE_SPEC.md`](docs/FIGURE_STYLE_SPEC.md); option-by-option usage, including automatic composite layout, spans and legends, is in [`USAGE.md`](USAGE.md). In short:

| 元素 / Element | 規則 / Rule |
|---|---|
| 文字 / Text | 所有文字皆為最終尺寸的 Arial Bold：座標軸與色條標籤 12 pt；刻度、偏移量、圖例與註解 10 pt；組合圖面板標籤 (a)、(b) ... 14 pt / Arial Bold everywhere at final size: 12 pt axis and colour-bar labels; 10 pt ticks, offsets, legends and annotations; composite panel labels (a), (b) ... 14 pt |
| 數據線 / Data lines | 1.5 pt（密集光譜 1.25 pt） / 1.5 pt (1.25 pt for dense spectra) |
| 邊框線 / Spines | 1.25 pt |
| 刻度 / Ticks | 1.0 pt |
| 外框 / Frame | 不加標題；上/右邊框線顯示但無刻度 / No titles; top/right spines visible without ticks |
| 影像 / Images | 原生像素與熱圖格子直接繪製，不平滑、不降採樣 / Native pixels and heatmap cells drawn without smoothing or downsampling |

## Installation / 安裝

```sh
python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

必須安裝 **Arial Bold**，且 Matplotlib 能找到它。可用 `fc-list | grep -i arial` 檢查；安裝後請刪除 `~/.cache/matplotlib`。本工具不會默默改用其他字型：除非你加上 `--font-substitute FAMILY`，否則會以結束碼 3 退出；用替代字型產生的輸出會被標記為不符合規範。

**Arial Bold** must be installed and visible to Matplotlib. Check with `fc-list | grep -i arial`; after installing it, delete `~/.cache/matplotlib`. The tool refuses to fall back silently: it exits with code 3 unless you pass `--font-substitute FAMILY`, and output made that way is flagged as non-compliant.

## Quick start (bundled demo data) / 快速開始（內附示範數據）

> **第一次執行：請先重新產生示範數據。** 兩個二進位示範輸入檔 `demo/data/XRD.xls` 與 `demo/data/in situ PL.xlsx` 沒有存放在本儲存庫中。執行 `bash demo/run_demo.sh` 之前，請先執行 `python demo/make_demo_data.py`。它會重建 `demo/data/` 中全部六個合成檔案，並改寫 `demo/data_manifest.json` 以符合這些檔案。

> **First run: regenerate the demo data.** The two binary demo inputs, `demo/data/XRD.xls` and `demo/data/in situ PL.xlsx`, are not stored in this repository. Before `bash demo/run_demo.sh`, run `python demo/make_demo_data.py`. It rebuilds all six synthetic files in `demo/data/` and rewrites `demo/data_manifest.json` to match them.

```sh
bash demo/run_demo.sh              # figures, double column, scripted menu, composites, verification
```

輸出寫到 `demo_out/`。只有在每一項檢查都通過時，腳本才會以 0 結束。

Outputs go to `demo_out/`. The script exits 0 only when every check passes.

**示範數據為合成數據。** `demo/data/` 中所有示範與範例數據都是合成的。`demo/make_demo_data.py` 以 NumPy 從固定種子（20261120）產生，不含任何實測數據。產生器不讀取任何輸入檔案。它以載入程式預期的相同檔案格式，寫出合理的 IR 吸收帶、XRD 峰、TPC 衰減、一張 221 x 221 的小型 PL 影像，以及 100 條隨時間漂移的 in situ PL 光譜。若要重建它們以及 `demo/data_manifest.json`（SHA-256、`"synthetic": true`、產生器與種子），請執行 `python demo/make_demo_data.py`。在同一套 NumPy/openpyxl 安裝下，輸出逐位元組可重現。不同 openpyxl 版本產生的 `.xlsx` zip 位元組可能不同，但儲存格數值相同；manifest 每次都會改寫。

**Demo data are synthetic.** All demo and example data in `demo/data/` are synthetic. `demo/make_demo_data.py` generates them with NumPy from a fixed seed (20261120), and they contain no measured data. The generator reads no input files. It writes plausible IR bands, XRD peaks, TPC decays, a small 221 x 221 PL map and 100 time-drifting in situ PL spectra in the same file formats the loaders expect. To rebuild them, together with `demo/data_manifest.json` (SHA-256, `"synthetic": true`, generator and seed), run `python demo/make_demo_data.py`. The output is byte-reproducible for a given NumPy/openpyxl install. The `.xlsx` zip bytes can differ between openpyxl versions, but the cell values stay the same, and the manifest is rewritten each time.

若要使用自己的數據，請把六個輸入檔放在同一個資料夾：`IR.csv`、`XRD.xls`、`TPC 1.txt`、`TPC 2.txt`、`PL_Image_Data.CSV`、`in situ PL.xlsx`。把它們的雜湊值記錄在 manifest 中（`{"source_sha256": {"IR.csv": "<sha256>", ...}}`），然後執行：

To use your own data, put the six inputs in one directory: `IR.csv`, `XRD.xls`, `TPC 1.txt`, `TPC 2.txt`, `PL_Image_Data.CSV`, `in situ PL.xlsx`. Record their hashes in a manifest (`{"source_sha256": {"IR.csv": "<sha256>", ...}}`), then run:

```sh
python make_figures.py --data DATA --manifest DATA_MANIFEST.json --out out            # all ten, 89 mm
python make_figures.py --data DATA --manifest DATA_MANIFEST.json --out out_wide --double-column --only 06_in_situ_PL_heatmap
```

`--only` 接受以逗號分隔、取自下列清單的基本名稱 / `--only` takes comma-separated basenames from this list:

- `01_IR`, `02_XRD`, `03_TPC_overlay`, `04_TPC_overlay_logtime`
- `05_PL_image`
- `06_in_situ_PL_heatmap`, `07_in_situ_PL_mean_spectrum`, `08_in_situ_PL_normalized_global`, `09_in_situ_PL_normalized_per_scan`, `10_in_situ_PL_normalized_mean_spectrum`

`--dpi` 是最低值：影像與熱圖會自動提高 dpi，以解析每一個原生像素或格子。每次執行都會寫出 `out/qa/data_manifest.json`（前/後雜湊值、版本、套用的覆寫設定）與 `out/qa/<name>.style.json`（繪圖物件證據）。

`--dpi` is a minimum: image and heatmap figures raise it automatically to resolve every native pixel or cell. Each run writes `out/qa/data_manifest.json` (hashes before/after, versions, applied overrides) and `out/qa/<name>.style.json` (artist evidence).

## Terminal menu / 終端機選單

```sh
python figmenu.py --data DATA --manifest DATA_MANIFEST.json            # interactive
python figmenu.py ... --script keys.txt --transcript session.txt       # scripted
printf '1\nx\nm\nt\n500\nb\ns\nr\nb\nq\n' | python figmenu.py ...     # piped stdin
```

| 層級 / Level | 按鍵 / Keys |
|---|---|
| 主選單 / Main | `1`-`10` 選擇圖表 · `c` 組合圖標籤、版面與跨格 · `q` 離開 / `1`-`10` pick a figure · `c` composite labels, layout and spans · `q` quit |
| 圖表 / Figure | `x` / `y` / `c` x 軸、y 軸、色條 · `r` 繪製 · `s` 儲存 · `l` 重新載入已存設定 · `d` 重設為預設值 · `p` 列印 · `b` 返回 / `x` / `y` / `c` x axis, y axis, colour bar · `r` render · `s` save · `l` reload saved · `d` reset to defaults · `p` print · `b` back |
| 座標軸 / Axis | `v` 顯示/隱藏 · `M` 主刻度 · `m` 次刻度 · `t` 間距 · `n` 最小值 · `x` 最大值（`auto` 清除） · `b` 返回 / `v` show/hide · `M` major ticks · `m` minor ticks · `t` step · `n` min · `x` max (`auto` clears) · `b` back |
| 組合圖 / Composite | `f` 格式 `(a)` `a` `a)` `a.` `(A)` `A` `A)` `A.` · `z` 大小 6-24 pt（`auto` = 預設 (a) / 14 pt） · `a` 版面 manual/auto · `g` 跨格（`a=row`、`b=2x1`、`a=`、`none`） · `e` 空格子 blank/legend · `k` 圖例格子 · `o` 圖例項目 · `r` 繪製預覽（`--composite-panels`） · `s` 儲存 · `l` 重新載入 · `d` 預設值 · `p` 列印 · `b` 返回 / `f` format `(a)` `a` `a)` `a.` `(A)` `A` `A)` `A.` · `z` size 6-24 pt (`auto` = default (a) / 14 pt) · `a` layout manual/auto · `g` spans (`a=row`, `b=2x1`, `a=`, `none`) · `e` empty cells blank/legend · `k` legend cell · `o` legend entries · `r` render preview (`--composite-panels`) · `s` save · `l` reload · `d` defaults · `p` print · `b` back |

輸入值會依座標軸尺度驗證（對數邊界 > 0、對數間距須為整數個十倍、`min < max`），被拒絕的值不會改變設定。座標軸方向會保留；例如 IR 波數軸維持遞減。

Values are validated against the axis scale (log bounds > 0, whole-decade log steps, `min < max`) and rejected values leave the setting unchanged. Axis direction is preserved; for example, the IR wavenumber axis stays descending.

**設定檔位置：** `--config-dir`，否則 `$FIGSTYLE_CONFIG_DIR`，否則工具旁的 `figure_configs/`。每張圖有自己的 `<figure>.json`；組合圖標籤設定存到 `composite.json`（`{"composite": {"label_format": "(a)", "label_pt": 14.0}}`）。`make_figures.py` 與 `make_composite.py` 會自動載入這些檔案。加上 `--no-config` 則以規範預設值繪製。

**Config location:** `--config-dir`, else `$FIGSTYLE_CONFIG_DIR`, else `figure_configs/` next to the tool. Each figure gets its own `<figure>.json`; composite label settings go to `composite.json` (`{"composite": {"label_format": "(a)", "label_pt": 14.0}}`). `make_figures.py` and `make_composite.py` load these files automatically. Pass `--no-config` to render spec defaults.

## Composite figures / 組合圖

```sh
python make_composite.py --data DATA --manifest DATA_MANIFEST.json --out fig1.tiff \
    --panels 01_IR 03_TPC_overlay other_panel.tiff photo.png scheme.pdf#1 [--double-column] [--cols 2] [--gap-mm 3] \
    [--label-format '(a)'] [--label-pt 14] [--layout manual|auto] [--span a=row] [--span b=2x1] \
    [--empty-cells blank|legend] [--legend-entry 'Label=color[:style]'] [--legend-cell auto|ROW,COL] [--force]
```

- **面板：** 基本名稱會透過圖表流程以最終尺寸重新繪製，套用相同的風格、覆寫設定與數據保真規則。TIFF 與 PNG 檔以一致的比例完整放入。PDF 由 PyMuPDF 以最終放置尺寸點陣化（≥ 600 dpi）。
- **標籤：** (a)、(b)、(c) ... 以最終尺寸 14 pt Arial Bold 標示，位於每個左上角外側、相同偏移處。`--label-format` / `--label-pt` 可覆寫；否則套用已存的 `composite.json`（加 `--no-config` 時忽略）；否則用預設值。其他文字維持 12/10 pt；標籤區會增加圖高，絕不縮小文字。
- **網格：** `--layout manual`（預設）：`--cols` 在 89 mm 預設為 1、在 183 mm 預設為 2，因為 12 pt 直向標籤需要較高的框；數據框至少與其 y 標籤一樣高。`--layout auto` 依序搜尋 1、2、3 ... 欄，並依量測的突出量、最小框尺寸、標籤是否放得下、原生像素密度、匯入圖稿比例、圖例格子以及總高度 <= 247 mm 來評估每個候選。它繪製第一個通過的網格，再以完整的文字配合檢查複驗，並在 JSON 中記錄網格與選擇理由。`--cols N` 將 auto 限制為 N 欄。auto 保持 (a) / 14 pt 標籤與 12/10 pt 文字，絕不縮小文字。若沒有任何候選放得下，會出現 `WARNING` 指出限制原因，並建議改用 183 mm 或拆成兩張圖；不寫出 TIFF，結束碼為 4。`--force` 會輸出一個有標記的備案版面。
- **跨格：** `--span a=row`（整列）或 `--span b=2x1`（欄 x 列），以輸入順序的字母指定。面板依閱讀順序排列，不重疊。`--span none` 清除已存的跨格設定。
- **空格子：** 留白，或以 `--empty-cells legend` 搭配 `--legend-entry` 項目（10 pt Arial Bold、1.5 pt 樣本線）放在最後一個空格子或 `--legend-cell ROW,COL`。
- **匯入圖稿：** `--artwork-scale fit`（預設）將每個 TIFF/PNG/PDF 等比例縮放到欄寬；`--artwork-scale native` 以 1.0 比例放置，使圖稿內已有的 12/10 pt 文字保持原大小。附屬的 `<file>.evidence.json`（繪圖程式紀錄）讓 `text_fit.py` 與 `verify_figures.py` 能檢查該圖稿的文字。
- **對齊與間距：** 各列各欄的框邊對齊，格子之間的間距一致。
- **密度：** 視需要提高，使 PL 影像每個原生像素對應整數個裝置像素，熱圖格子保持可解析。
- **紀錄：** `fig1.json` 保存版面、量測的對齊結果、檢查、各面板證據、解析後的位置/跨格/空格子、圖例的文字框，以及（auto 時）每個候選及其評估條件。
- **已存設定：** `composite.json` 也可保存 `layout`、`spans`、`empty_cells`、`legend_cell` 與 `legend_entries`。明確的 CLI 參數優先；只含標籤設定的檔案仍然有效。CLI/JSON 對應寫法與重設方法見 [`USAGE.md`](USAGE.md)。

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

`run_composites.py --data DATA --manifest MAN.json --out OUT/composite` 會以兩種寬度重現兩組範例：數據面板 01、03、04、05；以及以精確格寬繪製到 `OUT/composite/test_inputs/`、再以 1.0 比例放置的 TIFF + PNG + PDF 圖稿。除非指定 `--config-dir`，否則忽略選單已存的覆寫設定。`--layout-acceptance` 則改為透過實際 CLI 執行自動版面、跨格、圖例、`--force` 與無效輸入等案例，並寫出 `layout_acceptance.json` 與 `layout_acceptance.md`。

`run_composites.py --data DATA --manifest MAN.json --out OUT/composite` reproduces two example sets at both widths: data panels 01, 03, 04, 05; and TIFF + PNG + PDF artwork rendered at the exact cell width into `OUT/composite/test_inputs/` and placed at scale 1.0. Saved menu overrides are ignored unless `--config-dir` is given. `--layout-acceptance` instead runs the auto-layout, span, legend, `--force` and invalid-input cases through the real CLI, and writes `layout_acceptance.json` and `layout_acceptance.md`.

## Labels, legends and time axes (Batch 6) / 標籤、圖例與時間軸（Batch 6）

- 座標軸與色條標籤屬於設定，而非程式碼：每張圖的 `labels.xlabel|ylabel|cbar_label` = `{"name", "unit"}`（各座標軸子選單的 `l` 鍵；接受 mathtext 與 `cm⁻¹`；`auto` 恢復預設值）。標籤比其可用長度長時，會出現 `WARNING: label too long: <figure> <axis> ...`；文字絕不縮小。
- `axes.<axis>.tick_labels: false`（選單 `h`，「只隱藏刻度數字」）隱藏數字與偏移量，保留刻度與標籤。
- 03/04 的圖例文字（`legend.labels`，選單 `g`）；06/08/09 的熱圖擷取間隔（`heatmap.interval_s`，選單 `i`）會產生 `Time (s)` 或 `Time (min)`（> 300 s），第一個刻度 = 起始值。
- 組合圖：`--shared-legend` / `"shared_legend": true`（組合圖選單 `h`）把一個由面板線條建立的圖例放進空格子，並隱藏各面板圖例；不一致的 `--legend-entry` 值會以 `WARNING` 回報。y 標籤依欄對齊；色條間距為 6 pt，它與下一個面板的間隙由 `text_fit.py` 量測。
- 細節與設定範例：`USAGE.md` 的「Labels, legend text, heatmap time axis and shared legends」一節。示範：`demo/menu_b6.keys`，`bash demo/run_demo.sh` 的第 11 步。

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

## QA / 品質檢查

```sh
python text_fit.py --out OUT          # text/tick collisions, clipping, crop and edge clearance at final size
python verify_figures.py --out OUT    # size, dpi, LZW, sRGB ICC, fonts, point sizes, strokes, pixels
python text_fit_composite_labels.py --out OUT   # panel labels: overlap/clipping, Arial Bold 14 pt read-back, pixel re-render
```

`OUT` 採用示範的目錄結構：圖表在 `OUT/`，另有 `double_column/`、`composite/` 與 `qa/{before,after,menu_renders}/`。這些工具會寫出 `OUT/qa/text_fit.json`、`OUT/qa/verify_figures.json`、`OUT/qa/overview_final_size.tiff`，以及 `OUT/qa/preview/` 中的縮小預覽圖，全部通過時以 0 結束。

`OUT` uses the demo layout: figures in `OUT/`, plus `double_column/`, `composite/` and `qa/{before,after,menu_renders}/`. They write `OUT/qa/text_fit.json`, `OUT/qa/verify_figures.json`, `OUT/qa/overview_final_size.tiff` and downscaled previews in `OUT/qa/preview/`, and exit 0 when everything passes.

## Files / 檔案

| 檔案 / File | 用途 / Role |
|---|---|
| `make_figures.py`, `make_composite.py`, `figmenu.py`, `run_composites.py`, `text_fit.py`, `text_fit_composite_labels.py`, `verify_figures.py` | CLI 進入點 / CLI entry points |
| `verify_core.py` | 共用驗證輔助函式（TIFF 資訊、證據檢查、總覽） / shared verification helpers (TIFF facts, evidence checks, overview) |
| `plot_figures.py` | 數據讀取、轉換、來源紀錄（不含樣式） / data reading, transforms, provenance (no styling) |
| `paper_style.py`, `paper.mplstyle` | 字型解析、固定畫布版面、圖例/刻度碰撞處理、TIFF 輸出、證據 / font resolution, fixed-canvas layout, legend/tick collision handling, TIFF export, evidence |
| `figure_config.py` | 座標軸覆寫設定的結構、驗證、載入/儲存/套用 / axis-override schema, validation, load/save/apply |
| `palettes.py`, `palettes/nature_palettes.json` | 可選的系列配色（36 組 Nature 配色 + `okabe-ito`）：目錄、`list_palettes`、`get_palette`、`assign_series` / selectable series palettes (36 Nature palettes + `okabe-ito`): catalog, `list_palettes`, `get_palette`, `assign_series` |
| `docs/nature_palettes_preview.png` | 36 組 Nature 配色的預覽圖（複製自已驗證的轉錄預覽） / preview of the 36 Nature palettes (copied from the verified transcription preview) |
| `demo/test_palettes.py` | 合成數據的配色自我測試（nature-6c-2 繪製、超量、未知 id、okabe-ito） / synthetic palette self-test (nature-6c-2 render, overflow, unknown id, okabe-ito) |
| `sample_colors.py` | 同名同色：pins/order 對照表、整次執行的 名稱 -> 色彩/線型 解析器（不繪圖） / same sample name, same colour: pins/order map, run-wide name -> colour/linestyle resolver (no plotting) |
| `demo/test_samecolor.py` | 合成數據的同名同色自我測試（兩面板 183 mm 組合圖、pins、超量） / synthetic same-name-same-colour self-test (two-panel 183 mm composite, pins, overflow) |
| `qa_helpers.py` | `verify_figures.py` 使用的色彩查找表與熱圖格子稽核輔助函式 / colour LUT and heatmap-cell audit helpers used by `verify_figures.py` |
| `docs/FIGURE_STYLE_SPEC.md` | 圖表規範 / the figure specification |
| `USAGE.md` | 詳細用法：組合圖版面模式、跨格、圖例、已存設定、選單按鍵 / detailed usage: composite layout modes, spans, legends, saved settings, menu keys |
| `demo/menu_layout.keys` | 示範使用的組合圖版面/跨格/圖例腳本化選單流程 / scripted composite layout/span/legend menu session used by the demo |
| `demo/demo_config/02_XRD.json` | 僅供示範的 XRD 預設設定，用於 `run_demo.sh` 第 1 步（`axes.y.tick_labels: false`，y 標籤 `Intensity (a.u.)`） / demo-only default XRD config for `run_demo.sh` step 1 (`axes.y.tick_labels: false`, y label `Intensity (a.u.)`) |
| `SKILL.md`, `AGENTS.md`, `CLAUDE.md` | 給程式碼代理（coding agents）的說明 / instructions for coding agents |

## Selectable palettes / 可選配色

- 設定 JSON（每張圖，由 `figmenu.py` 儲存或手寫）：`{"figure": "04_TPC_overlay_logtime", "axes": {}, "palette": "nature-6c-2"}`。名稱會被驗證；未知的 id 會被拒絕，並列出一小段有效 id。
- CLI：`python make_figures.py ... --palette nature-6c-2` 或 `python figmenu.py ... --palette nature-6c-2`。這是本次執行的選擇，套用於設定中沒有 `palette` 鍵的每張線圖。
- 選單：在線圖選單（01、02、03、04、07、10）按 `P`，再輸入 id（`list` 列出每個 id 及其 hex，`none` 清除該圖的配色）。會印出所選 id 與其 hex 清單；按 `s` 儲存。
- 指定配色後，系列色彩會直接切換。單一系列的圖取第一個色；03/04 取前兩個色並保留實線/虛線組合。熱圖、PL 影像與色條維持原本的色彩對照表（`viridis`）。
- 若沒有指定配色，內附圖表保留規範色彩（#2166AC；03/04 為 #2166AC / #B35806 實線/虛線）。
- 超量：系列數多於配色所含色數時，色彩循環使用，且每循環一輪線型前進一次（solid -> dashed -> dotted -> dashdot，然後重複）。`WARNING: palette ... has N colours but M series were requested ...` 會輸出到 stderr，並寫入證據 / `qa/<figure>.style.json`（`palette.warning`）。不會當機。
- 證據：使用配色繪製的圖會在 `qa/<figure>.style.json` 記錄 `palette`、`palette_hex_used` 與 `line_handles`，完整分配結果記錄在 `evidence.palette`。
- Python：`import palettes; palettes.list_palettes(); palettes.get_palette("nature-6c-2"); palettes.assign_series(8, "nature-6c-2")`。`python palettes.py` 印出目錄；數據在 `palettes/nature_palettes.json`。
- 全部 36 組 Nature 配色的預覽：[`docs/nature_palettes_preview.png`](docs/nature_palettes_preview.png)（從來源文章經驗證的轉錄預覽原樣複製；二進位 PNG）。此 PNG 保留在本地工具組中，但沒有存放在 GitHub 儲存庫，因為純文字上傳無法攜帶二進位檔；下方 hex 表與 `python palettes.py` 會列出每一組配色。
- 自我測試（僅合成數據）：`python demo/test_palettes.py --out demo_out/palette_test`（也是 `bash demo/run_demo.sh` 的第 12 步）。

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

36 組 `nature-*` 配色的來源：[论文配色：跟着顶刊学配色（Nature篇）](https://www.163.com/dy/article/J70K7HOA0511CJ6T.html)（連結文字為原文章標題，保留原樣），hex 值由印出的標示轉錄（36 組配色、270 個 hex 值，保留順序）。`okabe-ito`（色盲友善）以另一個獨立名稱的配色提供。

Source of the 36 `nature-*` palettes: [论文配色：跟着顶刊学配色（Nature篇）](https://www.163.com/dy/article/J70K7HOA0511CJ6T.html), hex transcribed from printed labels (36 palettes, 270 hex values, order kept). `okabe-ito` (colour-blind friendly) is shipped as a separately named palette.

全部 37 個 id / All 37 ids:

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

## Same sample name, same colour / 同名同色

指定了配色（圖表設定的 `"palette"` 鍵或 `--palette`）或給了 pin 時，一個圖例名稱（套用設定覆寫後，例如 `MeO-2PACz`）在一次執行的每張圖、以及組合圖的每個數據面板中都會得到相同色彩，不論其位置；名稱比對在去除前後空白後須完全相同（不做大小寫轉換，大小寫不同即為不同名稱）。沒有配色也沒有 pin：什麼都不變（規範色彩，逐像素相同）。規則：先處理 pins；接著 `order` 清單中的名稱，再來其他名稱依首次出現順序（組合圖：面板順序，再依圖例順序；批次：FIGURE_NAMES 順序，再依系列順序）取得下一個未被 pin 佔用的配色色彩；所有名稱都在分配任何色彩之前收集完成。只有 pin 而沒有配色：未被 pin 的名稱依位置保留規範色彩。共用對照表 `<config-dir>/sample_colors.json` = `{"pins": {"MeO-2PACz": "#3B549D"}, "order": ["MeO-2PACz", "2PACz"]}`（自動讀取，`--no-config` 會略過；`make_figures.py`、`make_composite.py`、`figmenu.py` 有 `--sample-colors FILE`；`--save-sample-colors` 會附加解析後的順序，pins 不變）。超量（不同名稱數 > 未被 pin 佔用的配色色數）：色彩循環，線型依每個名稱、每循環一輪前進（solid -> dashed -> dotted -> dashdot），只出現一則 `WARNING`；在放得下的情況下，圖表自身的線型保持不變（04 實線/虛線）。重複的 pin 色彩會產生 `WARNING`。figmenu 主選單按鍵 `n`：pins、order、解析後的對照表。影像檔面板不會重新上色。對照表記錄在每個 style JSON 與 `FIG.json`（`sample_colors`）中。完整規則：`USAGE.md`；測試：`python demo/test_samecolor.py`（`demo/run_demo.sh` 的第 13 步）。

With a palette named (figure `"palette"` key or `--palette`) or a pin given, a legend name (after config overrides, e.g. `MeO-2PACz`) gets the same colour in every figure of a run and in every data panel of a composite, whatever its position; matching is exact after stripping surrounding whitespace (no case folding). No palette and no pins: nothing changes (spec colours, pixel-identical). Rule: pins first; then `order`-list names, then the other names in first-appearance order (composite: panel order, then legend order; batch: FIGURE_NAMES order, then series order) take the next palette colour not taken by a pin; all names are collected before any colour is assigned. Pins without a palette: unpinned names keep their spec colour by position. Shared map `<config-dir>/sample_colors.json` = `{"pins": {"MeO-2PACz": "#3B549D"}, "order": ["MeO-2PACz", "2PACz"]}` (read automatically, `--no-config` skips it; `--sample-colors FILE` on `make_figures.py`, `make_composite.py`, `figmenu.py`; `--save-sample-colors` appends the resolved order, pins untouched). Overflow (distinct names > palette colours not taken by pins): colours cycle, the linestyle advances per cycle per name (solid -> dashed -> dotted -> dashdot), one `WARNING`; while it fits the figure's own linestyles stay (04 solid/dashed). Duplicate pin colours give a `WARNING`. figmenu main-level key `n`: pins, order, resolved table. Image-file panels are not recoloured. The table is recorded in every style JSON and `FIG.json` (`sample_colors`). Full rule: `USAGE.md`; test: `python demo/test_samecolor.py` (step 13 of `demo/run_demo.sh`).
