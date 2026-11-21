---
name: nature-figure-kit
description: Render, compose, adjust and verify Nature-size publication figures (89 mm / 183 mm RGB LZW TIFF with sRGB ICC, Arial Bold, fixed canvas) from raw IR, XRD, TPC, PL-image and in-situ PL data. Use when asked to make or fix manuscript figures, multi-panel composites, axis ticks/limits, or to audit figure TIFFs against the house spec. 中文：繪製、組合並驗證 Nature 尺寸的論文圖表。
---

# nature-figure-kit

本技能說明逐節中英對照：每節先列繁體中文，再列英文原文。指令、參數、檔名與色票代號一律保留英文。
This skill is bilingual, section by section: Traditional Chinese (zh-TW) first, then English. Commands, flags, file names and palette ids stay in English.

## When to use / 使用時機

- 製作或重新製作十張固定圖表中的任何一張（01_IR ... 10_in_situ_PL_normalized_mean_spectrum）。
- 由數據面板和/或 TIFF、PNG、PDF 圖稿組成多面板圖。
- 不改程式碼而調整座標軸（顯示/隱藏、主/次刻度、間距、最小/最大值）。
- 檢查輸出的 TIFF 是否符合規範（尺寸、dpi、LZW、sRGB ICC、字型、線寬、像素）。

不要用於互動式儀表板、統計分析或數據清理。本工具絕不改動數據：不平滑、不重新正規化、不擬合，也不刪除任何觀測值。

- Making or re-making any of the ten house figures (01_IR ... 10_in_situ_PL_normalized_mean_spectrum).
- Building a multi-panel figure from data panels and/or TIFF, PNG, PDF artwork.
- Changing an axis (visibility, major/minor ticks, step, min/max) without editing code.
- Checking that exported TIFFs meet the spec (size, dpi, LZW, sRGB ICC, fonts, strokes, pixels).

Do not use it for interactive dashboards, statistics, or data cleaning. The tool never changes the data: no smoothing, re-normalization, fitting or dropping of observations.

## Commands / 指令

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

`make_figures.py` 的結束碼：0 正常、2 輸入雜湊不符（不繪製任何東西）、3 缺少 Arial Bold、1 其他。`make_composite.py`：0 正常、1 繪製檢查失敗、2 用法/輸入錯誤、4 沒有可用的 auto 版面（不輸出 TIFF）。細節見 `USAGE.md`。

Exit codes for `make_figures.py`: 0 ok, 2 input hash mismatch (nothing rendered), 3 Arial Bold missing, 1 other. `make_composite.py`: 0 ok, 1 render checks failed, 2 usage/input error, 4 no auto layout fits (no TIFF). Details: `USAGE.md`.

## Figure spec (summary; full text in docs/FIGURE_STYLE_SPEC.md) / 圖表規範（摘要；全文見 docs/FIGURE_STYLE_SPEC.md）

- **畫布：** 預設寬 89 mm（起始高 60 mm）；`--double-column` 為 183 mm（起始高 105 mm）。當 12 pt 直向標籤比其數據框長時，高度以 1 mm 為單位增加。畫布是固定、不裁切的滿版（full bleed），墨跡與邊緣保留 1-2 mm 間隙，以最終尺寸放置、不縮放。
- **輸出：** RGB TIFF、LZW、≥ 600 dpi、內嵌 sRGB ICC。TIFF 是唯一的圖表格式。
- **文字：** 每個字形都用 Arial Bold。座標軸標籤與色條標題 12 pt；刻度標籤、科學記號偏移量、圖例與註解 10 pt；組合圖面板標籤 (a)、(b) ... 14 pt；全部以最終放置尺寸計。使用真正的上標（cm^-1）、半形連字號與括號。不加標題。
- **線寬：** 見下表。
- **光譜：** 四邊邊框線都顯示；上/右兩側沒有刻度或標籤。
- **各圖特定規則：**
  - 01：x 方向約 2 % 留白，遞減座標軸。
  - 03：衰減區間 0-10 µs，實線與虛線曲線。
  - 04：藍色 #2166AC 與深橘色 #B35806，搭配不同虛線樣式。
  - 05：右側色條；每個原生像素對應整數個裝置像素；原點在上（upper origin）；完整視野。
  - 06/08/09：每個原生格子在量測波長上都可解析。06 使用其完整線性範圍；08/09 使用共用的 0-1 色階。
- **組合圖：** 標籤 (a)、(b)、(c) ... 為 Arial Bold 14 pt（可透過 figmenu `c`、`composite.json`、`--label-format`/`--label-pt` 設定），位於每個左上角外側、相同偏移處；以邊界/間距/高度解決空間問題，絕不縮小文字；框邊對齊、間距一致。預設網格：89 mm 為 1 欄，183 mm 為 2 欄（12 pt 標籤需要寬度）。匯入圖稿以單一一致比例完整放置；`--artwork-scale native` 保持比例 1.0，使圖稿內的文字維持 12/10 pt（請以格寬繪製圖稿）。PDF 以放置尺寸 ≥ 600 dpi 點陣化。附屬的 `<file>.evidence.json` 讓 QA 能對應圖稿的文字框。
- **組合圖版面：** `--layout auto` 搜尋 欄 x 列，並依量測的突出量、最小框尺寸、標籤是否放得下、原生像素、圖稿比例、圖例格子與高度 <= 247 mm 評估每個候選。然後繪製第一個通過的網格，再以完整文字配合檢查複驗。auto 保持 (a) 14 pt 標籤與 12/10 pt 文字；絕不縮小文字。沒有任何候選放得下時，印出含原因與建議（183 mm 或拆成兩張圖）的 `WARNING`，以 4 結束且不輸出 TIFF；`--force` 會輸出一個在 JSON 中標記的備案。`--span a=row` / `b=2x1`（輸入順序字母）依閱讀順序排列跨格。空格子保持空白，或放一個圖例（`--empty-cells legend --legend-entry ...`，最後一個空格子或 `--legend-cell R,C`）。相同的鍵可存在 `composite.json`（CLI 參數優先；`--span none` 清除）。

- **Canvas:** 89 mm wide by default (starts at 60 mm tall); `--double-column` gives 183 mm (starts at 105 mm). Height grows in 1 mm steps when a 12 pt vertical label would be longer than its data box. The canvas is a fixed, uncropped full bleed with 1-2 mm ink clearance, placed at final size without scaling.
- **Export:** RGB TIFF, LZW, ≥ 600 dpi, embedded sRGB ICC. TIFF is the only figure format.
- **Text:** Arial Bold for every glyph. Axis labels and colour-bar titles 12 pt; tick labels, scientific offsets, legends and annotations 10 pt; composite panel labels (a), (b) ... 14 pt; all at final placement size. Use true superscripts (cm^-1), halfwidth hyphens and parentheses. No titles.
- **Strokes:**

  | 元素 / Element | 線寬 / Width |
  |---|---|
  | 數據線與圖例樣本 / Data lines and legend samples | 1.5 pt（07 與 10 為 1.25 pt） / 1.5 pt (1.25 pt for 07 and 10) |
  | 邊框線與色條外框 / Spines and colour-bar outlines | 1.25 pt |
  | 刻度 / Ticks | 1.0 pt |

- **Spectra:** all four spines visible; no ticks or labels on the top/right.
- **Figure-specific:**
  - 01: about 2 % x padding, descending axis.
  - 03: decay window 0-10 µs, solid and dashed traces.
  - 04: blue #2166AC and dark orange #B35806 with distinct dashes.
  - 05: right-hand colour bar; whole device pixels per native pixel; upper origin; full field.
  - 06/08/09: every native cell is resolved at the measured wavelengths. 06 uses its full linear range; 08/09 use a shared 0-1 scale.
- **Composites:** labels (a), (b), (c) ... in Arial Bold 14 pt (configurable via figmenu `c`, `composite.json`, `--label-format`/`--label-pt`) outside each top-left corner at one offset; fit is solved by margins/gaps/height, never by shrinking text; aligned box edges, uniform gaps. Default grid: 1 column at 89 mm, 2 at 183 mm (12 pt labels need the width). Imported artwork is placed whole at one uniform scale; `--artwork-scale native` keeps it at scale 1.0 so baked-in type stays 12/10 pt (render artwork at the cell width). PDFs are rasterized at ≥ 600 dpi at placement size. A `<file>.evidence.json` sidecar lets the QA map the artwork's text boxes.
- **Composite layout:** `--layout auto` searches columns x rows and qualifies each candidate on measured overhangs, minimum box size, label fit, native pixels, artwork scale, legend cell and height <= 247 mm. It then renders the first passing grid and re-checks it with the full text fit. Auto keeps (a) 14 pt labels and 12/10 pt text; it never shrinks text. When nothing fits, it prints a `WARNING` with the reason and a suggestion (183 mm or two figures) and exits 4 with no TIFF; `--force` publishes a fallback that is marked in the JSON. `--span a=row` / `b=2x1` (input-order letters) packs spans in reading order. Empty cells stay blank or take one legend (`--empty-cells legend --legend-entry ...`, last empty cell or `--legend-cell R,C`). The same keys can be saved in `composite.json` (CLI flags win; `--span none` clears).

## Rules for agents / 代理規則

- 把輸入數據視為唯讀。工具會在繪製前後依 manifest 驗證 SHA-256。
- 樣式改在 `paper.mplstyle` 與 `paper_style.py`，科學內容改在 `plot_figures.py`。絕不默默替換字型。
- 每張圖的覆寫設定用 `figmenu.py` 儲存，或以 JSON 存在設定資料夾；`make_figures.py` 會自動載入。
- 任何修改後，執行 `text_fit.py` 與 `verify_figures.py`（或 `demo/run_demo.sh`），回報實際量測結果，而非假設的結果。保持規範字級；以邊界、高度或刻度密度解決空間問題。

- Treat input data as read-only. The tool verifies SHA-256 against the manifest before and after rendering.
- Change styling in `paper.mplstyle` and `paper_style.py`, and the science in `plot_figures.py`. Never silently substitute fonts.
- Save per-figure overrides with `figmenu.py` or as JSON in the config directory; `make_figures.py` loads them automatically.
- After any change, run `text_fit.py` and `verify_figures.py` (or `demo/run_demo.sh`) and report the measured results, not assumed ones. Keep the spec type sizes; fix fit problems with margins, height or tick density.

## Labels, legends, time axes (Batch 6) / 標籤、圖例、時間軸（Batch 6）

- 每張圖的 JSON 鍵（全部選填；舊設定仍有效）：`labels.{xlabel,ylabel,cbar_label}.{name,unit}`（mathtext 或 `cm⁻¹`；`"unit": ""` = 無單位）、`axes.<x|y|colorbar>.tick_labels: false`（只隱藏刻度數字與偏移量）、`legend.labels`（03/04，每條線一個）、`heatmap.{interval_s,start_s}`（06/08/09：x = Time (s)，超過 300 s 為 Time (min)，第一個刻度 = 起始值）。
- figmenu：座標軸子選單 `l` 標籤 name/unit、`h` 只隱藏刻度數字；圖表選單 `g` 圖例文字、`i` 間隔；組合圖選單 `h` 共用圖例。`auto` 恢復預設值；`s` 儲存、`l` 重新載入、`d` 重設。
- `make_composite.py --shared-legend`（或 `composite.json` `"shared_legend": true`）：一個由面板線條 handle 建立的圖例放在空格子，隱藏各面板圖例；`--legend-entry 'Label=color[:style[:marker]]'` 不一致時印出 `WARNING`。y 標籤依欄對齊；色條間距 6 pt，間隙由文字配合檢查量測。
- 標籤比其可用長度長時印出 `WARNING: label too long: <figure> <axis> ...`；保持 12/10/14 pt，改為縮短標籤或加寬面板。

- Per-figure JSON keys (all optional; old configs stay valid): `labels.{xlabel,ylabel,cbar_label}.{name,unit}` (mathtext or `cm⁻¹`; `"unit": ""` = no unit), `axes.<x|y|colorbar>.tick_labels: false` (hide tick numbers and offset only), `legend.labels` (03/04, one per line), `heatmap.{interval_s,start_s}` (06/08/09: x = Time (s), or Time (min) above 300 s, first tick = start).
- figmenu: axis submenu `l` label name/unit, `h` hide tick numbers only; figure menu `g` legend text, `i` interval; composite menu `h` shared legend. `auto` restores a default; `s` save, `l` reload, `d` reset.
- `make_composite.py --shared-legend` (or `composite.json` `"shared_legend": true`): one legend from the panel line handles in an empty cell, panel legends suppressed; `--legend-entry 'Label=color[:style[:marker]]'` mismatches print `WARNING`s. Y labels align per column; colour-bar pad 6 pt, clearance measured by the text fit.
- A label longer than its span prints `WARNING: label too long: <figure> <axis> ...`; keep 12/10/14 pt and shorten the label or widen the panel.

## Selectable palettes / 可選配色

指定配色後，線圖的系列色彩會切換為該配色：每張圖的設定 `"palette": "nature-6c-2"`、CLI `--palette NAME`（`make_figures.py`、`figmenu.py`），或圖表選單按鍵 `P`。若沒有指定配色，內附圖表保留規範色彩。超量（系列多於色數）時色彩循環、線型前進（solid -> dashed -> dotted -> dashdot），並印出 `WARNING`，同時記錄在 style JSON。熱圖與色條保持其色彩對照表。完整 hex 表：`USAGE.md`；預覽：`docs/nature_palettes_preview.png`；測試：`python demo/test_palettes.py`。

36 組 `nature-*` 配色的來源：[论文配色：跟着顶刊学配色（Nature篇）](https://www.163.com/dy/article/J70K7HOA0511CJ6T.html)（連結文字為原文章標題，保留原樣），hex 值由印出的標示轉錄（36 組配色、270 個 hex 值，保留順序）。`okabe-ito` 為色盲友善配色。全部 37 個 id（n = 色數）列於下方清單。

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

## Same sample name, same colour / 同名同色

指定了配色（圖表設定的 `"palette"` 鍵或 `--palette`）或給了 pin 時，一個圖例名稱（套用設定覆寫後，例如 `MeO-2PACz`）在一次執行的每張圖、以及組合圖的每個數據面板中都會得到相同色彩，不論其位置；名稱比對在去除前後空白後須完全相同（不做大小寫轉換，大小寫不同即為不同名稱）。沒有配色也沒有 pin：什麼都不變（規範色彩，逐像素相同）。規則：先處理 pins；接著 `order` 清單中的名稱，再來其他名稱依首次出現順序（組合圖：面板順序，再依圖例順序；批次：FIGURE_NAMES 順序，再依系列順序）取得下一個未被 pin 佔用的配色色彩；所有名稱都在分配任何色彩之前收集完成。只有 pin 而沒有配色：未被 pin 的名稱依位置保留規範色彩。共用對照表 `<config-dir>/sample_colors.json` = `{"pins": {"MeO-2PACz": "#3B549D"}, "order": ["MeO-2PACz", "2PACz"]}`（自動讀取，`--no-config` 會略過；`make_figures.py`、`make_composite.py`、`figmenu.py` 有 `--sample-colors FILE`；`--save-sample-colors` 會附加解析後的順序，pins 不變）。超量（不同名稱數 > 未被 pin 佔用的配色色數）：色彩循環，線型依每個名稱、每循環一輪前進（solid -> dashed -> dotted -> dashdot），只出現一則 `WARNING`；在放得下的情況下，圖表自身的線型保持不變（04 實線/虛線）。重複的 pin 色彩會產生 `WARNING`。figmenu 主選單按鍵 `n`：pins、order、解析後的對照表。影像檔面板不會重新上色。對照表記錄在每個 style JSON 與 `FIG.json`（`sample_colors`）中。完整規則：`USAGE.md`；測試：`python demo/test_samecolor.py`（`demo/run_demo.sh` 的第 13 步）。

With a palette named (figure `"palette"` key or `--palette`) or a pin given, a legend name (after config overrides, e.g. `MeO-2PACz`) gets the same colour in every figure of a run and in every data panel of a composite, whatever its position; matching is exact after stripping surrounding whitespace (no case folding). No palette and no pins: nothing changes (spec colours, pixel-identical). Rule: pins first; then `order`-list names, then the other names in first-appearance order (composite: panel order, then legend order; batch: FIGURE_NAMES order, then series order) take the next palette colour not taken by a pin; all names are collected before any colour is assigned. Pins without a palette: unpinned names keep their spec colour by position. Shared map `<config-dir>/sample_colors.json` = `{"pins": {"MeO-2PACz": "#3B549D"}, "order": ["MeO-2PACz", "2PACz"]}` (read automatically, `--no-config` skips it; `--sample-colors FILE` on `make_figures.py`, `make_composite.py`, `figmenu.py`; `--save-sample-colors` appends the resolved order, pins untouched). Overflow (distinct names > palette colours not taken by pins): colours cycle, the linestyle advances per cycle per name (solid -> dashed -> dotted -> dashdot), one `WARNING`; while it fits the figure's own linestyles stay (04 solid/dashed). Duplicate pin colours give a `WARNING`. figmenu main-level key `n`: pins, order, resolved table. Image-file panels are not recoloured. The table is recorded in every style JSON and `FIG.json` (`sample_colors`). Full rule: `USAGE.md`; test: `python demo/test_samecolor.py` (step 13 of `demo/run_demo.sh`).
