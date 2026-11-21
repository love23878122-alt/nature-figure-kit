# Claude Code instructions

## 繁體中文摘要 (zh-TW summary)

本檔是給 Claude Code 的說明：完全依照 `AGENTS.md`，並以 `SKILL.md` 作為技能說明與快速參考。優先使用現有 CLI，每項工作最後執行 `bash demo/run_demo.sh`（或 `text_fit.py` 與 `verify_figures.py`）並引用 PASS/FAIL 行。

- 設定：`python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`，並需安裝 Arial Bold。任何修改後執行 `bash demo/run_demo.sh`，必須以 `DEMO OK` 結束（結束碼 0）。
- 絕不縮小文字：字級固定為 12 pt 座標軸/色條標籤、10 pt 刻度/圖例/註解、14 pt 組合圖面板標籤 (a)、(b) ...（12/10/14 pt）。文字碰撞或被裁切時，調整邊界、畫布高度或刻度密度，並以 `WARNING` 回報，不改字級。
- 寬度只有 89 mm（單欄）與 183 mm（`--double-column`）。只輸出 TIFF（LZW、≥ 600 dpi、內嵌 sRGB ICC）；PDF 只能作為組合圖的輸入圖稿。
- 配色為選用（opt-in）：只有用 `--palette NAME`、圖表設定 `"palette"` 鍵或選單 `P` 指定時才套用，不會自動啟用；未指定時內附圖表保留規範色彩。
- 同名同色：指定配色或 pin 時，同一圖例名稱在整次執行與組合圖中顏色相同；共用對照表 `<config-dir>/sample_colors.json`（`pins`、`order`），參數 `--sample-colors FILE`、`--save-sample-colors`，figmenu 主選單按鍵 `n`。
- 細節請看 `SKILL.md` 與 `USAGE.md`（完整 hex 表與分配規則）。以下英文內容為主要文字，完整保留。

## Instructions (English) / 英文說明

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

## Same sample name, same colour

With a palette named (figure `"palette"` key or `--palette`) or a pin given, a legend name (after config overrides, e.g. `MeO-2PACz`) gets the same colour in every figure of a run and in every data panel of a composite, whatever its position; matching is exact after stripping surrounding whitespace (no case folding). No palette and no pins: nothing changes (spec colours, pixel-identical). Rule: pins first; then `order`-list names, then the other names in first-appearance order (composite: panel order, then legend order; batch: FIGURE_NAMES order, then series order) take the next palette colour not taken by a pin; all names are collected before any colour is assigned. Pins without a palette: unpinned names keep their spec colour by position. Shared map `<config-dir>/sample_colors.json` = `{"pins": {"MeO-2PACz": "#3B549D"}, "order": ["MeO-2PACz", "2PACz"]}` (read automatically, `--no-config` skips it; `--sample-colors FILE` on `make_figures.py`, `make_composite.py`, `figmenu.py`; `--save-sample-colors` appends the resolved order, pins untouched). Overflow (distinct names > palette colours not taken by pins): colours cycle, the linestyle advances per cycle per name (solid -> dashed -> dotted -> dashdot), one `WARNING`; while it fits the figure's own linestyles stay (04 solid/dashed). Duplicate pin colours give a `WARNING`. figmenu main-level key `n`: pins, order, resolved table. Image-file panels are not recoloured. The table is recorded in every style JSON and `FIG.json` (`sample_colors`). Full rule: `USAGE.md`; test: `python demo/test_samecolor.py` (step 13 of `demo/run_demo.sh`).
