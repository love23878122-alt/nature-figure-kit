"""Compose several panels into one Nature-width figure (one RGB LZW TIFF, sRGB ICC).

    python make_composite.py --panels 01_IR 03_TPC_overlay a.tiff b.png c.pdf[#page]
                             --out FIG.tiff [--double-column] [--cols N] [--data DIR]
                             [--layout manual|auto] [--span a=row] [--span b=2x1] [--force]
                             [--empty-cells blank|legend] [--legend-entry 'Label=color[:style]']
                             [--legend-cell auto|ROW,COL] [--max-height-mm 247]
                             [--gap-mm 3] [--dpi 600] [--box-aspect 0.68] [--artwork-scale fit|native]
                             [--config-dir DIR | --no-config]
                             [--label-format '(a)'] [--label-pt 14]
                             [--palette NAME] [--sample-colors FILE] [--save-sample-colors]

Same sample name, same colour (sample_colors.py): with a palette named
(``--palette`` or a figure config "palette" key) or pins given, every data
panel uses one run-wide name table. All series names of all data panels are
collected first (panels in --panels order, then legend order) and only then
coloured, so a name has the same colour in every panel. Pins/order come from
``--sample-colors FILE`` or, automatically, ``<config-dir>/sample_colors.json``
(``--no-config`` skips it); ``--save-sample-colors`` appends the run's names to
its "order". The table goes into FIG.json (``sample_colors``). Image-file
panels (TIFF/PNG/PDF) are placed as they are and never recoloured. No palette
and no pins: nothing changes.

Panels are taken in the given order (reading order, left to right then down)
and labelled (a), (b), (c) ... in 14 pt Arial Bold (default; at final placement
size) outside the top-left corner of each axes box or image frame, at one
constant offset. ``--label-format`` picks the style ((a), a, a), a., (A), A, A),
A.) and ``--label-pt`` the size; without these flags the saved composite config
``<config-dir>/composite.json`` (written by figmenu.py) applies, and without that
the defaults (a) / 14 pt. ``--no-config`` ignores the saved file. Other text keeps
its spec size (12 pt axis/colour-bar labels, 10 pt ticks/legends); a larger label
is absorbed by the top margin, never by shrinking other text.

Layout modes (``--layout``; default: saved composite config, else ``manual``):

* ``manual`` - the Batch 2-4 behaviour: ``--cols`` columns (default 1 at 89 mm,
  2 at 183 mm), rows as needed, explicit label settings honoured.
* ``auto`` - columns x rows are searched deterministically (1, 2, ... columns;
  rows follow from the panel count and spans). Each candidate is qualified with
  the renderer's measured overhangs (pass-1 probe), the minimum box size
  (``--min-box-mm``, 20 mm), the x-label and PL-image label fit, the data-box
  aspect of spanning panels (>= 0.25), the native pixel density (<= ``--max-dpi``),
  imported artwork (effective >= 600 dpi, baked-in text never shrunk), the legend
  cell and the full height (labels, margins, gaps and spans included) <=
  ``--max-height-mm`` (247 mm). The first candidate that passes - fewest columns,
  i.e. the largest panels - is rendered at final size and checked again (render
  checks, final height and the full composite text fit of text_fit.py
  ``composite_fit``); if that fails the next candidate is tried. The grid, every
  candidate's criteria and the selection reason go into ``FIG.json``
  (``auto_layout``). With ``--cols N`` auto only searches N columns.
  Typography is fixed in auto: (a) labels at 14 pt, 12/10 pt for everything else.
  Saved label settings that differ are ignored (recorded in
  ``label.settings_source``); explicit ``--label-format``/``--label-pt`` values
  that differ are an error (use ``--layout manual`` for custom labels).
* No auto candidate fits: a ``WARNING`` names the limiting reason of each
  candidate and suggests 183 mm (``--double-column``) or splitting into two
  figures (at 183 mm: splitting). No TIFF is published, ``FIG.nofit.json``
  records the requested geometry, exit status 4. ``--force`` instead renders the
  fallback - the lowest candidate that fails only the height limit, else the one
  with the fewest failed criteria (then lowest height) - publishes it with
  ``auto_layout.forced = true`` and the failed criteria in its JSON, and exits 0
  when its render checks pass. Text sizes are never changed. Input errors (bad
  panels, spans, legend settings, hash mismatch) and render errors still stop
  the run with a non-zero status, with or without ``--force``.

Spans (``--span ID=row`` or ``--span ID=COLSxROWS``, repeatable, both modes):
the ID is the lowercase input-order letter (a = first panel) whatever the label
format. ``row`` spans the full grid width for one row; ``2x1`` two columns by one
row, ``1x2`` one column by two rows. Panels are packed in reading order: each
starts at the first free cell at or after the previous panel's start, so the
order is preserved and spans never overlap; skipped cells stay empty. A
spanning box runs from the first column's box edge to the last column's box
edge (rows likewise), so edges stay aligned. 05_PL_image keeps its exact square
box and cannot span. ``--span none`` clears saved spans. Errors: malformed or
duplicate spans, IDs without a panel, spans wider than the grid (manual).

Empty cells (``--empty-cells blank|legend``): left white, or one of them holds a
shared legend built from ``--legend-entry 'Label=color[:style]'`` (style solid,
dashed, dotted or dashdot; 1.5 pt samples, 10 pt Arial Bold text, no frame).
``--legend-cell auto`` (default) picks the last empty cell in reading order;
``--legend-cell ROW,COL`` (1-based) names one, which must be empty. A legend with
no free cell, or one that does not fit its cell, is an error in manual mode and a
failed criterion in auto. The legend's text boxes are recorded (``legend``) and
checked by the text-fit tools like any other 10 pt text.

* Data panels (figure basenames such as ``05_PL_image``) are re-rendered through
  the ``make_figures``/``plot_figures`` pipeline at their final placement size
  with the shared style, saved axis overrides and data-fidelity rules. The
  density is raised so the 3536 x 3536 PL image maps 1:1 onto device pixels and
  every heatmap cell spans >= 1.1 px.
* TIFF/PNG panels are placed whole (no crop, no stretch). ``--artwork-scale fit``
  (default) scales each uniformly to the column box width; ``--artwork-scale
  native`` places every imported panel at its own physical size (scale 1.0 for
  all, so baked-in 10/12 pt text stays 10/12 pt). PDF panels are rasterized by
  PyMuPDF straight at the final placement size (>= 600 dpi). A sidecar
  ``<file>.evidence.json`` (renderer record from paper_style.describe_figure)
  is picked up and its text boxes are mapped into the composite for QA.
* Vertical axis and colour-bar labels must fit their box height (12 pt labels):
  ordinary data boxes are made tall enough; a 05 box too small for its labels
  stops the run (use --cols 1 or --double-column).
* Layout: all data boxes share one width; left/top margins are global, right
  margins per column and bottom margins per row, so box edges align along rows
  and columns. Cells are separated by one uniform gap; the outer clearance is
  --clearance-mm. Imported images use their frame edges as the box.

Shared legend (Batch 6, ``--shared-legend`` or ``"shared_legend": true`` in
composite.json): one legend for the whole figure in an empty cell (chosen as
above). Enabling it suppresses every per-panel legend. Entries default to the
panel line handles (label, colour, marker, linestyle; duplicates across panels
merged), so they follow the per-figure legend text overrides. User entries
(``--legend-entry 'Label=color[:style[:marker]]'``) replace them; each count or
style mismatch against the handles is printed as a ``WARNING`` and recorded in
``legend.mismatch_warnings``. The legend size enters the layout measurement and
the text-fit evidence like any other 10 pt text.

Y labels of data panels that start in the same column are aligned to one left
edge (the leftmost natural position) in final composite coordinates; the panels
are rendered separately, so the target is fed back into each panel render and
the result is measured on the composed sheet (``ylabel_alignment``).

A JSON record (``FIG.json``) next to the TIFF documents the layout, measured
alignment, density, clipping checks, resolved positions/spans/empty cells and
per-panel evidence. Exit status: 0 ok, 1 render checks failed, 2 usage/input
error, 4 no auto layout fits (no TIFF written).
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import io
import json
import math
import os
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from PIL import Image, ImageCms, ImageDraw, ImageFont  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

RASTER_SUFFIXES = {".tif", ".tiff", ".png"}
from figure_config import (LABEL_FORMAT_DEFAULT, LABEL_PT_DEFAULT,  # noqa: E402
                           format_panel_label)
LABEL_PT = LABEL_PT_DEFAULT  # panel labels: 14 pt Arial Bold (spec, 2026-11-20 01:53)
LABEL_GAP_MM = 0.5     # between the label and the highest panel artwork
PAD_MM = 1.0           # white pad around each data-panel render (clip detection)
PROBE_MM = 160.0       # probe canvas for overhang measurement
MAX_HEIGHT_MM = 247.0  # Nature full-page height limit for auto layouts
MIN_BOX_MM = 20.0      # smallest auto-layout box (data box or artwork frame) width
MIN_SPAN_ASPECT = 0.25  # spanning data boxes: height/width lower bound in auto
MAX_AUTO_DPI = 2400    # auto: highest density a candidate may need for native pixels/cells
EXIT_NO_FIT = 4
LAST_ERROR = None      # message of the last input/render error from main() (read by figmenu)


class LayoutError(Exception):
    """A grid that cannot be laid out at all (reason in the message)."""


def mm2in(mm):
    return mm / 25.4


def parse_panels(items, figure_names):
    panels = []
    for item in items:
        if item in figure_names:
            panels.append({"kind": "data", "name": item, "spec": item})
            continue
        path, page = item, 0
        if "#" in item and item.lower().split("#")[0].endswith(".pdf"):
            path, page = item.rsplit("#", 1)
            page = int(page) - 1
        p = Path(path)
        if not p.exists():
            raise SystemExit(f"panel {item!r}: not a figure name ({', '.join(figure_names)}) and no such file")
        suffix = p.suffix.lower()
        if suffix in RASTER_SUFFIXES:
            with Image.open(p) as im:
                w, h = im.size
                src_dpi = im.info.get("dpi")
            panels.append({"kind": "raster", "path": str(p), "spec": item, "src_px": [w, h],
                           "src_dpi": [float(v) for v in src_dpi] if src_dpi else None,
                           "aspect": h / w, "evidence_json": evidence_sidecar(p)})
        elif suffix == ".pdf":
            import pymupdf
            with pymupdf.open(p) as doc:
                rect = doc[page].rect
            panels.append({"kind": "pdf", "path": str(p), "page": page + 1, "spec": item,
                           "src_pt": [rect.width, rect.height], "aspect": rect.height / rect.width,
                           "evidence_json": evidence_sidecar(p)})
        else:
            raise SystemExit(f"panel {item!r}: unsupported type {suffix} (use TIFF, PNG or PDF)")
    return panels


def to_rgb_white(im):
    if im.mode in ("RGBA", "LA", "P", "PA") or "transparency" in im.info:
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, im).convert("RGB")
    if im.mode == "CMYK" and im.info.get("icc_profile"):
        src = ImageCms.ImageCmsProfile(io.BytesIO(im.info["icc_profile"]))
        return ImageCms.profileToProfile(im, src, ImageCms.createProfile("sRGB"), outputMode="RGB")
    return im.convert("RGB")


def native_size_in(panel):
    """Physical (w, h) in inches of imported artwork at scale 1.0."""
    if panel["kind"] == "pdf":
        return panel["src_pt"][0] / 72, panel["src_pt"][1] / 72
    if not panel.get("src_dpi"):
        raise SystemExit(f"{panel['spec']}: no DPI tag; native placement needs one (use --artwork-scale fit)")
    return panel["src_px"][0] / panel["src_dpi"][0], panel["src_px"][1] / panel["src_dpi"][1]


def evidence_sidecar(path):
    p = Path(path)
    for cand in (p.with_name(p.name + ".evidence.json"), p.with_suffix(".evidence.json")):
        if cand.exists():
            return str(cand)
    return None


def load_image_panel(panel, box_w, dpi):
    """Return an RGB image exactly box_w px wide, full aspect, no crop."""
    if panel["kind"] == "pdf":
        import pymupdf
        with pymupdf.open(panel["path"]) as doc:
            page = doc[panel["page"] - 1]
            zoom = box_w / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        panel["effective_dpi"] = pix.width / (box_w / dpi)  # rendered px per placed inch
        panel["pdf_zoom_px_per_pt"] = zoom
        panel["rasterized_px"] = [im.width, im.height]
        panel["rasterization"] = "PyMuPDF vector render at final placement size"
    else:
        with Image.open(panel["path"]) as src:
            im = to_rgb_white(src)
            im.load()
        panel["effective_dpi"] = im.width / (box_w / dpi)  # source px per placed inch
        panel["rasterization"] = "imported raster"
    target = (box_w, round(box_w * im.height / im.width))
    if im.size != target:
        resample = "downsampled" if im.width > target[0] else "upsampled"
        panel["resampled"] = f"{resample} {im.size} -> {target} (Lanczos, uniform scale)"
        im = im.resize(target, Image.LANCZOS)
    else:
        panel["resampled"] = "none (1:1)"
    return im


# ------------------------------------------------------------------ settings

def resolve_settings(args, n_panels):
    """Composite settings: explicit CLI > saved composite.json > defaults, per key.

    Spans are one key: any ``--span`` replaces the saved spans (``--span none`` = no
    spans). In auto layout the labels are fixed to (a) / 14 pt (see module doc).
    """
    import figure_config as fc
    saved, source = {}, {}
    cfg_path = fc.composite_config_path(args.config_dir)
    if not args.no_config:
        try:
            saved = fc.load_composite(args.config_dir) or {}
        except (fc.ConfigError, ValueError) as exc:
            raise SystemExit(f"invalid saved composite config {cfg_path}: {exc}")
    try:
        cli_spans = fc.parse_span_items(args.span) if args.span is not None else None
    except fc.ConfigError as exc:
        raise SystemExit(f"--span: {exc}")
    cli = {"label_format": args.label_format, "label_pt": args.label_pt, "layout": args.layout,
           "spans": cli_spans, "empty_cells": args.empty_cells, "legend_cell": args.legend_cell,
           "legend_entries": args.legend_entry, "shared_legend": args.shared_legend}
    merged = {}
    for key in fc.COMPOSITE_KEYS:
        if cli[key] is not None:
            merged[key], source[key] = cli[key], "cli"
        elif key in saved:
            merged[key], source[key] = saved[key], f"config {cfg_path}"
        else:
            merged[key], source[key] = copy.deepcopy(fc.COMPOSITE_DEFAULTS[key]), "default"
    try:
        out = fc.validate_composite(merged, n_panels=n_panels)
    except fc.ConfigError as exc:
        raise SystemExit(f"composite settings: {exc}")
    notes = []
    if out.get("shared_legend"):
        if out["empty_cells"] != "legend":
            notes.append(f"shared legend on: empty_cells {out['empty_cells']!r} -> 'legend'")
        out["empty_cells"], source["empty_cells"] = "legend", f"shared legend ({source['shared_legend']})"
    if out["layout"] == "auto":
        for key, default in (("label_format", fc.LABEL_FORMAT_DEFAULT), ("label_pt", fc.LABEL_PT_DEFAULT)):
            if out[key] == default:
                continue
            if source[key] == "cli":
                raise SystemExit(f"--layout auto fixes panel labels at {fc.LABEL_FORMAT_DEFAULT} / "
                                 f"{fc.LABEL_PT_DEFAULT:g} pt; drop --{key.replace('_', '-')} {out[key]} "
                                 "or use --layout manual for custom labels")
            notes.append(f"{key} {out[key]!r} from {source[key]} ignored: auto layout uses {default!r}")
            out[key], source[key] = default, f"auto layout default ({source[key]} value {out[key]!r} ignored)"
    out["source"] = source
    out["notes"] = notes
    return out


def label_ink_height_in(font_path, pt, texts):
    """Tallest ink height (inches) of the label texts at ``pt``, at least one em."""
    ref = ImageFont.truetype(font_path, 1000)
    tall = max(ref.getbbox(t, anchor="ls")[3] - ref.getbbox(t, anchor="ls")[1] for t in texts) / 1000
    return max(1.0, tall) * pt / 72


# ------------------------------------------------------------------ grid packing

def resolve_spans(spans, panels):
    """{'a': 'row'} -> {0: ('row', 1)}; 05_PL_image cannot span."""
    import figure_config as fc
    out = {}
    for pid, value in (spans or {}).items():
        i = string.ascii_lowercase.index(pid)
        if i >= len(panels):
            raise SystemExit(f"--span {pid}={value}: there is no panel {pid!r} ({len(panels)} panels)")
        cs, rs = fc.parse_span_value(pid, value)
        if panels[i].get("name") == "05_PL_image" and (cs, rs) != (1, 1):
            raise SystemExit(f"--span {pid}={value}: 05_PL_image keeps its exact square box and cannot span")
        out[i] = (cs, rs)
    return out


def pack_grid(n, ncol, spans):
    """Place n panels on an ncol-wide grid in reading order with rectangular spans.

    Each panel starts at the first free cell at or after the previous panel's start
    (row-major), so the order is preserved and spans never overlap. Returns
    (positions [(row, col, cs, rs)], nrow, empty cells [(row, col)]).
    """
    occ, pos, cursor = set(), [], 0
    for i in range(n):
        cs, rs = spans.get(i, (1, 1))
        if cs == "row":
            cs = ncol
        if cs > ncol:
            raise LayoutError(f"span {string.ascii_lowercase[i]}={cs}x{rs} needs {cs} columns; "
                              f"the grid has {ncol}")
        k = cursor
        while True:
            r, c = divmod(k, ncol)
            if c + cs <= ncol and all((r + dr, c + dc) not in occ for dr in range(rs) for dc in range(cs)):
                break
            k += 1
        occ |= {(r + dr, c + dc) for dr in range(rs) for dc in range(cs)}
        pos.append((r, c, cs, rs))
        cursor = k + cs
    nrow = max(r + rs for r, _, _, rs in pos)
    empty = [(r, c) for r in range(nrow) for c in range(ncol) if (r, c) not in occ]
    return pos, nrow, empty


def assign_grid(panels, ncol, spans):
    pos, nrow, empty = pack_grid(len(panels), ncol, spans)
    for p, (r, c, cs, rs) in zip(panels, pos):
        p["row"], p["col"], p["col_span"], p["row_span"] = r, c, cs, rs
    return nrow, empty


def choose_legend_cell(empty, request, ncol, nrow):
    """'auto' = last empty cell in reading order; (R, C) 1-based must be empty."""
    if not empty:
        raise LayoutError(f"no free cell for the legend in the {ncol}x{nrow} grid")
    if request == "auto":
        return empty[-1]
    r, c = (int(v) - 1 for v in request.split(","))
    if (r, c) not in empty:
        raise LayoutError(f"legend cell {request} is not an empty cell of the {ncol}x{nrow} grid "
                          f"(empty: {', '.join(f'{a + 1},{b + 1}' for a, b in empty) or 'none'})")
    return (r, c)


# ------------------------------------------------------------------ legend

def legend_handles(entries):
    """Entries ('Label=color[:style[:marker]]' strings or handle dicts) -> Line2D handles, labels."""
    import figure_config as fc
    import paper_style as ps
    from matplotlib.lines import Line2D
    handles, labels = [], []
    for e in entries:
        d = fc.parse_legend_entry_full(e)
        lw = e.get("linewidth_pt", ps.DATA_LINE_PT) if isinstance(e, dict) else ps.DATA_LINE_PT
        handles.append(Line2D([], [], color=d["color"], linestyle=d["linestyle"], linewidth=lw,
                              marker=None if d["marker"] == "none" else d["marker"]))
        labels.append(d["label"])
    return handles, labels


def panel_handles(panels):
    """Unique plotted line handles of all data panels in reading order (label, colour, style, marker)."""
    out, seen = [], set()
    for p in panels:
        for h in p.get("line_handles") or []:
            key = (h["label"], h["color"].lower(), h["linestyle"], h["marker"])
            if key not in seen:
                seen.add(key)
                out.append(dict(h, panel=p["label"]))
    return out


def legend_mismatches(user, handles):
    """WARNING lines for each count or style mismatch of user entries vs the panel handles."""
    import figure_config as fc
    from matplotlib.colors import to_hex
    out = []
    if len(user) != len(handles):
        out.append(f"WARNING: shared legend: {len(user)} entries supplied but the panels have {len(handles)} "
                   f"line handles ({'; '.join(h['label'] for h in handles) or 'none'})")
    for i, (e, h) in enumerate(zip(user, handles), 1):
        d = fc.parse_legend_entry_full(e)
        for key, a, b in (("colour", to_hex(d["color"]), to_hex(h["color"])), ("linestyle", d["linestyle"], h["linestyle"]),
                          ("marker", d["marker"], h["marker"])):
            if a != b:
                out.append(f"WARNING: shared legend entry {i} {d['label']!r}: {key} {a} differs from the panel "
                           f"handle {h['label']!r} ({key} {b})")
    return out


def draw_legend(entries, w_px, h_px, dpi, x_px, y_px, font):
    """Render the shared legend on a w x h px white canvas with its top-left at (x, y)."""
    import matplotlib.pyplot as plt

    import paper_style as ps
    handles, labels = legend_handles(entries)
    fig = plt.figure(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
    fig.patch.set_facecolor("white")
    leg = fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(x_px / w_px, 1 - y_px / h_px),
                     bbox_transform=fig.transFigure, fontsize=ps.LEGEND_PT, frameon=False,
                     borderaxespad=0.0, borderpad=0.0)
    rgb = ps.render_rgb(fig)
    renderer = fig.canvas.get_renderer()
    H = rgb.shape[0]
    bb = leg.get_window_extent(renderer)
    texts = [ps.describe_text("legend.text", t, font, renderer, H, dpi) for t in leg.get_texts()]
    plt.close(fig)
    return rgb, [float(bb.x0), float(H - bb.y1), float(bb.x1), float(H - bb.y0)], texts


def legend_size_in(entries, dpi, font):
    """Legend extent (w, h) in inches at final size, from a probe render."""
    W = H = int(PROBE_MM / 25.4 * dpi)
    _, bb, _ = draw_legend(entries, W, H, dpi, 0, 0, font)
    return (bb[2] - bb[0]) / dpi, (bb[3] - bb[1]) / dpi


# ------------------------------------------------------------------ geometry

def plan_layout(panels, ncol, nrow, args, env):
    """Grid geometry in device px for the current overhangs. Raises LayoutError."""
    width_mm, native, label_h_in, slack_in = env["width_mm"], env["native"], env["label_h_in"], env["slack_in"]
    clear, gap = mm2in(args.clearance_mm), mm2in(args.gap_mm)
    label_in = label_ink_height_in(env["font_path"], env["label_pt"], [p["label_text"] for p in panels])
    lastc = lambda p: p["col"] + p["col_span"] - 1  # noqa: E731
    lastr = lambda p: p["row"] + p["row_span"] - 1  # noqa: E731
    L = max(p["overhang_in"]["left"] for p in panels)
    T = max(p["overhang_in"]["top"] for p in panels) + label_in + mm2in(LABEL_GAP_MM)
    R = [max((p["overhang_in"]["right"] for p in panels if lastc(p) == c), default=0) for c in range(ncol)]
    B = [max((p["overhang_in"]["bottom"] for p in panels if lastr(p) == r), default=0) for r in range(nrow)]
    W_in = mm2in(width_mm)
    box_w_in = (W_in - 2 * clear - (ncol - 1) * gap - ncol * L - sum(R)) / ncol
    if box_w_in <= 0.3:
        raise LayoutError(f"{ncol} columns do not fit {width_mm:g} mm ({box_w_in * 25.4:.1f} mm boxes); "
                          "use fewer --cols or --double-column")
    cx_in = [clear + sum(L + box_w_in + R[k] for k in range(c)) + c * gap for c in range(ncol)]
    span_w_in = lambda p: cx_in[lastc(p)] - cx_in[p["col"]] + box_w_in  # noqa: E731

    for p in panels:
        if p["kind"] == "data" and p["name"] == "05_PL_image":
            need = max(p["vertical_label_in"].values(), default=0) + slack_in
            if box_w_in < need:
                raise LayoutError(f"05_PL_image: {box_w_in * 25.4:.1f} mm square box is shorter than its "
                                  f"{need * 25.4:.1f} mm labels at the spec type size; use fewer --cols "
                                  "or --double-column")

    def need_h(p):
        if p["kind"] in ("raster", "pdf"):
            return native_size_in(p)[1] if native else span_w_in(p) * p["aspect"]
        if p["name"] == "05_PL_image":
            return box_w_in
        return max(box_w_in * args.box_aspect, label_h_in) if p["row_span"] == 1 else label_h_in

    # Density: >= --dpi; every native image pixel / heatmap cell resolved.
    dpi = float(args.dpi)
    if native:  # never downsample imported rasters placed at scale 1.0
        dpi = max([dpi] + [p["src_dpi"][0] for p in panels if p["kind"] == "raster" and p.get("src_dpi")])
    exact = [p["requirement_px"]["exact_square_px"] for p in panels
             if (p.get("requirement_px") or {}).get("exact_square_px")]
    for p in panels:
        req = p.get("requirement_px")
        if not req or req.get("exact_square_px"):
            continue  # the exact-square (05) requirement is met by the search below
        dpi = max(dpi, req["x_px"] / span_w_in(p), req["y_px"] / need_h(p))
    dpi = float(math.ceil(dpi))
    # Raise the density until the image box is a whole multiple of the native size
    # within ~1 density step of slack (spare px go to the right-hand clearance).
    slack = int(math.ceil(W_in)) + 1
    while True:
        px = lambda v: int(round(v * dpi))  # noqa: E731
        up = lambda v: int(math.ceil(v * dpi)) + 2  # margins round up + 2 px anti-aliasing allowance  # noqa: E731
        Wpx = px(W_in)
        Lp, Tp, Gp, Cp = up(L), up(T), px(gap), px(clear)
        Rp, Bp = [up(v) for v in R], [up(v) for v in B]
        box_w = (Wpx - 2 * Cp - (ncol - 1) * Gp - ncol * Lp - sum(Rp)) // ncol
        if not exact:
            break
        if box_w >= exact[0] and box_w % exact[0] <= slack:
            break
        dpi += 1.0
        if dpi > 20000:
            raise LayoutError("no density up to 20000 dpi places the PL image at whole px per native px")
    if exact:
        if box_w < exact[0]:
            raise LayoutError("internal: density too low for 1:1 image placement")
        # whole device px per native px (k = 1 for the 3536 px project image);
        # spare px go to the right-hand clearance
        box_w = (box_w // exact[0]) * exact[0]
    data_h = max(round(box_w * args.box_aspect), math.ceil(label_h_in * dpi))
    cell_w = [Lp + box_w + Rp[c] for c in range(ncol)]
    cell_x = [Cp + sum(cell_w[:c]) + c * Gp for c in range(ncol)]
    span_w = lambda p: cell_x[lastc(p)] - cell_x[p["col"]] + box_w  # noqa: E731

    def img_w_px(p):
        return int(round(native_size_in(p)[0] * dpi)) if native else span_w(p)

    def need_hpx(p):
        if p["kind"] in ("raster", "pdf"):
            return round(img_w_px(p) * p["aspect"])
        if p["name"] == "05_PL_image":
            return box_w
        return data_h if p["row_span"] == 1 else math.ceil(label_h_in * dpi)

    box_h = [max([need_hpx(p) for p in panels if p["row"] == r and p["row_span"] == 1], default=data_h)
             for r in range(nrow)]

    def rows_y():
        cell_h = [Tp + box_h[r] + Bp[r] for r in range(nrow)]
        return cell_h, [sum(cell_h[:r]) + r * Gp for r in range(nrow)]
    # Multi-row spans: grow the last spanned row until the spanning box fits.
    for p in panels:
        if p["row_span"] > 1:
            cell_h, cy = rows_y()
            rl = lastr(p)
            avail = cy[rl] + box_h[rl] - cy[p["row"]]
            if need_hpx(p) > avail:
                box_h[rl] += need_hpx(p) - avail
    cell_h, cy = rows_y()
    if native:
        for p in panels:
            if p["kind"] != "data" and img_w_px(p) > span_w(p) + Rp[lastc(p)]:
                raise LayoutError(f"{p['spec']}: {img_w_px(p) / dpi * 25.4:.2f} mm artwork does not fit the "
                                  f"{(span_w(p) + Rp[lastc(p)]) / dpi * 25.4:.2f} mm cell at scale 1.0")
    # Panel letters share one baseline offset (= the tallest letter's ink ascent),
    # so every letter sits at the same offset from its box corner. The top canvas
    # clearance is measured to ink: lift the grid by the first row's unused ascent
    # so the top-row letter ink lands at the clearance target.
    lab_font = ImageFont.truetype(env["font_path"], env["label_pt"] / 72 * dpi)  # exact (fractional) em size
    asc = {p["label"]: -lab_font.getbbox(p["label_text"], anchor="ls")[1] for p in panels}
    asc_all = max(asc.values())
    lift = asc_all - max(asc[p["label"]] for p in panels if p["row"] == 0)
    Hpx = 2 * Cp + sum(cell_h) + (nrow - 1) * Gp - lift
    cell_y = [Cp - lift + y for y in cy]
    geo = {}
    for p in panels:
        r, c, rl, cl = p["row"], p["col"], lastr(p), lastc(p)
        x0, y0 = cell_x[c], cell_y[r]
        cw, ch = cell_x[cl] + cell_w[cl] - x0, cell_y[rl] + cell_h[rl] - y0
        g = {"cell": [x0, y0, cw, ch]}
        if p["kind"] == "data":
            if p["name"] == "05_PL_image":
                bw = bh = box_w
            else:
                # Left and top edges align across the grid; an ordinary panel takes the
                # column's spare right margin (reserved for a colour bar elsewhere in the
                # column) so no empty band opens on its right.
                bw = span_w(p) + Rp[cl] - up(p["overhang_in"]["right"])
                bh = cell_y[rl] + Tp + box_h[rl] - (y0 + Tp)
            g.update({"bw": bw, "bh": bh})
        else:
            g.update({"img_w": img_w_px(p)})
        geo[p["index"]] = g
    return {"dpi": dpi, "Wpx": Wpx, "Hpx": Hpx, "Lp": Lp, "Tp": Tp, "Gp": Gp, "Cp": Cp, "Rp": Rp, "Bp": Bp,
            "box_w": box_w, "box_h": box_h, "cell_w": cell_w, "cell_h": cell_h, "cell_x": cell_x,
            "cell_y": cell_y, "asc_all": asc_all, "label_in": label_in, "geo": geo, "exact": exact,
            "height_mm": Hpx / dpi * 25.4, "box_w_mm": box_w / dpi * 25.4, "up": up, "px": px}


def legend_origin(P, cell, size_in):
    """Legend top-left inside its cell: box-aligned (L, T) when it fits, else the cell corner."""
    r, c = cell
    dpi = P["dpi"]
    cw, ch = P["cell_w"][c], P["cell_h"][r]
    lw, lh = (math.ceil(v * dpi) + 2 for v in size_in)
    x = P["Lp"] if P["Lp"] + lw <= cw else 0
    y = P["Tp"] if P["Tp"] + lh <= ch else 0
    return x, y, (lw <= cw and lh <= ch)


def criteria(panels, P, args, env, ncol, nrow, empty, legend_cell):
    """Auto-layout qualification of one planned candidate (dict name -> {pass, value, limit})."""
    dpi = P["dpi"]
    crit = {}
    mm = lambda v: round(v / dpi * 25.4, 2)  # noqa: E731
    widths = []
    for p in panels:
        g = P["geo"][p["index"]]
        widths.append(g.get("bw", g.get("img_w")))
    crit["min_box_width"] = {"pass": min(widths) / dpi * 25.4 >= args.min_box_mm - 1e-9,
                             "value_mm": mm(min(widths)), "limit_mm": args.min_box_mm}
    worst = None
    for p in panels:
        if p["kind"] != "data" or not p.get("horizontal_label_in"):
            continue
        g = P["geo"][p["index"]]
        room = g["bw"] + 2 * P["up"](p["overhang_in"]["right"])
        need = p["horizontal_label_in"] * dpi
        if worst is None or need - room > worst[0]:
            worst = (need - room, p, need, room)
    crit["x_label_fits_cell"] = {"pass": worst is None or worst[0] <= 0,
                                 "value_mm": None if worst is None else mm(worst[2]),
                                 "limit_mm": None if worst is None else mm(worst[3]),
                                 "panel": None if worst is None else worst[1]["label"]}
    asp = [(P["geo"][p["index"]]["bh"] / P["geo"][p["index"]]["bw"], p["label"]) for p in panels
           if p["kind"] == "data" and p["name"] != "05_PL_image" and (p["col_span"] > 1 or p["row_span"] > 1)]
    crit["span_aspect"] = {"pass": all(a >= MIN_SPAN_ASPECT for a, _ in asp),
                           "value": round(min(asp)[0], 3) if asp else None, "limit": MIN_SPAN_ASPECT,
                           "panel": min(asp)[1] if asp else None}
    crit["native_px_density"] = {"pass": dpi <= args.max_dpi, "value_dpi": dpi, "limit_dpi": args.max_dpi}
    art = []
    for p in panels:
        if p["kind"] == "data":
            continue
        g = P["geo"][p["index"]]
        w_in = g["img_w"] / dpi
        if p["kind"] == "raster":
            eff = p["src_px"][0] / w_in
        else:
            eff = float("inf")   # PDFs are rasterized at the placement density
        scale = w_in / native_size_in(p)[0] if (p["kind"] == "pdf" or p.get("src_dpi")) else None
        min_pt = None
        if p.get("evidence_json") and scale:
            ev = json.loads(Path(p["evidence_json"]).read_text())
            sizes = [t["size_pt"] for t in ev.get("texts", [])]
            min_pt = min(sizes) * scale if sizes else None
        art.append({"panel": p["label"], "effective_dpi": None if eff == float("inf") else round(eff, 1),
                    "physical_scale": None if scale is None else round(scale, 4),
                    "min_text_pt_at_placement": None if min_pt is None else round(min_pt, 3),
                    "pass": eff >= args.dpi - 0.5 and (min_pt is None or min_pt >= 10.0 - 0.05)})
    crit["artwork"] = {"pass": all(a["pass"] for a in art), "panels": art}
    if env["legend_entries"] is not None:
        if legend_cell is None:
            crit["legend_cell"] = {"pass": False, "reason": f"no free cell in {ncol}x{nrow}"
                                   if not empty else "requested legend cell is not empty"}
        else:
            _, _, fits = legend_origin(P, legend_cell, env["legend_size_in"])
            crit["legend_cell"] = {"pass": fits, "cell_rc_1based": [legend_cell[0] + 1, legend_cell[1] + 1],
                                   "legend_mm": [round(v * 25.4, 2) for v in env["legend_size_in"]],
                                   "cell_mm": [mm(P["cell_w"][legend_cell[1]]), mm(P["cell_h"][legend_cell[0]])]}
    crit["height"] = {"pass": P["height_mm"] <= args.max_height_mm + 1e-6,
                      "value_mm": round(P["height_mm"], 2), "limit_mm": args.max_height_mm}
    return crit


def reason_of(crit):
    """One-line limiting reason(s) of a candidate."""
    out = []
    for k, v in crit.items():
        if v.get("pass"):
            continue
        if k == "height":
            out.append(f"height {v['value_mm']:.1f} mm > {v['limit_mm']:g} mm")
        elif k == "min_box_width":
            out.append(f"box {v['value_mm']:.1f} mm < {v['limit_mm']:g} mm minimum")
        elif k == "x_label_fits_cell":
            out.append(f"panel {v['panel']} x label {v['value_mm']:.1f} mm > {v['limit_mm']:.1f} mm cell room")
        elif k == "span_aspect":
            out.append(f"spanning panel {v['panel']} aspect {v['value']:.2f} < {v['limit']:g}")
        elif k == "native_px_density":
            out.append(f"native pixels need {v['value_dpi']:g} dpi > {v['limit_dpi']:g}")
        elif k == "artwork":
            out.append("imported artwork: " + ", ".join(f"{a['panel']} (eff. {a['effective_dpi']} dpi, text "
                                                       f"{a['min_text_pt_at_placement']} pt)"
                                                       for a in v["panels"] if not a["pass"]))
        elif k == "legend_cell":
            out.append("legend: " + (v["reason"] if "reason" in v else
                                     f"{v['legend_mm']} mm legend does not fit the {v['cell_mm']} mm cell"))
        elif k == "geometry":
            out.append(v["reason"])
        else:
            out.append(f"{k}: {v.get('reason', 'failed')}")
    return "; ".join(out) or "passes"


# ------------------------------------------------------------------ render

def render_layout(panels, ncol, nrow, empty, legend_cell, args, env, out, work, record):
    """Render, compose and save one grid at final size. Returns (record, render_ok)."""
    import paper_style as ps
    import plot_figures as pf
    font, label_pt, dpi = env["font"], env["label_pt"], None
    work.mkdir(parents=True, exist_ok=True)

    def context(**kw):
        return pf.Context(data=Path(args.data).resolve() if args.data else Path("."), out=work, dpi=ps.MIN_DPI,
                          font=font, width_mm=env["width_mm"] / ncol, use_configs=not args.no_config,
                          config_dir=args.config_dir, write_provenance=False,
                          suppress_legend=bool(env.get("shared_legend")), palette=args.palette,
                          sample_map=env["sample_map"], sample_map_file=env["sample_map_file"],
                          sample_names=env["sample_names"], **kw)

    # Layout, render, then re-measure the real ink overhang at the final box size
    # (tick layout depends on box size); repeat until no panel outgrows its margins.
    # Column y-label alignment: offsets of the y-label left edge from the box left
    # edge (px). natural = measured without a target; ytarget = shared column offset.
    ytarget, natural = {}, {}
    for attempt in range(1, 9):
        rendered, grew = {}, False
        P = plan_layout(panels, ncol, nrow, args, env)
        dpi, Wpx, Hpx = P["dpi"], P["Wpx"], P["Hpx"]
        Lp, Tp, up, px = P["Lp"], P["Tp"], P["up"], P["px"]
        print(f"COMPOSITE: {env['width_mm']:g} mm x {Hpx / dpi * 25.4:.1f} mm, {ncol}x{nrow} grid, {dpi:g} dpi, "
              f"{Wpx}x{Hpx} px, box {P['box_w']} px wide", flush=True)
        pad = px(mm2in(PAD_MM))
        for p in panels:
            g = P["geo"][p["index"]]
            x0, y0, cwid, chgt = g["cell"]
            bx, by = x0 + Lp, y0 + Tp
            p["cell_px"] = [x0, y0, cwid, chgt]
            if p["kind"] == "data":
                name = p["name"]
                bw, bh = g["bw"], g["bh"]
                cw, ch = cwid + 2 * pad, chgt + 2 * pad
                # forced box (left, bottom, width, height) in the padded panel canvas;
                # boxes are top-aligned in the row.
                forced = (pad + Lp, pad + chgt - Tp - bh, bw, bh)
                ctx = context(only={name}, force_dpi=dpi, forced_box_px={name: forced},
                              height_override_mm=ch / dpi * 25.4)
                if p["index"] in ytarget:   # box-relative offset -> padded panel-canvas px
                    ctx.ylabel_left_px = {name: pad + Lp + ytarget[p["index"]]}
                ctx.width_mm = cw / dpi * 25.4
                ctx.out = work / f"{p['label']}_{name}"
                pf.render_all(ctx)
                tif = ctx.out / f"{name}.tiff"
                rec = json.loads((ctx.qa / f"{name}.style.json").read_text())
                with Image.open(tif) as im:
                    arr = np.asarray(im.convert("RGB"))
                assert arr.shape[:2] == (ch, cw), (arr.shape, ch, cw)
                ink = ps.edge_clearance_px(arr)
                p["clip_check"] = {"ink_clearance_in_padded_canvas_px": ink,
                                   "inside_cell": all(v >= pad for v in ink.values())}
                rendered[p["index"]] = arr[pad:pad + ch - 2 * pad, pad:pad + cw - 2 * pad]
                ix0, iy0, ix1, iy1 = ps.ink_bbox(arr)
                mbx = rec["main_axes"]["box_px"]
                actual = {"left": (mbx["x0"] - ix0) / dpi, "right": (ix1 + 1 - mbx["x1"]) / dpi,
                          "top": (mbx["top"] - iy0) / dpi, "bottom": (iy1 + 1 - mbx["bottom"]) / dpi}
                # Renderer text boxes (incl. side bearings) must also stay inside the cell crop.
                for t in rec["texts"]:
                    tx0, ty0, tx1, ty1 = t["bbox_px"]
                    actual["left"] = max(actual["left"], (mbx["x0"] - tx0) / dpi)
                    actual["right"] = max(actual["right"], (tx1 - mbx["x1"]) / dpi)
                    actual["top"] = max(actual["top"], (mbx["top"] - ty0) / dpi)
                    actual["bottom"] = max(actual["bottom"], (ty1 - mbx["bottom"]) / dpi)
                for side, v in actual.items():
                    # The reserved margin already carries a 2 px allowance; only a real
                    # overrun re-lays out, adding a 0.2 mm safety so the loop converges.
                    if v > p["overhang_in"][side] + 1.5 / dpi:
                        p["overhang_in"][side] = v + mm2in(0.2)
                        grew = True
                del arr
                mb = rec["main_axes"]["box_px"]
                p["box_px"] = [x0 + mb["x0"] - pad, y0 + mb["top"] - pad, mb["width"], mb["height"]]
                p["render"] = {"tiff": str(tif), "style_json": str(ctx.qa / f"{name}.style.json"),
                               "dpi": rec["dpi"], "layout": rec["layout"],
                               "axis_overrides": rec.get("axis_overrides", {})}
                p["pad_px"] = pad
                p["render_origin_px"] = [x0 - pad, y0 - pad]   # panel render (0,0) in composite px
                p["crop_px"] = [x0, y0, x0 + cwid, y0 + chgt]
                yl = [t["bbox_px"] for t in rec["texts"] if t["role"] == "axes.ylabel"]
                p["ylabel_x0_px"] = yl[0][0] + x0 - pad if yl else None
                p["label_fit"] = rec["layout"].get("label_fit")
                p.setdefault("warnings", [])
                p["warnings"] = [w for w in ctx.warnings]
            else:
                im = load_image_panel(p, g["img_w"], dpi)
                rendered[p["index"]] = im
                p["box_px"] = [bx, by, im.width, im.height]
                p["placed_px"] = [im.width, im.height]
                p["crop_px"] = [bx, by, bx + im.width, by + im.height]
                src_w_in = native_size_in(p)[0] if (p["kind"] == "pdf" or p.get("src_dpi")) else None
                p["placement"] = {"offset_px": [bx, by],
                                  "physical_scale": (im.width / dpi) / src_w_in if src_w_in else None,
                                  "mode": args.artwork_scale}
                p["placed_mm"] = [im.width / dpi * 25.4, im.height / dpi * 25.4]
                p["aspect_error"] = abs(im.height / im.width - p["aspect"]) / p["aspect"]
            print(f"PANEL {p['label']}: {p['spec']} box {[round(v, 1) for v in p['box_px']]}", flush=True)
        # Column y-label alignment in final composite px: every data panel starting in
        # a column takes the leftmost natural y-label edge of that column.
        realign = False
        for p in panels:
            if p["kind"] == "data" and p.get("ylabel_x0_px") is not None and p["index"] not in ytarget:
                natural[p["index"]] = p["ylabel_x0_px"] - p["box_px"][0]
        for c in range(ncol):
            col = [p for p in panels if p["kind"] == "data" and p["col"] == c and p.get("ylabel_x0_px") is not None]
            if len(col) < 2:
                continue
            tgt = min(natural[p["index"]] for p in col if p["index"] in natural)
            for p in col:
                off = p["ylabel_x0_px"] - p["box_px"][0]
                if abs(off - tgt) > 0.5:
                    if abs(ytarget.get(p["index"], 1e9) - tgt) > 0.01:   # new or changed target
                        realign = True
                    ytarget[p["index"]] = tgt
                elif p["index"] in ytarget:
                    ytarget[p["index"]] = tgt
        print(f"LAYOUT attempt {attempt}: {'margins grew, re-laying out' if grew else 'y labels re-aligned' if realign else 'converged'}",
              flush=True)
        if not grew and not realign:
            break
    else:
        raise SystemExit("layout did not converge")
    sheet = Image.new("RGB", (Wpx, Hpx), "white")
    for p in panels:
        im = rendered.pop(p["index"])
        if isinstance(im, np.ndarray):
            sheet.paste(Image.fromarray(im), tuple(p["cell_px"][:2]))
        else:
            sheet.paste(im, tuple(int(v) for v in p["box_px"][:2]))
        del im

    # Shared legend in its empty cell (10 pt Arial Bold, 1.5 pt samples).
    legend_rec = None
    if legend_cell is not None:
        r, c = legend_cell
        lx0, ly0, lw, lh = P["cell_x"][c], P["cell_y"][r], P["cell_w"][c], P["cell_h"][r]
        ox, oy, fits = legend_origin(P, legend_cell, env["legend_size_in"])
        if not fits:
            raise SystemExit(f"legend ({[round(v * 25.4, 1) for v in env['legend_size_in']]} mm) does not fit "
                             f"cell {r + 1},{c + 1} ({lw / dpi * 25.4:.1f} x {lh / dpi * 25.4:.1f} mm)")
        rgb, bb, texts = draw_legend(env["legend_entries"], lw, lh, dpi, ox, oy, font)
        sheet.paste(Image.fromarray(rgb), (lx0, ly0))
        for t in texts:
            b = t["bbox_px"]
            t["bbox_px"] = [b[0] + lx0, b[1] + ly0, b[2] + lx0, b[3] + ly0]
        cell = [lx0, ly0, lx0 + lw, ly0 + lh]
        bbox = [bb[0] + lx0, bb[1] + ly0, bb[2] + lx0, bb[3] + ly0]
        inside = all(t["bbox_px"][0] >= cell[0] and t["bbox_px"][1] >= cell[1] and t["bbox_px"][2] <= cell[2]
                     and t["bbox_px"][3] <= cell[3] for t in texts)
        legend_rec = {"cell_rc": [r, c], "cell_rc_1based": [r + 1, c + 1], "cell_px": cell,
                      "shared_legend": bool(env.get("shared_legend")), "entries_source": env.get("legend_source"),
                      "panel_handles": env.get("panel_handles"), "mismatch_warnings": env.get("legend_warnings", []),
                      "size_mm": [round(v * 25.4, 2) for v in env["legend_size_in"]],
                      "selected_by": env["legend_cell_request"], "bbox_px": bbox,
                      "entries": env["legend_entries"], "font_pt": ps.LEGEND_PT,
                      "sample_line_pt": ps.DATA_LINE_PT, "texts": texts, "inside_cell": inside,
                      "text_sizes_pt": sorted({t["size_pt"] for t in texts}),
                      "all_glyphs_arial_bold": all(t["all_glyphs_in_resolved_face"] for t in texts)}

    # Labels: Arial Bold (a), (b) ... outside the top-left corner of each box at one offset.
    font_px = label_pt / 72 * dpi   # exact em size in device px (Pillow accepts fractional sizes)
    pil_font = ImageFont.truetype(font.path, font_px)
    draw = ImageDraw.Draw(sheet)
    asc_all = P["asc_all"]
    for p in panels:
        x0, y0 = p["cell_px"][:2]
        draw.text((x0, y0 + asc_all), p["label_text"], font=pil_font, fill=(0, 0, 0), anchor="ls")
        bb = draw.textbbox((x0, y0 + asc_all), p["label_text"], font=pil_font, anchor="ls")
        p["label_px"] = {"anchor_xy": [x0, y0], "bbox": list(bb), "text": p["label_text"],
                         "font_px": pil_font.size, "actual_pt": pil_font.size / dpi * 72, "baseline_xy": [x0, y0 + asc_all],
                         "offset_from_box_corner_mm": [(p["box_px"][0] - x0) / dpi * 25.4,
                                                       (p["box_px"][1] - y0) / dpi * 25.4]}
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi), icc_profile=ps.srgb_icc_bytes())
    rgb = np.asarray(sheet)
    canvas_clear = ps.edge_clearance_px(rgb)
    del sheet, rgb

    # Measured alignment and gaps.
    cell_x, cell_y, cell_w, cell_h = P["cell_x"], P["cell_y"], P["cell_w"], P["cell_h"]
    lastr = lambda p: p["row"] + p["row_span"] - 1  # noqa: E731
    rows = {r: [p for p in panels if p["row"] == r] for r in range(nrow)}
    cols = {c: [p for p in panels if p["col"] == c] for c in range(ncol)}
    spread = lambda vals: float(max(vals) - min(vals)) if vals else 0.0  # noqa: E731
    align = {"row_box_top_spread_px": {r: spread([p["box_px"][1] for p in ps_]) for r, ps_ in rows.items()},
             "col_box_left_spread_px": {c: spread([p["box_px"][0] for p in ps_]) for c, ps_ in cols.items()},
             "row_box_bottom_spread_px_data_only": {
                 r: spread([p["box_px"][1] + p["box_px"][3] for p in panels if lastr(p) == r
                            and p["kind"] == "data" and p["name"] != "05_PL_image"]) for r in range(nrow)},
             "box_width_px": sorted({round(p["box_px"][2], 1) for p in panels}),
             "label_offsets_mm": sorted({tuple(round(v, 3) for v in p["label_px"]["offset_from_box_corner_mm"])
                                         for p in panels}),
             "horizontal_cell_gaps_px": [cell_x[c + 1] - (cell_x[c] + cell_w[c]) for c in range(ncol - 1)],
             "vertical_cell_gaps_px": [cell_y[r + 1] - (cell_y[r] + cell_h[r]) for r in range(nrow - 1)]}
    ycols = {}
    for c in range(ncol):
        col = [p for p in panels if p["kind"] == "data" and p["col"] == c and p.get("ylabel_x0_px") is not None]
        if col:
            xs = {p["label"]: round(p["ylabel_x0_px"], 2) for p in col}
            ycols[c] = {"ylabel_x0_px": xs, "spread_px": round(max(xs.values()) - min(xs.values()), 2),
                        "spread_mm": round((max(xs.values()) - min(xs.values())) / dpi * 25.4, 3)}
    align["ylabel_alignment_per_column"] = ycols
    gaps = align["horizontal_cell_gaps_px"] + align["vertical_cell_gaps_px"]
    checks = {
        "boxes_aligned_rows_cols": all(v <= 1 for v in align["row_box_top_spread_px"].values())
        and all(v <= 1 for v in align["col_box_left_spread_px"].values()),
        "uniform_gaps": len(set(gaps)) <= 1,
        "ylabels_aligned_per_column": all(v["spread_px"] <= 1.0 for v in ycols.values()),
        "one_label_offset": len(align["label_offsets_mm"]) == 1,
        "no_clipping": all(p.get("clip_check", {"inside_cell": True})["inside_cell"] for p in panels),
        "aspect_preserved": all(p.get("aspect_error", 0) < 0.01 for p in panels),
        "artwork_uniform_scale": len({round(p["placement"]["physical_scale"], 3) for p in panels
                                      if p["kind"] != "data" and p["placement"]["physical_scale"]}) <= 1,
        "pdf_effective_dpi_ge_600": all(p["effective_dpi"] >= 600 for p in panels if p["kind"] == "pdf"),
        "pl_image_whole_px_per_native_px": all(
            round(p["box_px"][2]) % p["requirement_px"]["exact_square_px"] == 0
            and round(p["box_px"][2]) == round(p["box_px"][3])
            for p in panels if p["kind"] == "data" and p["name"] == "05_PL_image"),
    }
    if any(p["col_span"] > 1 or p["row_span"] > 1 for p in panels):
        # Spans: no two panel cells overlap and every spanning box ends on the grid lines.
        cells = [p["cell_px"] for p in panels]
        checks["spans_no_overlap"] = not any(
            min(a[0] + a[2], b[0] + b[2]) > max(a[0], b[0]) and min(a[1] + a[3], b[1] + b[3]) > max(a[1], b[1])
            for i, a in enumerate(cells) for b in cells[i + 1:])
    if legend_rec is not None:
        checks["legend_inside_cell"] = legend_rec["inside_cell"]
        checks["legend_text_10pt_arial_bold"] = (legend_rec["text_sizes_pt"] == [ps.LEGEND_PT]
                                                  and legend_rec["all_glyphs_arial_bold"])
    for p in panels:
        p.pop("style_record", None)
    label_cfg = env["settings"]
    record.update({"out": str(out), "width_mm": env["width_mm"], "height_mm": Hpx / dpi * 25.4, "dpi": dpi,
                   "canvas_px": [Wpx, Hpx], "grid": [ncol, nrow], "gap_mm": args.gap_mm,
                   "clearance_mm": args.clearance_mm, "canvas_ink_clearance_mm":
                       {k: v / dpi * 25.4 for k, v in canvas_clear.items()},
                   "label": {"text_pt": label_pt, "format": label_cfg["label_format"],
                             "settings_source": {k: label_cfg["source"][k] for k in ("label_format", "label_pt")},
                             "font": font.path,
                             "font_family": pil_font.getname()[0], "font_style": pil_font.getname()[1],
                             "truetype_px": pil_font.size, "actual_pt": pil_font.size / dpi * 72, "weight": "bold",
                             "texts": [p["label_text"] for p in panels],
                             "ink_height_mm": P["label_in"] * 25.4},
                   "box_px": {"width": P["box_w"], "row_heights": P["box_h"], "left_margin": Lp, "top_margin": Tp,
                              "right_margins": P["Rp"], "bottom_margins": P["Bp"]},
                   "spans": dict(label_cfg["spans"]),
                   "positions": [{"panel": p["label"], "label": p["label_text"], "spec": p["spec"],
                                  "row": p["row"], "col": p["col"], "col_span": p["col_span"],
                                  "row_span": p["row_span"], "cell_px": p["cell_px"]} for p in panels],
                   "empty_cells": {"use": label_cfg["empty_cells"], "cells_rc": [list(e) for e in empty],
                                   "cells_rc_1based": [[e[0] + 1, e[1] + 1] for e in empty],
                                   "legend_cell_rc": list(legend_cell) if legend_cell else None,
                                   "blank_cells_rc": [list(e) for e in empty if e != legend_cell]},
                   "legend": legend_rec,
                   "colorbar_gap_pt": ps.COLORBAR_GAP_PT, "colorbar_labelpad_pt": ps.COLORBAR_LABELPAD_PT,
                   "label_warnings": [w for p in panels for w in p.get("warnings", [])],
                   "height_le_max_mm": {"limit_mm": args.max_height_mm,
                                        "pass": Hpx / dpi * 25.4 <= args.max_height_mm + 1e-6},
                   "alignment": align, "checks": checks, "panels": panels})
    if env["data_names"]:
        import make_figures as mf
        after, _ = mf.verify_sources(args.data, args.manifest, pf.INPUT_FILES)
        record["sources_unchanged"] = after == record["source_sha256"]
    out.with_suffix(".json").write_text(json.dumps(record, indent=2, default=str, ensure_ascii=False))
    return record, all(checks.values())


def text_fit_module():
    try:
        import text_fit as tf            # kit name
    except ImportError:
        import text_fit_batch3 as tf     # project name
    return tf


# ------------------------------------------------------------------ build

def build(args):
    import make_figures as mf
    import paper_style as ps
    import plot_figures as pf

    panels = parse_panels(args.panels, pf.FIGURE_NAMES)
    if len(panels) > 26:
        raise SystemExit("at most 26 panels can be labelled")
    data_names = [p["name"] for p in panels if p["kind"] == "data"]
    font = ps.resolve_font(args.font, args.font_substitute)
    ps.apply_style(font)
    record = {"tool": "make_composite.py", "created": dt.datetime.now().isoformat(timespec="seconds"),
              "command": [Path(sys.executable).name, Path(__file__).name, *args._argv], "font": font.as_dict()}
    settings = resolve_settings(args, len(panels))
    for note in settings["notes"]:
        print(f"NOTE: {note}", flush=True)
    label_pt = settings["label_pt"]
    spans = resolve_spans(settings["spans"], panels)
    use_legend = settings["empty_cells"] == "legend"
    shared = bool(settings.get("shared_legend"))
    if use_legend and settings["legend_entries"]:
        try:
            legend_handles(settings["legend_entries"])
        except Exception as exc:
            raise SystemExit(f"legend entries: {exc}")
    if data_names:
        if not args.data:
            raise SystemExit("--data is required for data panels")
        before, problems = mf.verify_sources(args.data, args.manifest, pf.INPUT_FILES)
        if problems:
            raise SystemExit(f"SOURCE VERIFICATION FAILED: {problems}")
        record["source_sha256"] = before
    # Same sample name, same colour: collect every data panel's names (panel
    # order, then legend order) before any colour is assigned.
    import figure_config as _fc
    import sample_colors as sc
    try:
        sample_map, sample_file, sample_save = sc.cli_map(args.sample_colors, _fc.config_dir(args.config_dir).resolve(),
                                                          args.no_config)
    except sc.SampleColorError as exc:
        raise SystemExit(f"sample colours: {exc}")
    names_ctx = pf.Context(data=Path(args.data).resolve() if args.data else Path("."), out=Path(args.out).resolve().parent,
                           dpi=ps.MIN_DPI, font=font, use_configs=not args.no_config, config_dir=args.config_dir,
                           palette=args.palette, sample_map=sample_map, sample_map_file=sample_file)
    sample_names = pf.collect_series_names(names_ctx, data_names)
    names_ctx.sample_names = sample_names
    by_panel, palettes_used, sample_warn = {}, set(), []
    for i, p in enumerate(panels):
        if p["kind"] != "data":
            continue
        labels = pf.series_names(names_ctx, p["name"])
        r = pf.resolve_sample_colors(names_ctx, p["name"], labels)
        if r is not None:
            palettes_used.add(r["palette"])
            by_panel[string.ascii_lowercase[i]] = {"figure": p["name"], "palette": r["palette"],
                                                   "series_names": labels, "table": r["table"]}
            sample_warn += [w for w in r["warnings"] if w not in sample_warn]
    if len(palettes_used) > 1:
        w = (f"WARNING: sample colours: data panels name different palettes ({', '.join(sorted(map(str, palettes_used)))}); "
             f"a name can only share its colour across panels that use the same palette")
        print(w, flush=True)
        print(w, file=sys.stderr, flush=True)
        sample_warn.append(w)
    record["sample_colors"] = {
        "active": bool(by_panel), "map_file": str(sample_file) if sample_file else None,
        "pins": sample_map["pins"], "order": sample_map["order"], "session_palette": args.palette,
        "names_in_order": sample_names, "by_panel": by_panel, "warnings": sample_warn,
        "image_panels": "not recoloured (TIFF/PNG/PDF artwork is placed as supplied)",
        "match_rule": "exact after stripping surrounding whitespace; no case folding"}
    if args.save_sample_colors:
        path, order = sc.save_order(sample_save, sample_names)
        print(f"SAMPLE COLORS SAVED: {path} order={order}", flush=True)
    width_mm = ps.DOUBLE_COLUMN_MM if args.double_column else ps.SINGLE_COLUMN_MM
    for i, p in enumerate(panels):
        p["index"] = i
        p["label"] = string.ascii_lowercase[i]          # reading-order key (a, b, c ...)
        p["label_text"] = format_panel_label(settings["label_format"], i)   # rendered text, e.g. (a)
    out = Path(args.out).resolve()
    work = out.parent / (out.stem + "_panels")
    work.mkdir(parents=True, exist_ok=True)

    # Pass 1: measure ink overhang beyond the data box for every data panel.
    if data_names:
        # Large probe canvas so no overhang is clipped by the canvas edge; text and
        # tick sizes are in points, so the overhang does not depend on box size.
        ctx = pf.Context(data=Path(args.data).resolve(), out=work, dpi=ps.MIN_DPI, font=font,
                         width_mm=PROBE_MM, use_configs=not args.no_config, config_dir=args.config_dir,
                         write_provenance=False, only=set(data_names), measure=True,
                         height_override_mm=PROBE_MM, suppress_legend=shared, palette=args.palette,
                         sample_map=sample_map, sample_map_file=sample_file, sample_names=sample_names)
        for d in (ctx.out, ctx.qa, ctx.source):
            d.mkdir(parents=True, exist_ok=True)
        for action in pf.DRAWERS:
            action(ctx)
        for p in panels:
            if p["kind"] == "data":
                m = ctx.measurements[p["name"]]
                p["overhang_in"] = m["overhang_in"]
                p["requirement_px"] = m["requirement_px"]
                p["vertical_label_in"] = m.get("vertical_label_in", {})
                p["horizontal_label_in"] = m.get("horizontal_label_in", 0.0)
                p["line_handles"] = m.get("line_handles", [])
    for p in panels:
        p.setdefault("overhang_in", {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0})
    handles = panel_handles(panels)
    legend_entries, legend_source, legend_warnings = settings["legend_entries"], "legend_entries", []
    if shared:
        if settings["legend_entries"]:
            legend_warnings = legend_mismatches(settings["legend_entries"], handles)
            legend_source = "user legend_entries (compared against the panel line handles)"
        else:
            if not handles:
                raise SystemExit("shared legend: the panels have no labelled line handles; "
                                 "supply --legend-entry 'Label=color[:style[:marker]]'")
            legend_entries = [{k: h[k] for k in ("label", "color", "linestyle", "marker", "linewidth_pt")}
                              for h in handles]
            legend_source = "panel line handles"
        for w in legend_warnings:
            print(w, flush=True)
            print(w, file=sys.stderr, flush=True)
    slack_in = mm2in(ps.LABEL_BOX_SLACK_MM)
    env = {"width_mm": width_mm, "native": args.artwork_scale == "native", "slack_in": slack_in,
           # Ordinary data boxes must be at least as tall as their longest vertical label.
           "label_h_in": max([max(p["vertical_label_in"].values(), default=0) + slack_in for p in panels
                              if p["kind"] == "data" and p["name"] != "05_PL_image"], default=0.0),
           "font": font, "font_path": font.path, "label_pt": label_pt, "settings": settings,
           "sample_map": sample_map, "sample_map_file": sample_file, "sample_names": sample_names,
           "data_names": data_names, "legend_entries": legend_entries if use_legend else None,
           "shared_legend": shared, "legend_source": legend_source if use_legend else None,
           "panel_handles": handles, "legend_warnings": legend_warnings,
           "legend_cell_request": settings["legend_cell"],
           "legend_size_in": legend_size_in(legend_entries, ps.MIN_DPI, font) if use_legend else None}
    record["layout_settings"] = {k: settings[k] for k in ("layout", "spans", "empty_cells", "legend_cell",
                                                          "legend_entries", "shared_legend")}
    record["legend_warnings"] = legend_warnings
    record["layout_settings"]["source"] = {k: v for k, v in settings["source"].items()}
    record["layout_settings"]["notes"] = settings["notes"]

    if settings["layout"] == "manual":
        ncol = args.cols if args.cols is not None else (2 if args.double_column else 1)
        ncol = max(1, min(ncol, len(panels)))
        try:
            nrow, empty = assign_grid(panels, ncol, spans)
            legend_cell = choose_legend_cell(empty, settings["legend_cell"], ncol, nrow) if use_legend else None
            plan_layout(panels, ncol, nrow, args, env)   # surfaces geometry errors before rendering
        except LayoutError as exc:
            raise SystemExit(str(exc))
        record["auto_layout"] = None
        try:
            record, ok = render_layout(panels, ncol, nrow, empty, legend_cell, args, env, out, work, record)
        except LayoutError as exc:
            # The measured final-size overhang (for example a label longer than its
            # span) leaves no room for the boxes: report it, never shrink the text.
            raise SystemExit(f"{exc} (after re-measuring the final-size panels"
                             f"{'; ' + ' | '.join(w for p in panels for w in p.get('warnings', [])) if any(p.get('warnings') for p in panels) else ''})")
        H = record["height_mm"]
        print(f"{'PASS' if ok else 'FAIL'} {out} {width_mm:g} x {H:.2f} mm @ {record['dpi']:g} dpi; "
              f"checks {record['checks']}", flush=True)
        return 0 if ok else 1
    return build_auto(panels, spans, use_legend, args, env, out, work, record)


def build_auto(panels, spans, use_legend, args, env, out, work, record):
    width_mm = env["width_mm"]
    n = len(panels)
    col_range = [args.cols] if args.cols is not None else list(range(1, n + 1))
    cands = []
    for ncol in col_range:
        ps_ = copy.deepcopy(panels)
        cand = {"grid": None, "cols": ncol, "planned_height_mm": None, "criteria": {}, "precheck_pass": False}
        try:
            nrow, empty = assign_grid(ps_, ncol, spans)
            cand["grid"] = [ncol, nrow]
            cand["positions"] = [[p["row"], p["col"], p["col_span"], p["row_span"]] for p in ps_]
            cand["empty_cells_rc"] = [list(e) for e in empty]
            legend_cell = None
            if use_legend:
                try:
                    legend_cell = choose_legend_cell(empty, env["legend_cell_request"], ncol, nrow)
                except LayoutError:
                    legend_cell = None
            P = plan_layout(ps_, ncol, nrow, args, env)
            cand["planned_height_mm"] = round(P["height_mm"], 2)
            cand["planned_dpi"] = P["dpi"]
            cand["criteria"] = criteria(ps_, P, args, env, ncol, nrow, empty, legend_cell)
            cand["precheck_pass"] = all(v["pass"] for v in cand["criteria"].values())
            cand["_state"] = (ps_, nrow, empty, legend_cell)
        except LayoutError as exc:
            cand["criteria"] = {"geometry": {"pass": False, "reason": str(exc)}}
        cand["reason"] = reason_of(cand["criteria"])
        print(f"AUTO candidate {ncol} col{'s' if ncol > 1 else ''}"
              f"{' x %d rows' % cand['grid'][1] if cand['grid'] else ''}: "
              f"{'pre-check PASS' if cand['precheck_pass'] else 'FAIL'}"
              f"{' (%.1f mm planned)' % cand['planned_height_mm'] if cand['planned_height_mm'] else ''}"
              f" - {cand['reason']}", flush=True)
        cands.append(cand)

    tf = text_fit_module()
    auto = {"mode": "auto", "max_height_mm": args.max_height_mm, "min_box_mm": args.min_box_mm,
            "max_dpi": args.max_dpi, "search": "columns ascending (fewest columns = largest panels); "
                                               "rows from panel count and spans",
            "cols_constraint": args.cols, "candidates": cands, "selected_grid": None,
            "selection_reason": None, "forced": False, "failed_criteria": []}

    def finalize(cand, forced=False):
        ps_, nrow, empty, legend_cell = cand.pop("_state")
        ncol = cand["cols"]
        sub = work / f"auto_{ncol}x{nrow}"
        tmp = sub / f"candidate_{ncol}x{nrow}.tiff"
        rec, render_ok = render_layout(copy.deepcopy(ps_), ncol, nrow, empty, legend_cell, args, env, tmp, sub,
                                       dict(record))
        fit = tf.composite_fit(tmp)
        final = {"height_mm": round(rec["height_mm"], 3), "render_checks_pass": render_ok,
                 "height_pass": rec["height_le_max_mm"]["pass"], "text_fit_pass": fit["pass"],
                 "text_fit": {k: fit[k] for k in ("text_collisions", "tick_collisions", "text_in_data_box",
                                                  "clipped_canvas", "clipped_crop", "label_vs_artwork",
                                                  "edge_clearance_mm")}}
        cand["final"] = final
        return tmp, rec, final

    def publish(tmp, rec, cand, reason, forced=False, failed=()):
        auto.update({"selected_grid": cand["grid"], "selection_reason": reason, "forced": forced,
                     "failed_criteria": list(failed)})
        rec["auto_layout"] = auto
        rec["out"] = str(out)
        for c in auto["candidates"]:
            c.pop("_state", None)
        os.replace(tmp, out)
        out.with_suffix(".json").write_text(json.dumps(rec, indent=2, default=str, ensure_ascii=False))
        tmp.with_suffix(".json").rename(tmp.with_suffix(".json.published"))

    tried = []
    for cand in [c for c in cands if c["precheck_pass"]]:
        try:
            tmp, rec, final = finalize(cand)
        except LayoutError as exc:
            cand["reason"] = f"final-size layout failed: {exc}"
            cand["final"] = {"height_mm": None, "render_checks_pass": False, "height_pass": False,
                             "text_fit_pass": False, "error": str(exc)}
            tried.append(cand)
            print(f"AUTO candidate {cand['grid'][0]}x{cand['grid'][1]} rejected after render: {cand['reason']}",
                  flush=True)
            continue
        if final["render_checks_pass"] and final["height_pass"] and final["text_fit_pass"]:
            earlier = [f"{c['grid'][0] if c['grid'] else c['cols']}x{c['grid'][1] if c['grid'] else '?'}: "
                       f"{c['reason'] if not c.get('final') else 'final-size check failed'}"
                       for c in cands if c is not cand and (c["cols"] < cand["cols"])]
            reason = (f"{cand['grid'][0]}x{cand['grid'][1]} is the first candidate (fewest columns) passing all "
                      f"criteria and the final-size render/text-fit checks at {rec['height_mm']:.1f} mm <= "
                      f"{args.max_height_mm:g} mm" + (f"; rejected: {'; '.join(earlier)}" if earlier else ""))
            publish(tmp, rec, cand, reason)
            print(f"AUTO selected {cand['grid'][0]}x{cand['grid'][1]}: {reason}", flush=True)
            print(f"PASS {out} {width_mm:g} x {rec['height_mm']:.2f} mm @ {rec['dpi']:g} dpi; "
                  f"checks {rec['checks']}", flush=True)
            return 0
        fails = [k for k, ok in (("render_checks", final["render_checks_pass"]), ("height", final["height_pass"]),
                                 ("text_fit", final["text_fit_pass"])) if not ok]
        cand["reason"] = f"final-size check failed: {', '.join(fails)} ({final['height_mm']:.1f} mm)"
        tmp.rename(tmp.with_name(tmp.stem + ".rejected.tiff"))
        tried.append(cand)
        print(f"AUTO candidate {cand['grid'][0]}x{cand['grid'][1]} rejected after render: {cand['reason']}",
              flush=True)

    # No candidate fits.
    limiting = "; ".join(f"{c['grid'][0]}x{c['grid'][1]}" if c["grid"] else f"{c['cols']} cols" for c in cands)
    details = " | ".join(f"{(str(c['grid'][0]) + 'x' + str(c['grid'][1])) if c['grid'] else str(c['cols']) + ' cols'}"
                         f": {c['reason']}" for c in cands)
    suggestion = ("split the panels into two figures" if args.double_column
                  else "use 183 mm (--double-column) or split the panels into two figures")
    warning = (f"WARNING: no auto layout fits {width_mm:g} mm for {n} panels"
               f"{' with spans ' + ', '.join(f'{k}={v}' for k, v in env['settings']['spans'].items()) if spans else ''}"
               f" (height limit {args.max_height_mm:g} mm, tried {limiting}). Limiting: {details}. "
               f"Suggestion: {suggestion}.")
    print(warning, flush=True)
    print(warning, file=sys.stderr, flush=True)
    nofit = {"tool": "make_composite.py", "created": record["created"], "command": record["command"],
             "requested": {"width_mm": width_mm, "n_panels": n, "panels": [p["spec"] for p in panels],
                           "spans": env["settings"]["spans"], "cols": args.cols,
                           "empty_cells": env["settings"]["empty_cells"],
                           "max_height_mm": args.max_height_mm},
             "warning": warning, "suggestion": suggestion, "forced": bool(args.force), "auto_layout": auto}
    if not args.force:
        for c in cands:
            c.pop("_state", None)
        out.with_suffix(".nofit.json").write_text(json.dumps(nofit, indent=2, default=str, ensure_ascii=False))
        print(f"NO FIT: no TIFF written; record {out.with_suffix('.nofit.json')} (exit {EXIT_NO_FIT}; "
              "--force renders the fallback)", flush=True)
        return EXIT_NO_FIT
    # --force: fallback = lowest candidate failing only on height, else fewest failed criteria, then height.
    plannable = [c for c in cands if c["planned_height_mm"] is not None]
    if not plannable:
        for c in cands:
            c.pop("_state", None)
        out.with_suffix(".nofit.json").write_text(json.dumps(nofit, indent=2, default=str, ensure_ascii=False))
        print("FORCE: no candidate can be laid out at all; nothing to render", flush=True)
        return EXIT_NO_FIT

    def failed_of(c):
        f = [k for k, v in c["criteria"].items() if not v["pass"]]
        if c.get("final"):
            f += [f"final_{k}" for k in ("render_checks_pass", "height_pass", "text_fit_pass") if not c["final"][k]]
        return f
    only_h = [c for c in plannable if set(failed_of(c)) <= {"height", "final_height_pass"}]
    pool = only_h or plannable
    fb = min(pool, key=lambda c: (len(failed_of(c)), c["planned_height_mm"], c["cols"]))
    if "_state" not in fb:   # rendered and rejected earlier: re-plan from the measured state
        ps_ = copy.deepcopy(panels)
        nrow, empty = assign_grid(ps_, fb["cols"], spans)
        lc = choose_legend_cell(empty, env["legend_cell_request"], fb["cols"], nrow) if use_legend else None
        fb["_state"] = (ps_, nrow, empty, lc)
    failed = failed_of(fb)
    if fb["_state"][3] is None and use_legend:
        print("FORCE: the fallback grid has no free legend cell; the legend is left out", flush=True)
        env = dict(env, legend_entries=None)
    try:
        tmp, rec, final = finalize(fb, forced=True)
    except LayoutError as exc:
        raise SystemExit(f"--force fallback {fb['grid'][0]}x{fb['grid'][1]} cannot be laid out: {exc}")
    failed = sorted(set(failed + [f"final_{k}" for k in ("render_checks_pass", "height_pass", "text_fit_pass")
                                  if not final[k]]))
    reason = (f"FORCED fallback {fb['grid'][0]}x{fb['grid'][1]} ({'fails only the height limit' if only_h else 'fewest failed criteria'}"
              f", then lowest height) after: {warning}")
    publish(tmp, rec, fb, reason, forced=True, failed=failed)
    print(f"WARNING: FORCED output {out} {width_mm:g} x {rec['height_mm']:.2f} mm, failed criteria: "
          f"{', '.join(failed)}; text sizes unchanged", flush=True)
    return 0 if final["render_checks_pass"] else 1


def main(argv=None):
    import figure_config as fc
    import paper_style as ps
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panels", nargs="+", required=True,
                    help="ordered panels: figure basenames (data) and/or TIFF/PNG/PDF paths (PDF page: file.pdf#2)")
    ap.add_argument("--out", required=True, type=Path, help="output TIFF path")
    ap.add_argument("--data", type=Path, default=None, help="raw-data directory (needed for data panels)")
    ap.add_argument("--manifest", type=Path, default=HERE / "qa" / "data_manifest.json",
                    help="reference SHA-256 manifest for --data")
    ap.add_argument("--double-column", action="store_true", help="183 mm wide (default 89 mm)")
    ap.add_argument("--cols", type=int, default=None,
                    help="manual: panels per row (default 1 at 89 mm, 2 at 183 mm: 12 pt labels need the width); "
                         "auto: restrict the search to this column count")
    ap.add_argument("--layout", choices=fc.LAYOUT_MODES, default=None,
                    help=f"grid selection (default: saved composite config, else {fc.LAYOUT_DEFAULT})")
    ap.add_argument("--span", action="append", default=None, metavar="ID=row|COLSxROWS",
                    help="panel span by input-order id (a, b ...), repeatable: a=row, b=2x1, c=1x2; "
                         "'none' clears saved spans")
    ap.add_argument("--empty-cells", choices=fc.EMPTY_CELL_USES, default=None,
                    help="empty grid cells: blank (default) or one shared legend")
    ap.add_argument("--legend-entry", action="append", default=None, metavar="'Label=color[:style[:marker]]'",
                    help="shared legend entry (repeatable; style solid|dashed|dotted|dashdot; marker none|o|s|^...)")
    ap.add_argument("--shared-legend", dest="shared_legend", action="store_true", default=None,
                    help="one shared legend in an empty cell; suppresses per-panel legends; entries default "
                         "to the panel line handles")
    ap.add_argument("--no-shared-legend", dest="shared_legend", action="store_false",
                    help="per-panel legends (overrides a saved shared_legend)")
    ap.add_argument("--legend-cell", default=None,
                    help="legend cell: auto (last empty cell in reading order) or ROW,COL (1-based)")
    ap.add_argument("--force", action="store_true",
                    help="auto: when no layout fits, render and publish the documented fallback (marked forced)")
    ap.add_argument("--max-height-mm", type=float, default=MAX_HEIGHT_MM, help="auto: height limit (247 mm)")
    ap.add_argument("--min-box-mm", type=float, default=MIN_BOX_MM, help="auto: smallest box width (20 mm)")
    ap.add_argument("--max-dpi", type=float, default=MAX_AUTO_DPI,
                    help="auto: highest density a candidate may need for native pixels/cells (2400)")
    ap.add_argument("--gap-mm", type=float, default=3.0, help="uniform gap between panel cells")
    ap.add_argument("--clearance-mm", type=float, default=ps.DEFAULT_CLEARANCE_MM)
    ap.add_argument("--dpi", type=int, default=600, help="minimum density (raised for native pixels/cells)")
    ap.add_argument("--box-aspect", type=float, default=0.68,
                    help="minimum height/width of ordinary data boxes (raised to fit 12 pt vertical labels)")
    ap.add_argument("--artwork-scale", choices=("fit", "native"), default="fit",
                    help="imported TIFF/PNG/PDF: 'fit' = uniform scale to the box width; 'native' = every "
                         "panel at its own physical size (scale 1.0, keeps baked-in type sizes)")
    ap.add_argument("--config-dir", type=Path, default=None, help="axis override directory (as make_figures.py)")
    ap.add_argument("--no-config", action="store_true",
                    help="ignore saved axis overrides and the saved composite.json")
    ap.add_argument("--label-format", default=None, choices=fc.LABEL_FORMATS,
                    help=f"panel label style (default: saved composite config, else {LABEL_FORMAT_DEFAULT})")
    ap.add_argument("--label-pt", type=float, default=None,
                    help=f"panel label size in pt at final size (default: saved composite config, else "
                         f"{LABEL_PT_DEFAULT:g}; {fc.LABEL_PT_RANGE[0]:g}-{fc.LABEL_PT_RANGE[1]:g})")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--font-substitute", default=None)
    ap.add_argument("--palette", default=None,
                    help="series palette id for the data panels (a figure config 'palette' key wins)")
    ap.add_argument("--sample-colors", type=Path, default=None, metavar="FILE",
                    help="pins/order JSON for name-based colours (default: <config-dir>/sample_colors.json "
                         "when it exists; --no-config skips it)")
    ap.add_argument("--save-sample-colors", action="store_true",
                    help="append this run's series names to the map's 'order' (pins untouched)")
    args = ap.parse_args(argv)
    if args.palette is not None:
        import palettes
        try:
            args.palette = palettes.validate_name(args.palette)
        except palettes.PaletteError as exc:
            ap.error(str(exc))
    args._argv = [str(a) for a in (argv if argv is not None else sys.argv[1:])]
    if args.label_pt is not None and not fc.LABEL_PT_RANGE[0] <= args.label_pt <= fc.LABEL_PT_RANGE[1]:
        ap.error(f"--label-pt must lie in {fc.LABEL_PT_RANGE[0]:g}-{fc.LABEL_PT_RANGE[1]:g}")
    if args.dpi < ps.MIN_DPI:
        ap.error(f"--dpi must be >= {ps.MIN_DPI}")
    if args.out.suffix.lower() not in (".tif", ".tiff"):
        ap.error("--out must be a .tiff file")
    if args.cols is not None and args.cols < 1:
        ap.error("--cols must be >= 1")
    if args.legend_cell is not None:
        try:
            fc.parse_legend_cell(args.legend_cell)
        except fc.ConfigError as exc:
            ap.error(str(exc))
    if args.legend_entry is not None:
        try:
            for e in args.legend_entry:
                fc.parse_legend_entry(e)
        except fc.ConfigError as exc:
            ap.error(str(exc))
    global LAST_ERROR
    LAST_ERROR = None
    try:
        return build(args)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            LAST_ERROR = exc.code
            print(f"ERROR: {exc.code}", file=sys.stderr, flush=True)
            return 2
        raise


if __name__ == "__main__":
    sys.exit(main())
