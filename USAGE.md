# nature-figure-kit - usage / 使用說明

本文件逐節中英對照：每節先列繁體中文，再列英文原文。指令、參數、檔名、JSON 鍵、選單按鍵、色票代號與 hex 值一律保留英文。
This manual is bilingual, section by section: Traditional Chinese (zh-TW) first, then English. Commands, flags, file names, JSON keys, menu keys, palette ids and hex values stay in English.

風格規則：[`docs/FIGURE_STYLE_SPEC.md`](docs/FIGURE_STYLE_SPEC.md)。概覽與安裝：[`README.md`](README.md)。代理快速參考：[`SKILL.md`](SKILL.md)。

以下所有路徑都相對於工具組資料夾。`DATA` 是放有六個輸入檔的資料夾，`MAN.json` 是其 SHA-256 manifest（內附合成數據為 `demo/data` 與 `demo/data_manifest.json`）。

Style rules: [`docs/FIGURE_STYLE_SPEC.md`](docs/FIGURE_STYLE_SPEC.md). Overview and installation: [`README.md`](README.md). Agent quick reference: [`SKILL.md`](SKILL.md).

All paths below are relative to the kit folder. `DATA` is a directory with the six inputs and `MAN.json` its SHA-256 manifest (`demo/data` and `demo/data_manifest.json` for the bundled synthetic data).

## Commands / 指令

```sh
python make_figures.py   --data DATA --manifest MAN.json --out OUT [--double-column] [--only NAMES] [--no-config]
python make_composite.py --data DATA --manifest MAN.json --out FIG.tiff --panels P1 P2 ... [options below]
python figmenu.py        --data DATA --manifest MAN.json [--config-dir DIR] [--script keys.txt --transcript t.txt]
python run_composites.py --data DATA --manifest MAN.json --out OUT/composite [--layout-acceptance]
python text_fit.py --out OUT ; python text_fit_composite_labels.py --out OUT ; python verify_figures.py --out OUT
bash demo/run_demo.sh                                  # end-to-end self-test, must end with DEMO OK
```

`bash demo/run_demo.sh` 是端到端自我測試，必須以 `DEMO OK` 結束。

`bash demo/run_demo.sh` is the end-to-end self-test and must end with `DEMO OK`.

## Composite layout / 組合圖版面

```sh
python make_composite.py --data DATA --manifest MAN.json --out FIG.tiff --panels 01_IR 03_TPC_overlay a.tiff \
    [--double-column] [--layout manual|auto] [--cols N] [--span a=row] [--span b=2x1] \
    [--empty-cells blank|legend] [--legend-entry 'Label=color[:style]'] [--legend-cell auto|ROW,COL] \
    [--force] [--max-height-mm 247] [--min-box-mm 20] [--max-dpi 2400] \
    [--label-format '(a)'] [--label-pt 14] [--config-dir DIR | --no-config]
```

### Layout modes / 版面模式

- **`--layout manual`**（預設）：`--cols` 欄（89 mm 預設 1 欄，183 mm 預設 2 欄），列數依需要而定。這是原本未變的行為；自訂的標籤格式與大小會被採用。
- **`--layout auto`**：工具以確定性方式搜尋 欄 x 列：1、2、3 ... 欄，列數由面板數與跨格決定。每個候選在繪製前都以下列條件評估：
  - 繪圖程式量測到的墨跡突出量（每個數據面板的試繪）；
  - 最小框寬（`--min-box-mm`，20 mm）；
  - x 軸標籤放得進其格子，PL 影像標籤放得進其正方形框；
  - 跨格的數據框維持 高/寬 >= 0.25；
  - 原生像素與熱圖格子所需的密度（<= `--max-dpi`）；
  - 匯入圖稿有效解析度 >= 600 dpi，且內含文字絕不縮小到 10 pt 以下（依其證據附屬檔）；
  - 若要求圖例，需有一個夠大的空格子；
  - 包含標籤、邊界、間距與跨格的總高度 <= `--max-height-mm`（247 mm）。

  第一個通過的候選（欄數最少，因此面板最大）會以最終尺寸繪製並再次檢查：繪製檢查、最終高度，以及完整的組合圖文字配合檢查（`text_fit.py` `composite_fit`）。若失敗，改試下一個候選。`FIG.json` 記錄 `grid` 與 `auto_layout`（每個候選的條件與理由、`selected_grid`、`selection_reason`、`forced`、`failed_criteria`）。
- **auto 搭配 `--cols`** 會把搜尋限制在正好該欄數；列數仍由面板與跨格決定。可用來指定幾何形狀，例如 `--cols 2 --span a=row` = 第一列全寬，加上 2 欄的主體。
- **auto 中的標籤** 固定為 (a)、(b) ... 14 pt Arial Bold；座標軸與色條標籤維持 12 pt，刻度/圖例 10 pt。絕不為了讓候選放得下而縮小文字。標籤設定衝突時：
  - 不同的 **已存** 標籤設定（`composite.json`）會被忽略，JSON 中的 `label.settings_source` 會註明；
  - 不同的 **明確** `--label-format` / `--label-pt` 是錯誤（結束碼 2）：自訂標籤請用 `--layout manual`。

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

### No fit and `--force` / 放不下與 `--force`

沒有任何 auto 候選放得下時，工具會印出 `WARNING: no auto layout fits ...`，附上每個候選的限制原因與建議。在 89 mm 時建議 `--double-column` 或拆成兩張圖；在 183 mm 時建議拆圖。它會寫出 `FIG.nofit.json`（含要求的幾何與候選），**不輸出 TIFF**，並以 **4** 結束。

加上 `--force` 則改為繪製備案：取只違反高度限制的最低候選，否則取違反條件最少者（再取高度最低者）。輸出時會在 `FIG.json` 中標記 `auto_layout.forced = true` 與 `auto_layout.failed_criteria`，繪製檢查通過時以 0 結束。文字大小不變。輸入錯誤（未知面板、格式錯誤的跨格、雜湊不符、圖例問題）與繪製錯誤，不論有無 `--force`，都仍會以非零結束碼停止執行。

結束碼：0 正常 · 1 繪製檢查失敗 · 2 用法/輸入錯誤（stderr 上的 `ERROR: ...`） · 4 沒有可用的 auto 版面。

When no auto candidate fits, the tool prints `WARNING: no auto layout fits ...` with the limiting reason of each candidate and a suggestion. At 89 mm it suggests `--double-column` or splitting into two figures; at 183 mm it suggests splitting. It writes `FIG.nofit.json` with the requested geometry and the candidates, publishes **no TIFF**, and exits **4**.

With `--force` it renders a fallback instead: the lowest candidate that fails only the height limit, otherwise the one with the fewest failed criteria (then the lowest height). The output is published with `auto_layout.forced = true` and `auto_layout.failed_criteria` in `FIG.json`, and the run exits 0 when its render checks pass. Text sizes are unchanged. Input errors (unknown panel, malformed span, hash mismatch, legend problems) and render errors still stop the run with a non-zero exit status, with or without `--force`.

Exit status: 0 ok · 1 render checks failed · 2 usage/input error (`ERROR: ...` on stderr) · 4 no auto layout fits.

### Spans / 跨格

`--span ID=row`（整個網格寬、一列）或 `--span ID=COLSxROWS`（例如 `2x1` = 兩欄乘一列，`1x2` = 一欄乘兩列）。此選項可重複，兩種版面模式皆可用。

- **ID** 是面板輸入位置的小寫字母（a = 第一個 `--panels` 項目），與標籤格式無關；使用 `(A)` 標籤時，第一個面板仍是 `a`。
- **排列：** 面板依閱讀順序放置。每個面板從前一面板起點或其後的第一個空格子開始，因此順序保持、矩形絕不重疊，被跳過的格子成為空格子。
- **幾何：** 跨格的框從第一個跨越欄的框邊延伸到最後一欄的框邊（列亦同），所以邊緣保持對齊。單列跨格保持一般面板的列高；多列跨格涵蓋其各列（若框需要更多空間，最後一列會變高）。
- **限制：** `05_PL_image` 保持其精確的正方形框，不能跨格。
- **錯誤（結束碼 2）：** 格式錯誤的值（`a=3`）、重複的 ID、沒有對應面板的 ID、比 manual 網格寬的跨格，以及 05 的跨格。在 auto 中，比候選網格寬的跨格只會使該候選不合格。
- **清除：** `--span none` 清除存在 `composite.json` 中的跨格。

`FIG.json` 記錄 `spans`、`positions`（每個面板的 row、col、col_span、row_span 與 cell）以及 `empty_cells`（`use`、`cells_rc`、`legend_cell_rc`、`blank_cells_rc`；從 0 起算，另有 `cells_rc_1based`）。

`--span ID=row` (full grid width, one row) or `--span ID=COLSxROWS` (for example `2x1` = two columns by one row, `1x2` = one column by two rows). The option is repeatable and works in both layout modes.

- **ID** is the lowercase letter of the panel's input position (a = first `--panels` item), whatever the label format; with `(A)` labels the first panel is still `a`.
- **Packing:** panels are placed in reading order. Each starts at the first free cell at or after the previous panel's start, so the order is kept, rectangles never overlap, and skipped cells become empty cells.
- **Geometry:** a spanning box runs from the first spanned column's box edge to the last one's (rows likewise), so edges stay aligned. A one-row span keeps the row height of an ordinary panel; a multi-row span covers its rows (the last row grows if the box needs more).
- **Limits:** `05_PL_image` keeps its exact square box and cannot span.
- **Errors (exit 2):** malformed values (`a=3`), duplicate IDs, IDs without a panel, a span wider than the manual grid, and a 05 span. In auto, a span wider than a candidate grid simply disqualifies that candidate.
- **Clearing:** `--span none` clears spans saved in `composite.json`.

`FIG.json` records `spans`, `positions` (row, col, col_span, row_span and cell for every panel) and `empty_cells` (`use`, `cells_rc`, `legend_cell_rc`, `blank_cells_rc`; 0-based, plus `cells_rc_1based`).

### Empty cells and the shared legend / 空格子與共用圖例

- `--empty-cells blank`（預設）讓未使用的格子保持白色。
- `--empty-cells legend` 在一個空格子中放一個共用圖例。圖例以可重複的 `--legend-entry 'Label=color[:style]'` 項目 **提供**（任何 Matplotlib 色彩；style 為 `solid`、`dashed`、`dotted` 或 `dashdot`）。以 1.5 pt 樣本線與 10 pt Arial Bold 文字繪製，無外框。
- **目標格子：** `--legend-cell auto`（預設）選擇 **閱讀順序中最後一個空格子**；`--legend-cell ROW,COL`（從 1 起算）指定一格，且該格必須是空的。圖例放在該格與框對齊的左上角；若放不下，則放在格子角落。
- **錯誤：** 圖例沒有項目、沒有空格子、指定的格子已被佔用，或圖例比其格子大。在 manual 模式這些是結束碼 2，在 auto 中則是該候選的一項失敗條件。
- **QA：** 圖例的繪圖文字框存在 `FIG.json`（`legend.texts`）。`text_fit.py` 與 `text_fit_composite_labels.py` 把它們納入重疊檢查，要求它們位於圖例格子內，並檢查其為 10 pt Arial Bold。

- `--empty-cells blank` (default) leaves unused cells white.
- `--empty-cells legend` puts one shared legend in an empty cell. The legend is **supplied** as repeatable `--legend-entry 'Label=color[:style]'` items (any Matplotlib colour; style `solid`, `dashed`, `dotted` or `dashdot`). It is drawn with 1.5 pt line samples and 10 pt Arial Bold text, without a frame.
- **Target cell:** `--legend-cell auto` (default) selects the **last empty cell in reading order**; `--legend-cell ROW,COL` (1-based) names one, and it must be empty. The legend sits at the cell's box-aligned top-left corner, or at the cell corner if it would not fit there.
- **Errors:** legend without entries, no free cell, an occupied requested cell, or a legend larger than its cell. These are exit 2 in manual mode and a failed criterion for that candidate in auto.
- **QA:** the legend's renderer text boxes are stored in `FIG.json` (`legend.texts`). `text_fit.py` and `text_fit_composite_labels.py` include them in the overlap checks, require them inside the legend cell, and check them at 10 pt Arial Bold.

### Settings precedence and saved config / 設定優先順序與已存設定

每個鍵的優先順序都相同：明確的 CLI 參數 > 已存的 `<config-dir>/composite.json` > 預設值。`--no-config` 忽略已存檔案（以及已存的座標軸覆寫）。跨格是單一鍵：任何 `--span` 都會取代已存的跨格，`--span none` 表示「沒有跨格」。

對應的 CLI 與 JSON 寫法：

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

只含標籤的檔案，例如 `{"composite": {"label_format": "(a)", "label_pt": 14.0}}`，仍然有效。每個鍵都是選填。

- **重設跨格：** 刪除 `spans` 鍵（或設為 `{}`），單次執行加 `--span none`，或在選單用 `g` -> `none` 再按 `s`。
- **全部重設：** 刪除 `composite.json`、使用 `--no-config`，或在選單用 `d`（重設，未儲存）再按 `s`。

A label-only file such as `{"composite": {"label_format": "(a)", "label_pt": 14.0}}` stays valid. Every key is optional.

- **Reset spans:** delete the `spans` key (or set `{}`), pass `--span none` for one run, or use the menu's `g` -> `none` and then `s`.
- **Reset everything:** delete `composite.json`, use `--no-config`, or use the menu's `d` (reset, unsaved) and then `s`.

### Menu (`figmenu.py`, main level `c`) / 選單（`figmenu.py`，主選單 `c`）

| 按鍵 / Key | 動作 / Action |
|---|---|
| `f` / `z` | 標籤格式 / 大小（`auto` = 預設值） / label format / size (`auto` = default) |
| `a` | 版面 `manual` / `auto`（`default` = manual） / layout `manual` / `auto` (`default` = manual) |
| `g` | 跨格：`a=row`、`b=2x1` 新增/取代 · `a=` 移除 · `none` 全部清除 / span: `a=row`, `b=2x1` add/replace · `a=` removes · `none` clears all |
| `e` | 空格子 `blank` / `legend` / empty cells `blank` / `legend` |
| `k` | 圖例格子 `auto` 或 `ROW,COL` / legend cell `auto` or `ROW,COL` |
| `o` | 圖例項目 `Label=color[:style]; Label2=...` 或 `none` / legend entries `Label=color[:style]; Label2=...` or `none` |
| `r` | 繪製 `--composite-panels` 的預覽（183 mm 時搭配 `--double-column`）：TIFF + JSON + `.preview.png`；印出網格、位置、空格子與 auto 選擇理由 / render preview of `--composite-panels` (with `--double-column` for 183 mm): TIFF + JSON + `.preview.png`; the grid, positions, empty cells and auto selection reason are printed |
| `s` / `l` / `d` / `p` / `b` | 儲存 / 重新載入 / 重設為預設值（未儲存） / 列印 / 返回 / save / reload / reset to defaults (unsaved) / print / back |

- **驗證：** 無效的值會被拒絕並顯示驗證訊息，保留先前的設定。這包括沒有對應預覽面板的跨格 ID、格式錯誤的跨格，以及沒有項目的圖例。
- **繪製：** `r` 會明確傳入每個顯示中的值（`--layout`、標籤、`--span ...` 或 `--span none`、`--empty-cells`、`--legend-cell`、`--legend-entry`）。因此即使磁碟上有較舊的 `composite.json`，未儲存的重設也會以顯示中的預設值繪製。
- **失敗：** 繪製失敗（放不下、圖例格子被佔用）會記錄在操作紀錄中，選單保持開啟。

腳本範例：`demo/menu_layout.keys`。

- **Validation:** invalid values are rejected with the validation message, and the previous settings are kept. This includes span IDs without a preview panel, malformed spans, and a legend without entries.
- **Render:** `r` passes every displayed value explicitly (`--layout`, labels, `--span ...` or `--span none`, `--empty-cells`, `--legend-cell`, `--legend-entry`). An unsaved reset therefore renders the displayed defaults even when an older `composite.json` is on disk.
- **Failures:** a failed render (no fit, occupied legend cell) is reported in the transcript, and the menu stays open.

Scripted example: `demo/menu_layout.keys`.

## Labels, legend text, heatmap time axis and shared legends (Batch 6) / 標籤、圖例文字、熱圖時間軸與共用圖例（Batch 6）

以下都是現有 `<config-dir>/<figure>.json` 中的每圖鍵（由 `figmenu.py` 寫入，`make_figures.py`、`make_composite.py` 與 `run_composites.py --config-dir` 會自動讀取）。每個鍵都是選填。只含 `"axes"` 的舊設定仍可原樣載入，並以下列預設值繪製。`--no-config` 會忽略它們。

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

### Axis and colour-bar labels (`labels`: `xlabel`, `ylabel`, `cbar_label`) / 座標軸與色條標籤

- 標籤繪製為 `name (unit)`；unit 為空時只繪製 `name`。每個部分未設定時退回預設值。`"unit": ""` 會移除單位。
- 預設值（在 `figure_config.DEFAULT_LABELS` 中；繪圖程式不再寫死標籤）見下表。標籤文字本身是圖上實際顯示的英文，保留原樣。
- 接受 mathtext：`cm$^{-1}$`、`2$\theta$`、`x$_{2}$`。Unicode 上下標會轉為真正的上下標：`cm⁻¹`（U+207B U+00B9）變成 `cm$^{-1}$`。數學式中的負號（`-`、U+207B、U+2212）會排成規範要求的半形連字號（`\text{-1}`）。`$` 不成對或無效的 mathtext 會被拒絕並顯示訊息。每個部分上限 80 個字元。
- 配合：每個最終標籤都會與其可用長度比較（x 標籤：數據框寬；y 標籤：數據框高；色條標籤：色條長度）。標籤較長時，工具會印出 `WARNING: label too long: <figure> <axis> label '<text>' is A mm, longer than its B mm available span`（也記錄在組合圖 JSON 的 `label_warnings` 與選單中）。字型大小絕不縮小。證據在 `qa/<figure>.style.json` → `layout.label_fit`。

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

  表中 06 的「(Time (s/min) with an interval)」意指設定擷取間隔後改為 Time (s/min)；08、09 的「as 06」意指與 06 相同。

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

### Hide tick numbers only (`axes.<x|y|colorbar>.tick_labels: false`) / 只隱藏刻度數字

刻度數字會被隱藏，若有數值偏移量（`x10^n`、`+c`）也一併隱藏。刻度線與座標軸標籤保留。證據：`layout.tick_numbers_hidden`（`offset_visible: false`、`tick_marks_visible`、`label_visible`）。

The tick numbers are hidden, and so is the numeric offset (`x10^n`, `+c`) when there is
one. The tick marks and the axis label stay. Evidence: `layout.tick_numbers_hidden`
(`offset_visible: false`, `tick_marks_visible`, `label_visible`).

### Legend text (`legend.labels`, figures 03 and 04) / 圖例文字（圖 03 與 04）

每條繪製的線有一個標籤（預設 `TPC 1 (D1-1)`、`TPC 2 (D2-1)`）。文字設定在繪製的線上，因此獨立圖例與組合圖的線條 handle 使用相同名稱。某一條線設為 `null` 或 `"auto"` 時保留其預設值。

There is one label per plotted line (default `TPC 1 (D1-1)`, `TPC 2 (D2-1)`). The text is
set on the plotted lines, so the standalone legend and the composite line handles use the
same names. `null` or `"auto"` for one line keeps its default.

### Heatmap acquisition interval (`heatmap.interval_s`, `heatmap.start_s`; 06, 08, 09) / 熱圖擷取間隔

- 沒有間隔時，x 是擷取編號（預設）。
- 有間隔時，x 變成經過時間 `start_s + (k - 1) * interval_s`。標示為 `Time (s)`，跨度超過 300 s 時為 `Time (min)`。第一個主刻度一定顯示起始值（0 或 `start_s`）。
- 原生格子密度檢查（每格 ≥ 1.1 裝置像素）使用繪製的座標。座標存在 `source_data/in_situ_PL.npz`（鍵例如 `x_06_elapsed_s`），點陣驗證透過紀錄中的 `raster.x_key` 讀取。

- Without an interval, x is the acquisition number (default).
- With an interval, x becomes the elapsed time `start_s + (k - 1) * interval_s`. It is
  labelled `Time (s)`, or `Time (min)` when the span exceeds 300 s. The first major
  tick always shows the starting value (0 or `start_s`).
- The native-cell density check (≥ 1.1 device px per cell) uses the plotted coordinate.
  The coordinate is stored in `source_data/in_situ_PL.npz` (key such as
  `x_06_elapsed_s`), and the raster verification reads it through the record's `raster.x_key`.

### Shared composite legend (`composite.json` `shared_legend`, `--shared-legend`) / 組合圖共用圖例

```json
{"composite": {"shared_legend": true, "spans": {"d": "row"}, "legend_cell": "2,2"}}
```

- `true` 會在一個空格子（以 `legend_cell` 選擇，`auto` = 最後一個空格子）放一個整張圖共用的圖例，並隱藏每個面板各自的圖例。此時 `empty_cells` 自動為 `legend`。`--no-shared-legend` 可覆寫已存的 `true`。
- 項目預設取自面板線條 handle：標籤、色彩、標記、線型與線寬，依閱讀順序，重複者合併。它們會跟隨圖例文字覆寫。
- 提供的 `legend_entries`（`'Label=color[:style[:marker]]'`，marker 為 `none o s ^ v D x + * .`）會取代它們。與 handle 相比，每一處數量或樣式（色彩、線型、標記）不一致都會印出 `WARNING: shared legend ...`，並記錄在組合圖 JSON（`legend.mismatch_warnings`）。
- 圖例大小納入版面量測（格子配合、auto 條件），其 10 pt 文字也納入文字配合證據。
- 沒有空白格子的範例：183 mm 的 4 個面板、`--cols 2`、`d=row`、圖例在 `2,2`。熱圖保持其一般框（長寬比 ≈ 0.68）。

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

### Composite y-label alignment and colour-bar pad / 組合圖 y 標籤對齊與色條間距

- 起始於同一欄的數據面板，其 y 標籤共用同一條左邊緣，即最靠左的自然位置。每個面板分開繪製，因此目標位置會回饋到面板繪製中。在組合後的圖頁上量測：`alignment.ylabel_alignment_per_column` 與檢查項 `ylabels_aligned_per_column`（差異 ≤ 1 px）。
- `paper_style.py` 中加大了色條間距：`COLORBAR_GAP_PT` 5 → 6 pt（框到色條）與 `COLORBAR_LABELPAD_PT` 3 → 4 pt（刻度到標籤）。突出量量測包含這些值。文字配合的組合圖紀錄 `colorbar_label_clearance` 給出每個色條標籤到其右側面板座標軸標籤（及最近文字）的間隙（mm）。發生碰撞時文字配合檢查失敗。

- The y labels of data panels that start in the same column share one left edge, the
  leftmost natural position. Each panel is rendered separately, so the target is fed back
  into the panel render. It is measured on the composed sheet:
  `alignment.ylabel_alignment_per_column` and check `ylabels_aligned_per_column` (spread ≤ 1 px).
- The colour-bar pad was increased in `paper_style.py`: `COLORBAR_GAP_PT` 5 → 6 pt (box to
  bar) and `COLORBAR_LABELPAD_PT` 3 → 4 pt (ticks to label). The overhang measurement
  includes them. The text-fit composite record `colorbar_label_clearance` gives the
  clearance in mm from each colour-bar label to the axis label (and nearest text) of the
  panel to its right. A collision fails the text fit.

### Menu keys (`figmenu.py`) / 選單按鍵

座標軸子選單（x、y、色條） / Axis submenus (x, y, colour bar):

| 按鍵 / Key | 動作 / Action |
|---|---|
| `l` | 編輯標籤：先 name 再 unit。每個提示接受文字、`auto`（預設值）或互動使用時的空白行（保留）。unit 另接受 `none`（無單位）。 / Edit the label: name, then unit. Each prompt takes text, `auto` (default) or a blank line in interactive use (keep). The unit also takes `none` (no unit). |
| `h` | `hide tick numbers only`（只隱藏刻度數字，切換）。 / `hide tick numbers only` (toggle). |

圖表選單 / Figure menu:

| 按鍵 / Key | 動作 / Action |
|---|---|
| `g` | 圖例文字（03/04）：`Control; Target`，或 `auto`。 / Legend text (03/04): `Control; Target`, or `auto`. |
| `i` | 擷取間隔，單位 s（06/08/09）：`1`、`5 start=10`，或 `auto`（擷取編號）。 / Acquisition interval in s (06/08/09): `1`, `5 start=10`, or `auto` (acquisition number). |

組合圖選單（主選單 `c`） / Composite menu (main level `c`):

| 按鍵 / Key | 動作 / Action |
|---|---|
| `h` | 共用圖例 `on` / `off` / `default`。 / Shared legend `on` / `off` / `default`. |
| `o` | 圖例項目；`none` = 使用面板 handle。 / Legend entries; `none` = use the panel handles. |

`s` 儲存，`l` 重新載入已存檔案，`d` 重設為預設值但不儲存。任何提示中的 `auto` 會恢復該值的預設值。腳本範例是 `demo/menu_b6.keys`，`bash demo/run_demo.sh` 第 11 步會檢查它。

`s` saves, `l` reloads the saved file and `d` resets to the defaults without saving.
`auto` in any prompt restores the default for that value. The scripted example is
`demo/menu_b6.keys`, and `bash demo/run_demo.sh` step 11 checks it.

## Batch 5 acceptance / Batch 5 驗收

`python run_composites.py --data DATA --manifest MAN.json --out OUT/composite --layout-acceptance [--qa-dir Q] [--preview-dir P]` 透過 CLI 執行 `make_composite.py`。它涵蓋 89 與 183 mm 下 4、6、7（要求 `--cols 2 --span a=row`）與 8 個面板的 auto 版面、`--force`、多列跨格、auto 與 manual 版面中的圖例，以及無效輸入案例。

它寫出 `layout_acceptance.json` 與 `layout_acceptance.md`：每個案例一列，含 case、width、n、grid、spans、height_mm、fits、warning、text_fit pass、結束碼與證據連結。也會寫出 PNG 預覽與各案例紀錄檔。只有在每個案例都符合預期時結束碼才是 0：

- 輸出的檔案通過 TIFF 標籤檢查與標籤/文字配合檢查；
- 放不下的案例會警告、以 4 結束且不輸出 TIFF；
- 無效輸入以 2 結束。

`python run_composites.py --data DATA --manifest MAN.json --out OUT/composite --layout-acceptance [--qa-dir Q] [--preview-dir P]` runs `make_composite.py` through its CLI. It covers auto layouts for 4, 6, 7 (requested `--cols 2 --span a=row`) and 8 panels at 89 and 183 mm, `--force`, a multi-row span, legends in auto and manual layouts, and the invalid-input cases.

It writes `layout_acceptance.json` and `layout_acceptance.md`: one row per case, with case, width, n, grid, spans, height_mm, fits, warning, text_fit pass, exit status and an evidence link. It also writes PNG previews and per-case logs. Exit status is 0 only when every case behaves as expected:

- published outputs pass the TIFF-tag checks and the label/text-fit checks;
- no-fit cases warn, exit 4 and publish no TIFF;
- invalid input exits 2.

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

- 同名同色：指定配色後，圖例名稱會在整次執行中依名稱上色（見下一節）。

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

- Same sample name, same colour: with a palette named, legend names are coloured by name across the run (see the section below).

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

### Overview / 概述

樣品/系列名稱就是套用設定覆寫後的圖例標籤（03/04 為 `legend.labels` 文字，例如 `MeO-2PACz`）。啟用依名稱上色時，同一個名稱在一次執行的每張圖、以及組合圖的每個面板中都得到相同色彩，即使系列順序不同或某張圖缺少部分樣品也一樣。邏輯在：`sample_colors.py`（`resolve(names_in_order, palette, pins, order)`，不繪圖）。

**名稱比對：** 去除前後空白後須完全相同；不做大小寫轉換（`2PACz` 與 `2pacz` 是兩個名稱）。沒有圖例標籤的系列（01、02、07、10）沒有名稱，維持依位置上色。

**何時啟用：** 指定配色（圖表設定的 `"palette"` 鍵或 `--palette`）或給了 pin（見下方共用對照表）時。沒有配色也沒有 pin 時什麼都不變：內附圖表完全保留其規範色彩與線型（#2166AC / #B35806，04 實線/虛線），逐像素相同。只有 pin 沒有配色：被 pin 的名稱取其 pin 色彩；未被 pin 的名稱依位置保留規範色彩（`source: "spec"`）。沒有配色時，只有 `order` 清單不會改變任何東西。

A sample/series name is its legend label after config overrides (for 03/04 the `legend.labels` text, e.g. `MeO-2PACz`). With name-based colouring on, a name gets the same colour in every figure of a run and in every panel of a composite, even when the series order differs or a figure lacks some samples. Logic: `sample_colors.py` (`resolve(names_in_order, palette, pins, order)`, no plotting).

**Name matching:** exact after stripping surrounding whitespace; no case folding (`2PACz` and `2pacz` are two names). Series without a legend label (01, 02, 07, 10) have no name and keep the position-based colouring.

**When it is active:** when a palette is named (figure `"palette"` key or `--palette`) or a pin is given (shared map below). With no palette and no pins nothing changes: the bundled figures keep their spec colours and linestyles exactly (#2166AC / #B35806, 04 solid/dashed), pixel for pixel. Pins without a palette: pinned names take their pin; unpinned names keep their spec colour by position (`source: "spec"`). An `order` list without a palette changes nothing.

### Assignment rule / 分配規則

**分配規則（確定性）：**

1. 被 pin 的名稱取其 pin 色彩。
2. 接著是共用對照表 `order` 清單中的名稱（若有），然後是其他每個名稱依 **首次出現順序**，各自取得下一個尚未被 pin 佔用的配色色彩（只要還有未使用的配色色彩，pin 的色彩就不會重複用於其他名稱）。
3. 首次出現：組合圖依面板順序（a、b、c ...，即命令列給定的順序），面板內依系列/圖例順序。`make_figures.py` 批次則依工具組的 FIGURE_NAMES 順序，再依系列順序。所有面板/圖表的所有名稱都在分配任何色彩 **之前** 收集完成，因此一個名稱在整次執行中只有一種色彩。
4. 單張圖的執行必須與組合圖一致：它們讀取相同的共用對照表（見下）。解析後的 名稱→色彩/線型 對照表會寫入每張圖與每張組合圖的 evidence/style JSON，並可透過明確的選項存入對照表，讓之後的單張圖執行重現它。

細節：`order` 中的名稱即使目前的圖沒有顯示它，也保留其位置（這使得已存的順序可以重現）。pin 的色彩即使被 pin 的名稱不在本次執行中，也算已佔用。在放得下的情況下，圖表自身的規範線型依位置保留（03/04 實線/虛線），所以圖例標籤順序反轉時，名稱保有其色彩，但不一定保有其虛線樣式。

**Assignment rule (deterministic):**

1. Pinned names take their pinned colour.
2. Then names listed in the shared map's `order` list (if any), then every other name in **first-appearance order**, each get the next palette colour that is not already taken by a pin (pinned colours are not reused for other names while unused palette colours remain).
3. First appearance: for a composite, panels in panel order (a, b, c ... as given on the command line), and inside a panel the series/legend order. For a `make_figures.py` batch, figures in the kit's FIGURE_NAMES order, then series order. All names of all panels/figures are collected **before** any colour is assigned, so one name has one colour across the whole run.
4. Single-figure runs must match the composite: they read the same shared map (below). The resolved name→colour/linestyle table is written to the evidence/style JSON of every figure and composite, and can be saved to the map with an explicit option so later single-figure runs reproduce it.

Details: a name in `order` keeps its slot even when the current figure does not show it (that is what makes a saved order reproducible). A pin's colour counts as taken even when the pinned name is absent from the run. While it fits, the figure's own spec linestyle stays by position (03/04 solid/dashed), so with reversed legend labels a name keeps its colour but not necessarily its dash.

### Shared map / pins file / 共用對照表 / pins 檔案

**共用對照表 / pins 檔案：** `<config-dir>/sample_colors.json`

**Shared map / pins file:** `<config-dir>/sample_colors.json`

```json
{"pins": {"MeO-2PACz": "#3B549D"}, "order": ["MeO-2PACz", "2PACz"]}
```

只允許 `pins` 與 `order` 兩個鍵（其他任何鍵都會被拒絕並顯示清楚的錯誤）；pin 色彩必須是 `#RRGGBB`，存檔時轉為大寫。檔案存在於設定資料夾時會自動讀取；`--no-config` 停用自動讀取。`--sample-colors FILE`（`make_figures.py`、`make_composite.py`、`figmenu.py`）明確指定檔案（加 `--no-config` 時也會讀取），此時它也是儲存目標。`--save-sample-colors`（`make_figures.py`、`make_composite.py`）把本次執行解析出的名稱順序附加到檔案的 `order`（已列出的名稱保留原位；pins 不變）。

Only the keys `pins` and `order` are allowed (anything else is rejected with a clear error); pin colours must be `#RRGGBB` and are saved uppercase. The file is read automatically when it exists in the config dir; `--no-config` disables the automatic read. `--sample-colors FILE` (on `make_figures.py`, `make_composite.py`, `figmenu.py`) names the file explicitly (also read with `--no-config`) and is then the save target. `--save-sample-colors` (`make_figures.py`, `make_composite.py`) appends the run's resolved name order to the file's `order` (names already listed keep their place; pins untouched).

### Overflow, composite, evidence, menu / 超量、組合圖、證據、選單

**超量 / 線型：** 超量是以本次執行中 **不同的** 未被 pin 名稱（加上 `order` 名稱）與可用配色色數（配色長度減去被 pin 佔用的配色色彩）比較。超過時，色彩在可用色彩中循環，且線型 **依每個名稱** 每循環一輪前進一次（solid -> dashed -> dotted -> dashdot），所以一個名稱在各處都保有同一組色彩 + 線型；被 pin 的名稱為實線。只有一則 `WARNING: sample colours: ...` 輸出到 stderr，並寫入 style JSON（`sample_colors.warnings`、`palette.warning`）與證據。兩個 pin 使用相同色彩是允許的，但會產生 `WARNING`。不會當機。當每個配色色彩都被 pin 佔用時，整組配色從 dashed 開始循環。

**組合圖：** `make_composite.py` 先收集所有數據面板的名稱（面板順序，再依圖例順序），並以同一張對照表為每個數據面板上色（`make_composite.py` 也有 `--palette NAME`；圖表設定的 `"palette"` 鍵在該面板優先；各面板指定不同配色時會產生 `WARNING`）。影像檔面板（TIFF/PNG/PDF 輸入）依提供的原樣放置，不會重新上色。`FIG.json` 記錄 `sample_colors`（`names_in_order`、`pins`、`order`、`by_panel` 對照表、`warnings`）。

**證據：** 每個 `qa/<figure>.style.json` 都有 `sample_colors`（本次執行的對照表、`names_in_order`、`series_names`、每個名稱的 `color`、`linestyle`、`source` pin|palette|spec、`color_used`、`linestyle_used`；或 `active: false` 加上原因），啟用時另有 `line_handles`；`evidence.sample_colors` 與 `qa/data_manifest.json`（`sample_colors.by_figure`）也帶有這張對照表。主控台輸出行：`SAMPLE COLORS <figure>: name=#HEX:linestyle (source); ...`。

**選單（`figmenu.py`，主選單 `n`）：** `a` pin（`MeO-2PACz=#3B549D`）、`u` 取消 pin、`c` 清除所有 pin、`o` order 清單（`MeO-2PACz; 2PACz; Me-4PACz`，或 `none`）、`t` 顯示每張圖例圖（03、04）與組合圖面板（`--composite-panels`）解析後的對照表、`s` 存到共用對照表檔案、`l` 重新載入、`p` 列印、`b` 返回。從選單繪製的圖表與組合圖預覽，使用目前顯示的對照表（包括未儲存的修改）。

**Overflow / linestyles:** overflow counts the **distinct** unpinned names of the run (plus `order` names) against the available palette colours (palette length minus the palette colours taken by pins). Beyond that the colours cycle over the available colours and the linestyle advances once per cycle **per name** (solid -> dashed -> dotted -> dashdot), so a name keeps one colour + linestyle everywhere; pinned names are solid. One `WARNING: sample colours: ...` goes to stderr and into the style JSON (`sample_colors.warnings`, `palette.warning`) and the evidence. Two pins with the same colour are allowed but give a `WARNING`. Nothing crashes. When every palette colour is pinned, the full palette cycles starting with dashed.

**Composite:** `make_composite.py` collects the names of all data panels first (panel order, then legend order) and colours every data panel from that one table (`--palette NAME` is available on `make_composite.py` too; a figure config `"palette"` key wins per panel; panels naming different palettes give a `WARNING`). Image-file panels (TIFF/PNG/PDF inputs) are placed as supplied and are not recoloured. `FIG.json` records `sample_colors` (`names_in_order`, `pins`, `order`, `by_panel` tables, `warnings`).

**Evidence:** every `qa/<figure>.style.json` has `sample_colors` (the run table, `names_in_order`, `series_names`, per-name `color`, `linestyle`, `source` pin|palette|spec, `color_used`, `linestyle_used`; or `active: false` with the reason) and `line_handles` when active; `evidence.sample_colors` and `qa/data_manifest.json` (`sample_colors.by_figure`) carry the table as well. Console lines: `SAMPLE COLORS <figure>: name=#HEX:linestyle (source); ...`.

**Menu (`figmenu.py`, main level `n`):** `a` pin (`MeO-2PACz=#3B549D`), `u` unpin, `c` clear all pins, `o` order list (`MeO-2PACz; 2PACz; Me-4PACz`, or `none`), `t` show the resolved table for each legend figure (03, 04) and for the composite panels (`--composite-panels`), `s` save to the shared map file, `l` reload, `p` print, `b` back. Figure renders and composite previews from the menu use the map as displayed (unsaved edits included).

### Examples and self-test / 範例與自我測試

**範例：** 第一行以 nature-6c-2 繪製並存下解析出的順序；第二行只繪製 04，透過已存的順序得到相同色彩；第三行以 183 mm 組合 04 與 03；第四行明確指定 pins/order 檔案。

**Examples:**

```sh
python make_figures.py --data DATA --manifest MAN.json --out OUT --palette nature-6c-2 --save-sample-colors
python make_figures.py --data DATA --manifest MAN.json --out OUT1 --palette nature-6c-2 --only 04_TPC_overlay_logtime   # same colours via the saved order
python make_composite.py --data DATA --manifest MAN.json --out fig.tiff --double-column --palette nature-6c-2 \
       --panels 04_TPC_overlay_logtime 03_TPC_overlay
python make_figures.py ... --sample-colors my_samples.json                                  # explicit pins/order file
```

**自我測試（僅合成數據）：** `python demo/test_samecolor.py --out demo_out/samecolor_test` 以 nature-6c-2 繪製兩個合成面板（a：MeO-2PACz、2PACz、Me-4PACz；b：Me-4PACz、MeO-2PACz），用 `make_composite.py` 組成一張 183 mm 的 TIFF（面板 1:1 放置，`--artwork-scale native`），並透過 JSON 與每個面板區域的精確像素檢查 同名 = 同 hex，以及 pin、首次出現與超量案例和對照表檔案規則。`bash demo/run_demo.sh` 的第 13 步會執行它，並另外以 nature-6c-2 與反轉的 04 圖例標籤繪製真實的 03/04（兩個 style JSON 中每個名稱色彩相同，已存的順序在只繪 04 的執行與組合圖中都能重現）。

**Self-test (synthetic data only):** `python demo/test_samecolor.py --out demo_out/samecolor_test` renders two synthetic panels (a: MeO-2PACz, 2PACz, Me-4PACz; b: Me-4PACz, MeO-2PACz) with nature-6c-2, assembles them with `make_composite.py` into one 183 mm TIFF (panels placed 1:1, `--artwork-scale native`), and checks same name = same hex via JSON and exact pixels per panel region, the pin, first-appearance and overflow cases and the map file rules. Step 13 of `bash demo/run_demo.sh` runs it and also renders the real 03/04 with nature-6c-2 and reversed 04 legend labels (same colour per name in both style JSONs, saved order reproduced in a 04-only run and in a composite).
