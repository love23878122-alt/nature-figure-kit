# Publication figure style

This house style governs all ten figures. Type sizes and stroke widths apply at final publication size in both column modes. Use the same settings for every panel.

## Canvas and paper placement

Draw and export at final publication size and place the TIFF at that size without downscaling. Default to 89 mm wide (single column). Use `--double-column` for 183 mm (double column). Start with heights of 60 mm and 105 mm, respectively, for ordinary plots and adjust to fit the content. For 05, derive the height from the square plot area and label clearances after reserving room for the right-hand colour bar. Record the target dimensions for each figure.

Use a full-bleed layout. Maximize the plot area within the fixed canvas. Fit the margins to the rendered ticks, labels, legends, and colour bars, aiming for 1-2 mm clear space between the outermost visible artwork and each canvas edge. Use comparable plot-box alignment where it does not introduce empty bands. Keep the native pixel aspect on the PL image and reserve only the space needed for its colour bar and labels. Adjust tick density, formatting, and legend placement to avoid collisions. Measure the layout after drawing and check the exported edges. Keep the page size fixed by exporting with an uncropped bounding box.

## Typography and strokes

| Element | At final size |
|---|---|
| Axis labels and colour-bar titles | Arial Bold, 12 pt |
| Tick labels, scientific offsets, legends, and any required annotations | Arial Bold, 10 pt |
| Data lines and matching legend samples | 1.5 pt |
| Data lines and matching legend samples for dense spectra 07 and 10 | 1.25 pt |
| Spines and colour-bar outlines | 1.25 pt |
| Major and minor tick marks on axes and colour bars | 1.0 pt |

- Use Arial Bold for all visible text, including Greek and scientific glyphs. Use correctly positioned superscripts and subscripts, such as cm<sup>-1</sup> for IR. Use halfwidth hyphens and parentheses. Verify the actual font and glyph coverage.
- Omit plot titles and figure suptitles on all ten figures. Place captions in the manuscript.
- Keep top and right spines visible on XRD, IR, and similar spectra, including the PL spectrum figures. Disable both major and minor ticks and tick labels on those two sides. Keep left and bottom ticks. A colour bar has its own ticks and labels.
- Keep the TPC legends compact and the decade labels in the log-time panel legible. Use a white background and distinguish TPC traces with both colour and line pattern.

## Figure-specific fixes

- **01 IR.** Pad each end of the descending x-axis by approximately 2% of the full data span.
- **03 TPC overlay.** Crop the displayed linear time axis to the decay region. Use solid and dashed traces. Record the display limits and retain the full data in provenance.
- **04 TPC log-time overlay.** Use blue and black with distinct line styles so the traces separate in grayscale print.
- **05 PL image.** Use a vertical colour bar on the right and eliminate avoidable right-side whitespace while keeping square source pixels.
- **07 and 10 PL spectra.** Use the thinner 1.25 pt data stroke.

## Data fidelity

Preserve the observations, units, coordinate order, transformations, normalization denominators, and uncertainty conventions in the existing plotter. Keep the provisional XRD angle interpretation in provenance. Keep 05 at its native 3536 × 3536 pixels with upper origin, square source pixels, and the full field. For 06, 08, and 09, preserve all 1541 × 800 values and measured wavelength coordinates. Render the cells directly from the full native arrays without smoothing or downsampling. Use sequential viridis, with the full linear intensity range for 05 and 06 and the shared 0-1 scale for 08 and 09.

## Export

- Export only RGB TIFF with lossless LZW compression at 600 dpi or higher, directly from the figure on the fixed, uncropped canvas. Embed an sRGB ICC profile in every TIFF.
- Render images and heatmaps from the full native arrays without smoothing or downsampling. Increase the TIFF density as needed to resolve the native 3536 × 3536 PL image and every native heatmap cell in the rendered data area. Account for the smallest cell spacing along measured coordinates.
- Inspect the saved TIFFs for the embedded sRGB profile, compression, resolution tags, canvas dimensions, image detail, heatmap cell boundaries, and resampling artifacts. Review them at their intended paper placement widths.


## Batch 2 additions

### Column widths and traces

- Use Nature column widths only. Default to 89 mm (single column). Use 183 mm (double column) with `--double-column`.
- For 04, use dark orange (`#B35806`) and the existing contrasting blue (`#2166AC`) with distinct line styles and matching legend samples. This supersedes the earlier colour instruction for 04.
- For 07 and 10, use 1.25 pt data lines and matching legend samples at final size.

### Composite figures

- Lay out multiple panels on one Figure at a final width of 89 mm or 183 mm. Align axes edges across rows and columns, with uniform gaps. Use the frame edges for imported image panels.
- Add panel labels automatically in reading order as lowercase letters in literal halfwidth parentheses: (a), (b), (c), and so on. Render them in Arial Bold at 14 pt at final placement size. Place them outside the top-left corner of each axes or image frame with a consistent offset. Keep axis and colour-bar labels at 12 pt and ticks, scientific offsets, legends, and other annotations at 10 pt; never shrink other text to fit a label. Resolve fit by adjusting margins, panel gaps, or figure height while keeping the 89 or 183 mm width. Apply this to every composite at both widths.
- The label format and size are user settings in the terminal menu, the saved composite config, and the composite CLI. Use (a) and 14 pt when they are absent.
- Mix data panels re-rendered through `make_figures.py` with existing TIFF, PNG, or PDF panels as needed. Place imported artwork as-is, keeping its full aspect ratio without stretching or cropping. Rasterize PDFs at an effective resolution of at least 600 dpi at final placement size, or retain vector artwork until final rasterization.
- Export one fixed-canvas RGB TIFF at 600 dpi or higher with LZW compression and embedded sRGB ICC. Apply the shared style and data fidelity rules to data panels at their final placement size.

### Terminal figure controls

- Provide a plain Python menu for the VS Code terminal. Select a figure, then select its x axis, y axis, or colour bar where present. Toggle axis visibility, major ticks, and minor ticks. Set the major tick step and minimum and maximum limits. Re-render and save the settings in a per-figure JSON or YAML config file.
- Load saved overrides automatically on subsequent `make_figures.py` runs. Use spec defaults for unset options. Preserve axis scale and direction, validate limits and steps against the selected scale, and keep the top and right spectrum spines free of ticks.
- Support the same workflow non-interactively through piped stdin or a script option so it can be tested.

2026-11-20 01:53: panel labels (a) 14 pt per user
