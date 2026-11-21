# Publication figure style / 出版圖表風格規範

本規範逐節中英對照：每節先列繁體中文，再列英文原文。所有數字與規則在兩種語言中相同。
This specification is bilingual, section by section: Traditional Chinese (zh-TW) first, then English. Every number and rule is the same in both languages.

本固定風格（house style）適用於全部十張圖表。字級與線寬以兩種欄寬模式下的最終出版尺寸計算。每個面板都使用相同設定。

This house style governs all ten figures. Type sizes and stroke widths apply at final publication size in both column modes. Use the same settings for every panel.

## Canvas and paper placement / 畫布與版面放置

以最終出版尺寸繪製並輸出，並以該尺寸放置 TIFF，不縮小。預設寬 89 mm（單欄）。使用 `--double-column` 得到 183 mm（雙欄）。一般圖表起始高度分別為 60 mm 與 105 mm，再依內容調整。05 的高度由正方形繪圖區與標籤間隙決定，並先保留右側色條的空間。記錄每張圖的目標尺寸。

使用滿版（full-bleed）版面。在固定畫布內盡量放大繪圖區。依實際繪製的刻度、標籤、圖例與色條調整邊界，目標是最外側可見圖形與每個畫布邊緣之間保留 1-2 mm 空白。在不產生空白帶的前提下，使繪圖框對齊方式一致。PL 影像保持原生像素長寬比，只保留其色條與標籤所需的空間。調整刻度密度、格式與圖例位置以避免碰撞。繪製後量測版面並檢查輸出的邊緣。以不裁切的邊界框輸出，保持頁面尺寸固定。

Draw and export at final publication size and place the TIFF at that size without downscaling. Default to 89 mm wide (single column). Use `--double-column` for 183 mm (double column). Start with heights of 60 mm and 105 mm, respectively, for ordinary plots and adjust to fit the content. For 05, derive the height from the square plot area and label clearances after reserving room for the right-hand colour bar. Record the target dimensions for each figure.

Use a full-bleed layout. Maximize the plot area within the fixed canvas. Fit the margins to the rendered ticks, labels, legends, and colour bars, aiming for 1-2 mm clear space between the outermost visible artwork and each canvas edge. Use comparable plot-box alignment where it does not introduce empty bands. Keep the native pixel aspect on the PL image and reserve only the space needed for its colour bar and labels. Adjust tick density, formatting, and legend placement to avoid collisions. Measure the layout after drawing and check the exported edges. Keep the page size fixed by exporting with an uncropped bounding box.

## Typography and strokes / 字型與線寬

| 元素 / Element | 最終尺寸 / At final size |
|---|---|
| 座標軸標籤與色條標題 / Axis labels and colour-bar titles | Arial Bold, 12 pt |
| 刻度標籤、科學記號偏移量、圖例及任何必要註解 / Tick labels, scientific offsets, legends, and any required annotations | Arial Bold, 10 pt |
| 數據線與對應的圖例樣本 / Data lines and matching legend samples | 1.5 pt |
| 密集光譜 07 與 10 的數據線與對應的圖例樣本 / Data lines and matching legend samples for dense spectra 07 and 10 | 1.25 pt |
| 邊框線與色條外框 / Spines and colour-bar outlines | 1.25 pt |
| 座標軸與色條上的主、次刻度線 / Major and minor tick marks on axes and colour bars | 1.0 pt |

- 所有可見文字都使用 Arial Bold，包括希臘字母與科學符號。使用位置正確的上標與下標，例如 IR 的 cm<sup>-1</sup>。使用半形連字號與括號。驗證實際使用的字型與字形涵蓋範圍。
- 十張圖都不加繪圖標題與整張圖的總標題（suptitle）。圖說放在稿件中。
- XRD、IR 及類似光譜（包括 PL 光譜圖）保持上方與右方邊框線可見。這兩側關閉主、次刻度與刻度標籤。保留左方與下方刻度。色條有自己的刻度與標籤。
- TPC 圖例保持精簡，對數時間面板中的十倍刻度標籤須清晰可讀。使用白色背景，並以色彩與線型兩者區分 TPC 曲線。

- Use Arial Bold for all visible text, including Greek and scientific glyphs. Use correctly positioned superscripts and subscripts, such as cm<sup>-1</sup> for IR. Use halfwidth hyphens and parentheses. Verify the actual font and glyph coverage.
- Omit plot titles and figure suptitles on all ten figures. Place captions in the manuscript.
- Keep top and right spines visible on XRD, IR, and similar spectra, including the PL spectrum figures. Disable both major and minor ticks and tick labels on those two sides. Keep left and bottom ticks. A colour bar has its own ticks and labels.
- Keep the TPC legends compact and the decade labels in the log-time panel legible. Use a white background and distinguish TPC traces with both colour and line pattern.

## Figure-specific fixes / 各圖特定修正

- **01 IR.** 遞減 x 軸的兩端各留約數據全跨度 2% 的空間。
- **03 TPC overlay.** 把顯示的線性時間軸裁到衰減區段。使用實線與虛線曲線。記錄顯示範圍，並在來源紀錄中保留完整數據。
- **04 TPC log-time overlay.** 使用藍色與黑色並搭配不同線型，使曲線在灰階列印中可區分。（此色彩規則已被下方「Batch 2 additions」取代。）
- **05 PL image.** 在右側使用直向色條，在保持正方形來源像素的同時，消除可避免的右側空白。
- **07 and 10 PL spectra.** 使用較細的 1.25 pt 數據線。

- **01 IR.** Pad each end of the descending x-axis by approximately 2% of the full data span.
- **03 TPC overlay.** Crop the displayed linear time axis to the decay region. Use solid and dashed traces. Record the display limits and retain the full data in provenance.
- **04 TPC log-time overlay.** Use blue and black with distinct line styles so the traces separate in grayscale print.
- **05 PL image.** Use a vertical colour bar on the right and eliminate avoidable right-side whitespace while keeping square source pixels.
- **07 and 10 PL spectra.** Use the thinner 1.25 pt data stroke.

## Data fidelity / 數據保真

保留現有繪圖程式中的觀測值、單位、座標順序、轉換、正規化分母與不確定度慣例。在來源紀錄中保留暫定的 XRD 角度解讀。05 保持其原生 3536 × 3536 像素、原點在上、正方形來源像素與完整視野。06、08 與 09 保留全部 1541 × 800 個數值與量測的波長座標。直接由完整原生陣列繪製格子，不平滑、不降採樣。使用循序色階 viridis：05 與 06 使用完整線性強度範圍，08 與 09 使用共用的 0-1 色階。

Preserve the observations, units, coordinate order, transformations, normalization denominators, and uncertainty conventions in the existing plotter. Keep the provisional XRD angle interpretation in provenance. Keep 05 at its native 3536 × 3536 pixels with upper origin, square source pixels, and the full field. For 06, 08, and 09, preserve all 1541 × 800 values and measured wavelength coordinates. Render the cells directly from the full native arrays without smoothing or downsampling. Use sequential viridis, with the full linear intensity range for 05 and 06 and the shared 0-1 scale for 08 and 09.

## Export / 輸出

- 只輸出 RGB TIFF，使用無損 LZW 壓縮、600 dpi 或更高，直接由固定、不裁切畫布上的圖輸出。每個 TIFF 都內嵌 sRGB ICC 色彩描述檔。
- 由完整原生陣列繪製影像與熱圖，不平滑、不降採樣。視需要提高 TIFF 密度，以在繪製的數據區中解析原生 3536 × 3536 PL 影像與每個原生熱圖格子。須考慮量測座標上最小的格距。
- 檢查儲存的 TIFF：內嵌 sRGB 描述檔、壓縮、解析度標籤、畫布尺寸、影像細節、熱圖格子邊界與重新取樣的瑕疵。以預定的紙面放置寬度檢視它們。

- Export only RGB TIFF with lossless LZW compression at 600 dpi or higher, directly from the figure on the fixed, uncropped canvas. Embed an sRGB ICC profile in every TIFF.
- Render images and heatmaps from the full native arrays without smoothing or downsampling. Increase the TIFF density as needed to resolve the native 3536 × 3536 PL image and every native heatmap cell in the rendered data area. Account for the smallest cell spacing along measured coordinates.
- Inspect the saved TIFFs for the embedded sRGB profile, compression, resolution tags, canvas dimensions, image detail, heatmap cell boundaries, and resampling artifacts. Review them at their intended paper placement widths.


## Batch 2 additions / Batch 2 補充

### Column widths and traces / 欄寬與曲線

- 只使用 Nature 欄寬。預設 89 mm（單欄）。使用 `--double-column` 時為 183 mm（雙欄）。
- 04 使用深橘色（`#B35806`）與現有的對比藍色（`#2166AC`），搭配不同線型與對應的圖例樣本。這取代先前對 04 的色彩規定。
- 07 與 10 在最終尺寸下使用 1.25 pt 數據線與對應的圖例樣本。

- Use Nature column widths only. Default to 89 mm (single column). Use 183 mm (double column) with `--double-column`.
- For 04, use dark orange (`#B35806`) and the existing contrasting blue (`#2166AC`) with distinct line styles and matching legend samples. This supersedes the earlier colour instruction for 04.
- For 07 and 10, use 1.25 pt data lines and matching legend samples at final size.

### Composite figures / 組合圖

- 在一張圖上以 89 mm 或 183 mm 的最終寬度排列多個面板。各列各欄的座標軸邊緣對齊，間距一致。匯入的影像面板以其外框邊緣對齊。
- 依閱讀順序自動加上面板標籤，格式為放在半形括號中的小寫字母：(a)、(b)、(c)，依此類推。以最終放置尺寸 14 pt Arial Bold 繪製。放在每個座標軸或影像外框左上角外側，偏移一致。座標軸與色條標籤維持 12 pt，刻度、科學記號偏移量、圖例與其他註解維持 10 pt；絕不為了放下標籤而縮小其他文字。在保持 89 或 183 mm 寬度下，以調整邊界、面板間距或圖高解決空間問題。此規則適用於兩種寬度的每張組合圖。
- 標籤格式與大小是使用者設定，可在終端機選單、已存的組合圖設定與組合圖 CLI 中設定。未設定時使用 (a) 與 14 pt。
- 視需要混合透過 `make_figures.py` 重新繪製的數據面板與現有的 TIFF、PNG 或 PDF 面板。匯入圖稿原樣放置，保持完整長寬比，不拉伸、不裁切。PDF 以最終放置尺寸、至少 600 dpi 的有效解析度點陣化，或保留向量圖稿直到最終點陣化。PDF 只作為輸入圖稿；輸出一律是 TIFF。
- 輸出一個固定畫布的 RGB TIFF，600 dpi 或更高，LZW 壓縮並內嵌 sRGB ICC。數據面板以其最終放置尺寸套用共用的風格與數據保真規則。

- Lay out multiple panels on one Figure at a final width of 89 mm or 183 mm. Align axes edges across rows and columns, with uniform gaps. Use the frame edges for imported image panels.
- Add panel labels automatically in reading order as lowercase letters in literal halfwidth parentheses: (a), (b), (c), and so on. Render them in Arial Bold at 14 pt at final placement size. Place them outside the top-left corner of each axes or image frame with a consistent offset. Keep axis and colour-bar labels at 12 pt and ticks, scientific offsets, legends, and other annotations at 10 pt; never shrink other text to fit a label. Resolve fit by adjusting margins, panel gaps, or figure height while keeping the 89 or 183 mm width. Apply this to every composite at both widths.
- The label format and size are user settings in the terminal menu, the saved composite config, and the composite CLI. Use (a) and 14 pt when they are absent.
- Mix data panels re-rendered through `make_figures.py` with existing TIFF, PNG, or PDF panels as needed. Place imported artwork as-is, keeping its full aspect ratio without stretching or cropping. Rasterize PDFs at an effective resolution of at least 600 dpi at final placement size, or retain vector artwork until final rasterization.
- Export one fixed-canvas RGB TIFF at 600 dpi or higher with LZW compression and embedded sRGB ICC. Apply the shared style and data fidelity rules to data panels at their final placement size.

### Terminal figure controls / 終端機圖表控制

- 提供可在 VS Code 終端機使用的純 Python 選單。選擇一張圖，再選擇其 x 軸、y 軸或色條（若有）。切換座標軸顯示、主刻度與次刻度。設定主刻度間距與最小、最大範圍。重新繪製，並把設定存成每張圖的 JSON 或 YAML 設定檔。
- 之後執行 `make_figures.py` 時自動載入已存的覆寫設定。未設定的選項使用規範預設值。保留座標軸尺度與方向，依所選尺度驗證範圍與間距，並保持光譜上方與右方邊框線沒有刻度。
- 透過管線 stdin 或腳本選項，以非互動方式支援相同的工作流程，以便測試。

- Provide a plain Python menu for the VS Code terminal. Select a figure, then select its x axis, y axis, or colour bar where present. Toggle axis visibility, major ticks, and minor ticks. Set the major tick step and minimum and maximum limits. Re-render and save the settings in a per-figure JSON or YAML config file.
- Load saved overrides automatically on subsequent `make_figures.py` runs. Use spec defaults for unset options. Preserve axis scale and direction, validate limits and steps against the selected scale, and keep the top and right spectrum spines free of ticks.
- Support the same workflow non-interactively through piped stdin or a script option so it can be tested.

2026-11-20 01:53：依使用者要求，面板標籤為 (a) 14 pt。

2026-11-20 01:53: panel labels (a) 14 pt per user
