"""Scientific content for the ten figures (reads raw data, writes provenance).

讀檔 → 驗證資料 → 作圖 → 交給 paper_style 排版與匯出 TIFF → 記錄來源。
所有原始檔只讀。未做平滑、基線校正、重新正規化、擬合或刪除觀測。
樣式全部來自 paper.mplstyle / paper_style.py；此檔不再覆寫字級、線寬或版面。
The pre-tool reference version is kept in versions/pre_tiff_tool/plot_figures.py.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xlrd
from matplotlib.ticker import FixedLocator, FuncFormatter, Locator, LogLocator, MaxNLocator, NullFormatter

import figure_config as fc
import paper_style as ps

BLUE, ORANGE = "#2166AC", "#B35806"
PL_IMAGE_SHAPE = (3536, 3536)  # project data; other square images are accepted
TPC_DECAY_WINDOW_US = (0.0, 10.0)

INPUT_FILES = ["IR.csv", "XRD.xls", "TPC 1.txt", "TPC 2.txt", "PL_Image_Data.CSV", "in situ PL.xlsx"]
FIGURE_NAMES = [
    "01_IR", "02_XRD", "03_TPC_overlay", "04_TPC_overlay_logtime", "05_PL_image",
    "06_in_situ_PL_heatmap", "07_in_situ_PL_mean_spectrum", "08_in_situ_PL_normalized_global",
    "09_in_situ_PL_normalized_per_scan", "10_in_situ_PL_normalized_mean_spectrum",
]
SPECTRUM_FIGURES = {"01_IR", "02_XRD", "03_TPC_overlay", "04_TPC_overlay_logtime",
                    "07_in_situ_PL_mean_spectrum", "10_in_situ_PL_normalized_mean_spectrum"}


@dataclass
class Context:
    data: Path
    out: Path
    dpi: int
    font: ps.FontInfo
    clearance_mm: float = ps.DEFAULT_CLEARANCE_MM
    width_mm: float = ps.SINGLE_COLUMN_MM
    only: set | None = None          # restrict to these figure basenames (None = all ten)
    records: list = field(default_factory=list)
    empty_sheets: list = field(default_factory=list)
    # Axis overrides (figure_config): saved per-figure JSON is loaded from
    # config_dir unless use_configs is False; ``overrides`` (name -> cfg) wins.
    use_configs: bool = True
    config_dir: Path | None = None
    overrides: dict = field(default_factory=dict)
    applied_configs: dict = field(default_factory=dict)
    # Composite support: fixed canvas height, one forced density, forced data
    # boxes {name: (left, bottom, width, height) px}, or measure-only mode.
    height_override_mm: float | None = None
    force_dpi: float | None = None
    forced_box_px: dict = field(default_factory=dict)
    measure: bool = False
    measurements: dict = field(default_factory=dict)
    write_provenance: bool = True
    # Batch 6: composite shared legend suppresses the per-panel legends; y-label
    # alignment target {name: left edge x in panel-canvas px}; label-fit warnings.
    suppress_legend: bool = False
    ylabel_left_px: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def height_mm(self):
        if self.height_override_mm:
            return self.height_override_mm
        return ps.DEFAULT_HEIGHT_MM.get(self.width_mm, 60.0)

    def config_for(self, name):
        if name in self.overrides:
            return self.overrides[name]
        if not self.use_configs:
            return None
        return fc.load(name, self.config_dir)

    def wants(self, *names):
        return self.only is None or any(n in self.only for n in names)

    @property
    def qa(self):
        return self.out / "qa"

    @property
    def source(self):
        return self.out / "source_data"


def check_array(name, values):
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError(f"{name}: empty or non-finite data; repair source explicitly")


def store(ctx, name, **arrays):
    for key, value in arrays.items():
        check_array(f"{name}/{key}", np.asarray(value))
    if ctx.write_provenance:
        np.savez_compressed(ctx.source / f"{name}.npz", **arrays)


_CACHE = {}


def cached(path, loader):
    """Load a raw input once per process (keyed by path, size and mtime)."""
    st = Path(path).stat()
    key = (str(path), st.st_size, st.st_mtime_ns, loader.__name__)
    if key not in _CACHE:
        _CACHE[key] = loader(path)
    return _CACHE[key]


def _load_pl_csv(path):
    return np.loadtxt(path, delimiter=",")


def _load_in_situ(path):
    book = pd.ExcelFile(path, engine="openpyxl")
    return [(sheet, pd.read_excel(book, sheet_name=sheet, header=None)) for sheet in book.sheet_names]


def new_plot(ctx, height_mm=None, dpi=None):
    if ctx.height_override_mm:
        height_mm = ctx.height_override_mm
    fig, ax = ps.new_figure(dpi or ctx.force_dpi or ctx.dpi, ctx.width_mm, height_mm or ctx.height_mm)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, min_n_ticks=3, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, min_n_ticks=3, steps=[1, 2, 5, 10]))
    return fig, ax


def apply_config(ctx, name, fig, ax, cb=None):
    """Apply saved/explicit overrides (axes, labels, ...); returns the applied settings.

    Labels always come from figure_config (defaults + overrides), so this runs for
    every figure, also without a saved config.
    """
    cfg = ctx.config_for(name)
    applied = fc.apply(name, cfg, fig, ax, cb)
    ctx.applied_configs[name] = applied
    _wrap_start_tick(ax)
    return applied


class StartTickLocator(Locator):
    """Major ticks of ``base`` with the starting value always shown as the first tick."""

    def __init__(self, start, base):
        self.start, self.base = float(start), base

    def set_axis(self, axis):
        super().set_axis(axis)
        self.base.set_axis(axis)

    def __call__(self):
        vmin, vmax = self.axis.get_view_interval()
        return self.tick_values(vmin, vmax)

    def tick_values(self, vmin, vmax):
        lo, hi = sorted((vmin, vmax))
        t = [v for v in self.base.tick_values(vmin, vmax) if lo <= v <= hi]
        step = (t[1] - t[0]) if len(t) > 1 else (hi - lo)
        if not any(abs(v - self.start) < 1e-9 * max(1.0, abs(step)) for v in t):
            t = [self.start] + [v for v in t if v - self.start > 0.5 * step]
        return np.asarray(t)


def _wrap_start_tick(ax):
    start = getattr(ax, "_paper_start_tick", None)
    loc = ax.xaxis.get_major_locator()
    if start is not None and not isinstance(loc, StartTickLocator):
        ax.xaxis.set_major_locator(StartTickLocator(start, loc))


def line_handles(ax):
    """Plotted line handles (label, colour, marker, linestyle, width) of labelled lines."""
    names = {"-": "solid", "--": "dashed", ":": "dotted", "-.": "dashdot"}
    out = []
    for line in ax.get_lines():
        lab = line.get_label()
        if not lab or lab.startswith("_"):
            continue
        out.append({"label": lab, "color": line.get_color(),
                    "linestyle": names.get(line.get_linestyle(), str(line.get_linestyle())),
                    "marker": "none" if line.get_marker() in (None, "None", "none", "", " ") else str(line.get_marker()),
                    "linewidth_pt": float(line.get_linewidth())})
    return out


def label_fit(fig, ax, cax, name):
    """Final rendered label length vs its available span (data box side).

    x label: data box width; y label: data box height; colour-bar label: bar
    length. Returns records; ``fits`` False means the label overruns its span.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    out = []
    pairs = [("x", ax.xaxis.label, ax.get_window_extent(r).width, "width"),
             ("y", ax.yaxis.label, ax.get_window_extent(r).height, "height")]
    if cax is not None and cax.get_visible():
        vertical = getattr(cax, "_paper_location", "right") == "right"
        lab = (cax.yaxis if vertical else cax.xaxis).label
        cb = cax.get_window_extent(r)
        pairs.append(("colorbar", lab, cb.height if vertical else cb.width, "height" if vertical else "width"))
    for axis, lab, avail, attr in pairs:
        if not (lab.get_visible() and lab.get_text()):
            continue
        length = getattr(lab.get_window_extent(r), attr)
        out.append({"axis": axis, "text": lab.get_text(), "length_mm": round(length / fig.dpi * 25.4, 2),
                    "available_mm": round(avail / fig.dpi * 25.4, 2), "fits": bool(length <= avail + 0.5),
                    "size_pt": float(lab.get_fontsize())})
    return out


def warn_label_fit(ctx, name, fits):
    for f in fits:
        if not f["fits"]:
            msg = (f"WARNING: label too long: {name} {f['axis']} label {f['text']!r} is {f['length_mm']:.1f} mm, "
                   f"longer than its {f['available_mm']:.1f} mm available span; font kept at {f['size_pt']:g} pt "
                   "(shorten the label or widen the panel)")
            ctx.warnings.append(msg)
            print(msg, flush=True)


def align_ylabel(fig, ax, target_x0_px, rounds=3):
    """Move the y label so its left ink-box edge sits at ``target_x0_px`` (canvas px)."""
    lab = ax.yaxis.label
    if not (lab.get_visible() and lab.get_text()):
        return None
    for _ in range(rounds):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        bb = lab.get_window_extent(r)
        dx = target_x0_px - bb.x0
        if abs(dx) < 0.25:
            break
        ax_bb = ax.get_window_extent(r)
        anchor = lab.get_transform().transform(lab.get_position())
        ax.yaxis.set_label_coords((anchor[0] + dx - ax_bb.x0) / ax_bb.width,
                                  (anchor[1] - ax_bb.y0) / ax_bb.height)
    fig.canvas.draw()
    return float(lab.get_window_extent(fig.canvas.get_renderer()).x0)


def save_figure(ctx, fig, name, evidence, cax=None, fixed_side_px=None, raster=None, cb=None,
                configured=False, requirement=None):
    ax = fig.axes[0]
    if not configured:
        apply_config(ctx, name, fig, ax, cb)
    if cax is not None and not cax.get_visible():
        cax = None
    if ctx.measure:
        # Composite pass 1: ink overhang beyond the data box (inches; size-independent).
        ctx.measurements[name] = {"overhang_in": ps.square_box_extents_in(fig, ax, cax),
                                  "vertical_label_in": ps.vertical_label_lengths_in(fig, ax, cax),
                                  # x-axis label length (inches) for the auto-layout cell-width check
                                  "horizontal_label_in": (ax.xaxis.label.get_window_extent(
                                      fig.canvas.get_renderer()).width / fig.dpi
                                      if ax.xaxis.label.get_visible() and ax.xaxis.label.get_text() else 0.0),
                                  "requirement_px": requirement, "kind": "data",
                                  "line_handles": line_handles(ax),
                                  "label_fit": label_fit(fig, ax, cax, name)}
        plt.close(fig)
        return
    if name in ctx.forced_box_px:
        left, bottom, width, height = ctx.forced_box_px[name]
        ps._place(fig, ax, cax, left, bottom, width, height)
        ps.close_spine_corners(ax)
        gaps = ps.edge_clearance_px(ps.render_rgb(fig))
        layout = {"forced_box_px": [left, bottom, width, height], "clearance_px": gaps,
                  "clearance_mm": {k: v / fig.dpi * 25.4 for k, v in gaps.items()}}
    else:
        layout = ps.fit_layout(fig, ax, cax=cax, clearance_mm=ctx.clearance_mm,
                               fixed_side_px=fixed_side_px)
    user_steps = {a for a, v in ctx.applied_configs.get(name, {}).items()
                  if a in ("x", "y") and "major_step" in v}
    thinned = ps.thin_ticks(ax, skip=user_steps)
    _wrap_start_tick(ax)
    if thinned:
        if name not in ctx.forced_box_px:
            layout = ps.fit_layout(fig, ax, cax=cax, clearance_mm=ctx.clearance_mm,
                                   fixed_side_px=fixed_side_px)
        else:
            ps.close_spine_corners(ax)
        layout["tick_thinning"] = thinned
    if ax.get_legend() is not None:
        # Legend inside the data box: keep it off the traces at the final box size.
        legend_info = ps.place_legend_clear(ax)
        if legend_info and "headroom_fraction" in legend_info:
            # y limits changed: close the spine corners again and, for fitted
            # layouts, refit the margins to the new tick labels.
            if name not in ctx.forced_box_px:
                legend_loc = legend_info["loc"]
                layout = ps.fit_layout(fig, ax, cax=cax, clearance_mm=ctx.clearance_mm,
                                       fixed_side_px=fixed_side_px)
                ax.get_legend().set_loc(legend_loc)
            ps.close_spine_corners(ax)
            fig.canvas.draw()
        layout["legend"] = legend_info
    if name in ctx.ylabel_left_px:
        # Composite column alignment: shared y-label left edge (canvas px from the left).
        layout["ylabel_aligned_x0_px"] = align_ylabel(fig, ax, ctx.ylabel_left_px[name])
        layout["ylabel_target_x0_px"] = ctx.ylabel_left_px[name]
    fits = label_fit(fig, ax, cax, name)
    warn_label_fit(ctx, name, fits)
    layout["label_fit"] = fits
    layout["colorbar_gap_pt"] = ps.COLORBAR_GAP_PT if cax is not None else None
    hidden = [a for a, axis in (("x", ax.xaxis), ("y", ax.yaxis)) if getattr(axis, "_paper_hide_offset", False)]
    if hidden:
        fig.canvas.draw()
        layout["tick_numbers_hidden"] = {
            a: {"offset_text": axis.offsetText.get_text(), "offset_visible": bool(axis.offsetText.get_visible()),
                "tick_labels_visible": sum(t.label1.get_visible() for t in axis.get_major_ticks()),
                "tick_marks_visible": sum(t.tick1line.get_visible() for t in axis.get_major_ticks()),
                "label_visible": bool(axis.label.get_visible())}
            for a, axis in (("x", ax.xaxis), ("y", ax.yaxis)) if a in hidden}
    path = ctx.out / f"{name}.tiff"
    ps.export_tiff(fig, path)
    record = ps.describe_figure(fig, ctx.font, "spectrum" if name in SPECTRUM_FIGURES else "map")
    record.update({"figure": name, "tiff": path.name, "layout": layout, "raster": raster,
                   "target_mm": list(fig._paper_target_mm), "evidence": evidence,
                   "axis_overrides": ctx.applied_configs.get(name, {}),
                   "native_requirement_px": requirement})
    (ctx.qa / f"{name}.style.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    plt.close(fig)
    evidence = dict(evidence)
    evidence["figure"] = name
    evidence["dpi"] = float(fig.dpi)
    evidence["target_mm"] = list(fig._paper_target_mm)
    evidence["excluded_observations"] = 0
    evidence["error_bars"] = "none: no replicate uncertainty supplied"
    evidence["axis_overrides"] = ctx.applied_configs.get(name, {})
    ctx.records.append(evidence)
    print(f"EXPORTED {name}.tiff  dpi={fig.dpi:g}  clearance_mm="
          + ", ".join(f"{k}={v:.2f}" for k, v in layout["clearance_mm"].items()), flush=True)


# ------------------------------------------------------------------- figures

def draw_ir(ctx):
    if not ctx.wants("01_IR"):
        return
    a = np.loadtxt(ctx.data / "IR.csv", delimiter=",", skiprows=2, encoding="utf-8-sig")
    check_array("IR", a)
    assert a.ndim == 2 and a.shape[1] == 2
    store(ctx, "IR", wavenumber_cm_minus_1=a[:, 0], transmittance_percent=a[:, 1])
    fig, ax = new_plot(ctx)
    ax.plot(a[:, 0], a[:, 1], color=BLUE, linewidth=ps.DATA_LINE_PT)
    lo, hi = float(a[:, 0].min()), float(a[:, 0].max())
    pad = 0.02 * (hi - lo)  # spec: ~2% of the full data span at each end
    ax.set_xlim(hi + pad, lo - pad)
    save_figure(ctx, fig, "01_IR", {"source": "IR.csv", "rows_plotted": len(a),
                                    "transform": "none; descending wavenumber axis",
                                    "data_x_range_cm_minus_1": [lo, hi],
                                    "x_padding_fraction_per_end": 0.02,
                                    "display_xlim": [hi + pad, lo - pad]})


def draw_xrd(ctx):
    if not ctx.wants("02_XRD"):
        return
    # 這是舊版 BIFF2 Excel。顯式用 xlrd 避免自動偵測誤判。
    book = xlrd.open_workbook(ctx.data / "XRD.xls")
    sheet = book.sheet_by_index(0)
    a = np.array([sheet.row_values(i) for i in range(sheet.nrows)], dtype=float)
    check_array("XRD", a)
    assert a.shape[1] == 2
    store(ctx, "XRD", column_1=a[:, 0], column_2=a[:, 1])
    fig, ax = new_plot(ctx)
    ax.plot(a[:, 0], a[:, 1], color=BLUE, linewidth=ps.DATA_LINE_PT)
    ax.set_xlim(a[:, 0].min(), a[:, 0].max())
    save_figure(ctx, fig, "02_XRD", {"source": "XRD.xls", "rows_plotted": len(a), "transform": "none",
                                     "assumption": "column 1 = 2theta degrees; source has no headers; intensity unit unspecified"})


def _decade_label(value, _pos):
    if value <= 0:
        return ""
    exponent = math.log10(value)
    if abs(exponent - round(exponent)) > 1e-9:
        return ""
    # Halfwidth hyphen as the exponent sign, set as a true superscript.
    return rf"10$^{{\text{{{int(round(exponent))}}}}}$"


def draw_tpc(ctx):
    if not ctx.wants("03_TPC_overlay", "04_TPC_overlay_logtime"):
        return
    curves = []
    for name, sample in (("TPC 1.txt", "D1-1"), ("TPC 2.txt", "D2-1")):
        a = np.loadtxt(ctx.data / name, comments="#")
        check_array(name, a)
        assert a.shape[1] == 2
        # 來源寫明 Time (us)、Normalized Current (1)，直接使用，不再次正規化。
        store(ctx, Path(name).stem.replace(" ", "_"), time_us=a[:, 0], normalized_current=a[:, 1])
        curves.append((a, f"{Path(name).stem} ({sample})"))
    for logtime, suffix in ((False, "03_TPC_overlay"), (True, "04_TPC_overlay_logtime")):
        if not ctx.wants(suffix):
            continue
        fig, ax = new_plot(ctx)
        # Legend text: defaults or per-figure overrides (figure_config "legend").
        names = fc.legend_labels(suffix, ctx.config_for(suffix))
        # Spec B2: 04 uses dark orange #B35806 and the contrasting blue #2166AC with
        # distinct line styles (solid / dashed) so the traces separate in grayscale.
        for (a, _), label, color, linestyle in zip(curves, names, (BLUE, ORANGE), ("-", "--")):
            if logtime and not (a[:, 0] > 0).all():
                raise ValueError("Log time requires strictly positive time values")
            ax.plot(a[:, 0], a[:, 1], color=color, linestyle=linestyle, label=label,
                    linewidth=ps.DATA_LINE_PT)
        if logtime:
            ax.set_xscale("log")
            ax.xaxis.set_major_locator(LogLocator(base=10, numticks=12))
            ax.xaxis.set_major_formatter(FuncFormatter(_decade_label))
            ax.xaxis.set_minor_formatter(NullFormatter())
        full_t = [min(a[:, 0].min() for a, _ in curves), max(a[:, 0].max() for a, _ in curves)]
        extra = {}
        if logtime:
            ax.set_xlim(*full_t)
        else:
            # Decay-region view (spec 03): both traces fall below 10% of peak by
            # ~3 us; the 0-10 us window shows the full decay and the onset of the
            # tail. All rows are still plotted and kept in source_data.
            ax.set_xlim(*TPC_DECAY_WINDOW_US)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10]))
            inside = [a[(a[:, 0] >= TPC_DECAY_WINDOW_US[0]) & (a[:, 0] <= TPC_DECAY_WINDOW_US[1])]
                      for a, _ in curves]
            extra = {"display_xlim_us": list(TPC_DECAY_WINDOW_US), "full_time_range_us": full_t,
                     "rows_inside_display_window": [len(v) for v in inside],
                     "display_window_rule": "decay region: 0-10 us (both traces < 10% of peak after ~3 us)"}
        if not ctx.suppress_legend:   # composite shared legend replaces the panel legend
            ax.legend(loc="upper right", handlelength=2.0)  # placement re-checked in save_figure
        save_figure(ctx, fig, suffix, {"sources": ["TPC 1.txt", "TPC 2.txt"],
                                       "rows_plotted": [len(a) for a, _ in curves],
                                       "transform": "log time axis only" if logtime else
                                       "none; linear axis cropped to decay region for display only",
                                       "line_styles": ["solid", "dashed"],
                                       "legend_labels": names, "panel_legend": not ctx.suppress_legend,
                                       "colors": [BLUE, ORANGE],
                                       "renormalized": False, **extra})


def _pl_decorate(fig, ax, image_shape, vmin, vmax, data=None):
    if data is None:
        data = np.zeros((8, 8))
    # origin upper 保留矩陣第一列在上方；沒有翻轉、裁切或百分位截斷。
    im = ax.imshow(data, origin="upper", cmap="viridis", interpolation="none", resample=False,
                   vmin=vmin, vmax=vmax, aspect="equal",
                   extent=(-0.5, image_shape[1] - 0.5, image_shape[0] - 0.5, -0.5))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4, min_n_ticks=3, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, min_n_ticks=3, steps=[1, 2, 5, 10]))
    cb = ps.add_colorbar(fig, ax, im, fc.label_for("05_PL_image", "cbar_label"), location="right")
    cb.locator = MaxNLocator(nbins=6, steps=[1, 2, 5, 10])
    cb.update_ticks()
    return im, cb


def pl_image_geometry(ctx, vmin, vmax, shape=PL_IMAGE_SHAPE):
    """Square data side, density and canvas height for 05 (vertical colour bar at right).

    The width is the column width. The overhang of labels, ticks and the colour
    bar is measured on a probe render; the square side takes all remaining
    width, the density maps one native pixel to one device pixel, and the
    height is the square plus the measured bottom/top overhang and clearances.
    """
    fig, ax = ps.new_figure(ps.MIN_DPI, ctx.width_mm, ctx.width_mm)
    _, cb = _pl_decorate(fig, ax, shape, vmin, vmax)
    apply_config(ctx, "05_PL_image", fig, ax, cb)
    ext = ps.square_box_extents_in(fig, ax, cb.ax if cb.ax.get_visible() else None)
    plt.close(fig)
    clear_in = ps.mm_to_in(ctx.clearance_mm)
    side_in = ps.mm_to_in(ctx.width_mm) - ext["left"] - ext["right"] - 2 * clear_in
    n = shape[1]
    base = max(ctx.dpi, math.ceil(n / side_in))
    # k whole device pixels per native pixel (k = 1 for the 3536 px project image).
    # The density is then set so the k*n px square fills the available side (no
    # empty band at the right); it never drops below the base density.
    k = max(1, int(side_in * base // n))
    dpi = math.ceil(k * n / side_in)
    if dpi < base:
        k += 1
        dpi = math.ceil(k * n / side_in)
    side_px = k * n
    height_in = side_px / dpi + ext["top"] + ext["bottom"] + 2 * clear_in
    height_mm = math.ceil(height_in * 25.4 * 10) / 10  # round up to 0.1 mm
    return {"dpi": dpi, "side_px": side_px, "device_pixels_per_source_pixel": k,
            "side_mm": side_px / dpi * 25.4,
            "height_mm": height_mm, "overhang_mm": {k: v * 25.4 for k, v in ext.items()}}


def pl_image_side_in(ctx):
    """Backward-compatible helper: available square side (in) for the PL image."""
    geo = pl_image_geometry(ctx, 0.0, 1.0)
    return geo["side_px"] / geo["dpi"]


def draw_pl_image(ctx):
    if not ctx.wants("05_PL_image"):
        return
    image = cached(ctx.data / "PL_Image_Data.CSV", _load_pl_csv)
    check_array("PL image", image)
    assert image.ndim == 2 and image.shape[0] == image.shape[1], "PL image must be a square array"
    store(ctx, "PL_image", intensity=image)
    vmin, vmax = float(image.min()), float(image.max())
    requirement = {"x_px": image.shape[1], "y_px": image.shape[0], "exact_square_px": image.shape[1]}
    if ctx.measure or "05_PL_image" in ctx.forced_box_px:
        # Composite: the composite tool fixes the box (exactly 3536 px) and density.
        geo = {"composite_forced": True}
        fig, ax = new_plot(ctx, dpi=ctx.force_dpi or ps.MIN_DPI)
    else:
        geo = pl_image_geometry(ctx, vmin, vmax, image.shape)
        fig, ax = new_plot(ctx, height_mm=geo["height_mm"], dpi=geo["dpi"])
    _, cb = _pl_decorate(fig, ax, image.shape, vmin, vmax, data=image)
    apply_config(ctx, "05_PL_image", fig, ax, cb)
    save_figure(ctx, fig, "05_PL_image",
                {"source": "PL_Image_Data.CSV", "shape": list(image.shape), "pixels_plotted": int(image.size),
                 "transform": "linear full min-max color scale; origin upper; no crop",
                 "units": "pixel index; intensity source units unspecified",
                 "range": [vmin, vmax], "geometry": geo,
                 "device_pixels_per_source_pixel": geo.get("device_pixels_per_source_pixel", "composite")},
                cax=cb.ax, fixed_side_px=geo.get("side_px"), cb=cb, configured=True,
                requirement=requirement,
                raster={"type": "image", "npz": "PL_image.npz", "key": "intensity", "origin": "upper",
                        "vmin": vmin, "vmax": vmax, "cmap": "viridis",
                        "device_pixels_per_source_pixel": geo.get("device_pixels_per_source_pixel", 1)})


HEATMAP_PX_PER_CELL = 1.1  # smallest native cell spans >= 1.1 device px


def heatmap_requirement(ax, scans, wavelength):  # scans = the plotted x coordinate
    """Device px the data box needs so the smallest visible cell spans >= 1.1 px."""
    xs, ys = np.asarray(scans, float), np.asarray(wavelength, float)
    xl, yl = sorted(ax.get_xlim()), sorted(ax.get_ylim())
    return {"x_px": math.ceil((xl[1] - xl[0]) / np.diff(xs).min() * HEATMAP_PX_PER_CELL),
            "y_px": math.ceil((yl[1] - yl[0]) / np.diff(ys).min() * HEATMAP_PX_PER_CELL),
            "smallest_step": {"x": float(np.diff(xs).min()), "y_nm": float(np.diff(ys).min())},
            "px_per_smallest_cell": HEATMAP_PX_PER_CELL}


def _heatmap_figure(ctx, scans, wavelength, matrix, vmin, vmax, label, name, dpi=None, x_info=None):
    fig, ax = new_plot(ctx, dpi=dpi)
    # 波長間隔略不均勻，使用真正的波長座標，不能只把矩陣當均勻影像。
    # x = acquisition number, or elapsed time when an acquisition interval is set.
    im = ax.pcolormesh(scans, wavelength, matrix, shading="nearest", cmap="viridis",
                       vmin=vmin, vmax=vmax, antialiased=False, edgecolors="none", linewidth=0)
    if x_info:
        fig._paper_label_defaults = {"xlabel": x_info["default_label"]}
        if x_info["coordinate"] == "elapsed_time":
            ax._paper_start_tick = x_info["start"]   # first tick shows 0 (or the first time)
    cb = ps.add_colorbar(fig, ax, im, label)
    apply_config(ctx, name, fig, ax, cb)
    return fig, ax, cb


def _heatmap(ctx, scans, wavelength, matrix, vmin, vmax, label, name, evidence, npz, key, x_info=None, x_key=None):
    fig, ax, cb = _heatmap_figure(ctx, scans, wavelength, matrix, vmin, vmax, label, name, x_info=x_info)
    requirement = heatmap_requirement(ax, scans, wavelength)
    if not ctx.measure and name not in ctx.forced_box_px:
        # Probe the fitted data box at the base density, then raise the density so
        # every native cell (smallest measured wavelength step) gets >= 1.1 px.
        cax = cb.ax if cb.ax.get_visible() else None
        ps.fit_layout(fig, ax, cax=cax, clearance_mm=ctx.clearance_mm)
        bb = ax.get_window_extent()
        box_in = (bb.width / fig.dpi, bb.height / fig.dpi)
        plt.close(fig)
        dpi = max(ctx.dpi, math.ceil(requirement["x_px"] / box_in[0]),
                  math.ceil(requirement["y_px"] / box_in[1]))
        requirement["probe_box_in"] = list(box_in)
        requirement["dpi"] = dpi
        fig, ax, cb = _heatmap_figure(ctx, scans, wavelength, matrix, vmin, vmax, label, name, dpi=dpi,
                                      x_info=x_info)
    evidence = {**evidence, "native_cell_requirement": requirement}
    if x_info:
        evidence["x_coordinate"] = {k: v for k, v in x_info.items() if k != "default_label"}
        evidence["x_coordinate"]["npz_key"] = x_key
    save_figure(ctx, fig, name, evidence, cax=cb.ax, cb=cb, configured=True, requirement=requirement,
                raster={"type": "mesh", "npz": npz, "key": key, "x_npz": "in_situ_PL.npz",
                        "x_key": x_key or "acquisition_number", "y_key": "wavelength_nm",
                        "vmin": float(vmin), "vmax": float(vmax), "cmap": "viridis",
                        "shading": "nearest"})


def draw_in_situ(ctx):
    if not ctx.wants(*FIGURE_NAMES[5:]):
        return
    nonempty = []
    for sheet, d in cached(ctx.data / "in situ PL.xlsx", _load_in_situ):
        if d.empty:
            ctx.empty_sheets.append(sheet)
        else:
            nonempty.append((sheet, d))
    if len(nonempty) != 1:
        raise ValueError("Expected one nonempty spectrum sheet; review workbook mapping")
    sheet, d = nonempty[0]
    wavelength = d.iloc[5:, 0].to_numpy(dtype=float)
    counts = d.iloc[5:, 1:].to_numpy(dtype=float)
    timestamp = d.iloc[3, 1:].to_numpy(dtype=float)
    check_array("in situ PL", counts)
    check_array("wavelength", wavelength)
    assert counts.shape == (len(wavelength), len(timestamp))
    assert (np.diff(wavelength) > 0).all()
    scans = np.arange(1, counts.shape[1] + 1)
    # Plotted x coordinate per heatmap: acquisition number, or elapsed time from the
    # configured acquisition interval (figure_config "heatmap"). Stored next to the
    # data so the raster verification uses the same coordinate as the plot.
    x_of, x_extra = {}, {}
    for hname in fc.HEATMAPS:
        x, default, info = fc.heatmap_x(hname, ctx.config_for(hname) if ctx.wants(hname) else None, counts.shape[1])
        info["default_label"] = default
        xkey = ("acquisition_number" if info["coordinate"] == "acquisition_number"
                else f"x_{hname[:2]}_elapsed_{info['unit']}")
        if xkey != "acquisition_number":
            x_extra[xkey] = x
        x_of[hname] = (x if xkey != "acquisition_number" else scans, info, xkey)
    store(ctx, "in_situ_PL", wavelength_nm=wavelength, counts=counts,
          acquisition_number=scans, timestamp_source_units=timestamp, **x_extra)
    if ctx.write_provenance:
        pd.DataFrame({"acquisition_number": scans, "timestamp_source_units": timestamp,
                      "date_time": d.iloc[4, 1:].to_numpy()}).to_csv(
            ctx.source / "in_situ_acquisition_metadata.csv", index=False)

    if ctx.wants("06_in_situ_PL_heatmap"):
        xs, xi, xk = x_of["06_in_situ_PL_heatmap"]
        _heatmap(ctx, xs, wavelength, counts, float(counts.min()), float(counts.max()),
             fc.label_for("06_in_situ_PL_heatmap", "cbar_label"), "06_in_situ_PL_heatmap",
             {"source": "in situ PL.xlsx", "sheet": sheet, "shape": list(counts.shape),
              "observations_plotted": int(counts.size),
              "transform": "none; linear full-range heatmap; scan order on x axis",
              "time_unit": ("not supplied; no inferred time conversion" if xi["coordinate"] == "acquisition_number"
                            else f"elapsed time from the configured interval {xi['interval_s']:g} s, in {xi['unit']}")},
             "in_situ_PL.npz", "counts", x_info=xi, x_key=xk)

    mean = counts.mean(axis=1)  # 全部光譜的逐波長算術平均。
    if ctx.write_provenance:
        pd.DataFrame({"wavelength_nm": wavelength, "mean_counts": mean}).to_csv(
            ctx.source / "in_situ_mean_spectrum.csv", index=False)
    if ctx.wants("07_in_situ_PL_mean_spectrum"):
        fig, ax = new_plot(ctx)
        # Spec: dense spectra 07 and 10 use the thinner 1.25 pt data stroke.
        ax.plot(wavelength, mean, color=BLUE, linewidth=ps.DENSE_LINE_PT)
        ax.set_xlim(wavelength.min(), wavelength.max())
        save_figure(ctx, fig, "07_in_situ_PL_mean_spectrum",
                {"source": "in situ PL.xlsx", "rows_plotted": len(wavelength), "data_line_pt": ps.DENSE_LINE_PT,
                 "observations_used": int(counts.size),
                 "transform": "arithmetic mean across ALL acquisitions at each wavelength; no background correction"})

    # 第四課：normalized 必須寫清楚「除以哪個最大值」。
    # 全域除法保留量測之間的相對強度；逐次除法凸顯形狀、會消除峰高變化。
    global_max = float(counts.max())
    per_scan_max = counts.max(axis=0)
    mean_max = float(mean.max())
    if global_max <= 0 or mean_max <= 0 or not (per_scan_max > 0).all():
        raise ValueError("Peak normalization requires positive maxima")
    global_norm = counts / global_max
    per_scan_norm = counts / per_scan_max[np.newaxis, :]
    mean_norm = mean / mean_max
    store(ctx, "in_situ_PL_normalized", wavelength_nm=wavelength, acquisition_number=scans,
          global_normalized_counts=global_norm,
          per_acquisition_normalized_counts=per_scan_norm,
          global_divisor=np.asarray([global_max]), per_acquisition_divisors=per_scan_max,
          normalized_mean_spectrum=mean_norm, mean_spectrum_divisor=np.asarray([mean_max]))
    for matrix, key, suffix, formula in (
        (global_norm, "global_normalized_counts", "08_in_situ_PL_normalized_global",
         "I(λ, scan) / max(I over all wavelengths and scans)"),
        (per_scan_norm, "per_acquisition_normalized_counts", "09_in_situ_PL_normalized_per_scan",
         "I(λ, scan) / max(I over wavelengths within that scan)"),
    ):
        if not ctx.wants(suffix):
            continue
        xs, xi, xk = x_of[suffix]
        _heatmap(ctx, xs, wavelength, matrix, 0.0, 1.0, fc.label_for(suffix, "cbar_label"), suffix,
                 {"source": "in situ PL.xlsx", "shape": list(matrix.shape),
                  "observations_plotted": int(matrix.size), "transform": formula,
                  "baseline_subtracted": False, "color_limits": [0, 1],
                  "divisors": "source_data/in_situ_PL_normalized.npz",
                  "global_maximum_counts": global_max},
                 "in_situ_PL_normalized.npz", key, x_info=xi, x_key=xk)

    if ctx.write_provenance:
        pd.DataFrame({"wavelength_nm": wavelength, "normalized_mean_intensity": mean_norm}).to_csv(
            ctx.source / "in_situ_mean_spectrum_normalized.csv", index=False)
    if not ctx.wants("10_in_situ_PL_normalized_mean_spectrum"):
        return
    fig, ax = new_plot(ctx)
    ax.plot(wavelength, mean_norm, color=BLUE, linewidth=ps.DENSE_LINE_PT)
    ax.set_xlim(wavelength.min(), wavelength.max())
    ax.set_ylim(0, 1.05)
    save_figure(ctx, fig, "10_in_situ_PL_normalized_mean_spectrum",
                {"source": "in situ PL.xlsx", "rows_plotted": len(wavelength),
                 "observations_used": int(counts.size),
                 "transform": "mean(I across ALL scans) / max(mean spectrum)",
                 "divisor_counts": mean_max, "baseline_subtracted": False,
                 "data_line_pt": ps.DENSE_LINE_PT})


DRAWERS = (draw_ir, draw_xrd, draw_tpc, draw_pl_image, draw_in_situ)


def render_all(ctx):
    for directory in (ctx.out, ctx.qa, ctx.source):
        directory.mkdir(parents=True, exist_ok=True)
    for action in DRAWERS:
        print(f"RUNNING {action.__name__}", flush=True)
        action(ctx)
    return ctx.records
