"""House figure style helper: font resolution, fixed-canvas layout, TIFF export.

The stylesheet ``paper.mplstyle`` next to this module carries the shared
Matplotlib settings. This module adds what depends on the host or the figure:

* ``resolve_font``   - find Arial Bold on the host; refuse silent fallbacks.
* ``new_figure``     - fixed final-size canvas (89 mm, or 183 mm double column),
                       spines drawn outside the data area.
* ``add_colorbar``   - styled colour bar placed by ``fit_layout``.
* ``fit_layout``     - fit margins to the rendered artwork (measured on the
                       actual raster) so ink sits ~1.5 mm from every edge.
* ``export_tiff``    - RGB, LZW-compressed TIFF with embedded sRGB ICC profile,
                       straight from the Agg buffer.
* ``describe_figure``- artist-level evidence (fonts, sizes, strokes, ticks,
                       collisions, geometry) for the audits.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.mathtext import MathTextParser
from PIL import Image

STYLE_PATH = Path(__file__).resolve().with_name("paper.mplstyle")

MM_PER_IN = 25.4
SINGLE_COLUMN_MM = 89.0
DOUBLE_COLUMN_MM = 183.0
DEFAULT_HEIGHT_MM = {SINGLE_COLUMN_MM: 60.0, DOUBLE_COLUMN_MM: 105.0}
AXIS_LABEL_PT = 12.0     # axis labels and colour-bar titles
TICK_PT = 10.0           # tick labels, offsets, legends, annotations
LEGEND_PT = 10.0
DATA_LINE_PT = 1.5       # data lines and legend samples
DENSE_LINE_PT = 1.25     # dense spectra 07 and 10
SPINE_PT = 1.25          # spines and colour-bar outlines
TICK_WIDTH_PT = 1.0      # major and minor tick marks
LINE_PT = SPINE_PT       # backwards-compatible alias (spine stroke)
MIN_DPI = 600
DEFAULT_CLEARANCE_MM = 1.5
COLORBAR_GAP_PT = 6.0      # data box -> colour bar (Batch 6: 5 -> 6 pt for more clearance)
COLORBAR_LABELPAD_PT = 4.0  # colour-bar ticks -> colour-bar label (Batch 6: 3 -> 4 pt)
COLORBAR_WIDTH_PT = 7.0


def mm_to_in(mm):
    return mm / MM_PER_IN


def srgb_icc_bytes():
    """sRGB ICC profile bytes (LittleCMS built-in sRGB via Pillow ImageCms)."""
    from PIL import ImageCms
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


class FontUnavailable(RuntimeError):
    pass


@dataclass
class FontInfo:
    requested: str
    family: str
    path: str
    full_name: str
    style_name: str
    is_arial_bold: bool
    substitute: bool
    cmap: set = field(default_factory=set, repr=False)

    def as_dict(self):
        return {"requested": self.requested, "family": self.family, "path": self.path,
                "full_name": self.full_name, "style_name": self.style_name,
                "is_arial_bold": self.is_arial_bold, "substitute": self.substitute}


def _font_names(path):
    from fontTools.ttLib import TTFont
    font = TTFont(path, fontNumber=0, lazy=True)
    names = font["name"]
    family = names.getDebugName(1) or ""
    style = names.getDebugName(2) or ""
    full = names.getDebugName(4) or ""
    typo_family = names.getDebugName(16)
    typo_style = names.getDebugName(17)
    cmap = set(font.getBestCmap().keys())
    weight = font["OS/2"].usWeightClass
    return (typo_family or family), (typo_style or style), full, weight, cmap


def resolve_font(family="Arial", substitute=None):
    """Return the bold face for ``family``; raise unless it really is that family.

    ``substitute`` names an explicitly accepted stand-in (for example a
    metric-compatible face for proofing on a host without Arial). Output made
    with a substitute is flagged and never counts as Arial Bold.
    """
    def lookup(name):
        prop = FontProperties(family=name, weight="bold")
        try:
            path = font_manager.findfont(prop, fallback_to_default=False)
        except ValueError:
            return None
        fam, style, full, weight, cmap = _font_names(path)
        if fam.lower() != name.lower() or weight < 700:
            return None
        return path, fam, style, full, cmap

    found = lookup(family)
    if found:
        path, fam, style, full, cmap = found
        return FontInfo(family, fam, path, full, style,
                        fam.lower() == "arial" and "bold" in style.lower(), False, cmap)
    if not substitute:
        raise FontUnavailable(
            f"{family} Bold is not installed or not registered with Matplotlib. "
            "Install it (and clear the Matplotlib font cache) or pass an explicit substitute.")
    found = lookup(substitute)
    if not found:
        raise FontUnavailable(f"Neither {family} Bold nor substitute {substitute} Bold is available")
    path, fam, style, full, cmap = found
    return FontInfo(family, fam, path, full, style, False, True, cmap)


def apply_style(font: FontInfo):
    """Load the shared stylesheet and pin every text path to the resolved bold face."""
    mpl.rcdefaults()
    plt.style.use(STYLE_PATH)
    spec = f"{font.family}:bold"
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [font.family],
        "mathtext.rm": spec, "mathtext.it": spec, "mathtext.bf": spec,
        "mathtext.sf": spec, "mathtext.tt": spec, "mathtext.cal": spec,
    })
    # Any request for a missing family must fail loudly, not fall back quietly.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)


# --------------------------------------------------------------------- figure

def new_figure(dpi, width_mm=SINGLE_COLUMN_MM, height_mm=None):
    if height_mm is None:
        height_mm = DEFAULT_HEIGHT_MM.get(width_mm, 60.0)
    # Snap the canvas to whole device pixels so figure fractions map exactly onto
    # the raster (otherwise a 1:1 image box would be resampled by a fraction).
    w_px, h_px = round(mm_to_in(width_mm) * dpi), round(mm_to_in(height_mm) * dpi)
    fig = plt.figure(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
    fig._paper_target_mm = (float(width_mm), float(height_mm))
    ax = fig.add_axes((0.2, 0.2, 0.7, 0.7))
    style_axes(ax)
    return fig, ax


def style_axes(ax):
    """Four visible 1.25 pt spines just outside the data area; 1.0 pt ticks only left/bottom."""
    for side, spine in ax.spines.items():
        spine.set_visible(True)
        spine.set_linewidth(SPINE_PT)
        # Shift each spine outward by half its width so it never covers data
        # cells or image pixels; projecting caps close the corners.
        spine.set_position(("outward", SPINE_PT / 2))
        spine.set_capstyle("projecting")
        # Draw spines beneath data artists so anti-aliased spine edges can never
        # tint the outermost image pixels or heatmap cells.
        spine.set_zorder(-1)
    ax.tick_params(which="both", top=False, right=False, labeltop=False, labelright=False,
                   bottom=True, left=True, labelbottom=True, labelleft=True,
                   width=TICK_WIDTH_PT)
    ax.set_title("")


def close_spine_corners(ax):
    """Extend each outward spine by half a stroke so the corners close exactly.

    Spines sit LINE_PT/2 outside the data box; with projecting caps (another
    LINE_PT/2) the extended ends reach the outer edge of the perpendicular
    spine. Call after the final axes position is set (works on linear, log and
    inverted axes because the extension is computed in display space).
    """
    fig = ax.figure
    ext = SPINE_PT / 2 / 72 * fig.dpi
    bb = ax.get_window_extent()
    inv = ax.transData.inverted()
    (x_lo, y_lo), (x_hi, y_hi) = inv.transform([(bb.x0 - ext, bb.y0 - ext), (bb.x1 + ext, bb.y1 + ext)])
    for side in ("bottom", "top"):
        ax.spines[side].set_bounds(min(x_lo, x_hi), max(x_lo, x_hi))
    for side in ("left", "right"):
        ax.spines[side].set_bounds(min(y_lo, y_hi), max(y_lo, y_hi))


def add_colorbar(fig, ax, mappable, label, location="right"):
    """Colour bar beside ("right") or above ("top") the data box; placed by fit_layout."""
    cax = fig.add_axes((0.9, 0.2, 0.03, 0.7))
    cb = fig.colorbar(mappable, cax=cax, location=location)
    cax._paper_location = location
    cb.outline.set_linewidth(SPINE_PT)
    cb.ax.tick_params(which="both", width=TICK_WIDTH_PT, labelsize=TICK_PT)
    cb.ax.minorticks_off()
    cb.set_label(label, fontsize=AXIS_LABEL_PT, fontweight="bold", labelpad=COLORBAR_LABELPAD_PT)
    cax.set_label("<colorbar>")
    return cb


# --------------------------------------------------------------------- layout

def render_rgb(fig):
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()


def ink_bbox(rgb):
    """Bounding box (x0, y0_top, x1, y1_bottom) in raster rows/cols of non-white pixels."""
    mask = np.any(rgb != 255, axis=2)
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0:
        raise RuntimeError("Blank canvas")
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def edge_clearance_px(rgb):
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = ink_bbox(rgb)
    return {"left": x0, "right": w - 1 - x1, "top": y0, "bottom": h - 1 - y1}


def _place(fig, ax, cax, left, bottom, width, height):
    W, H = fig.canvas.get_width_height()
    ax.set_position((left / W, bottom / H, width / W, height / H))
    if cax is not None:
        gap = round(COLORBAR_GAP_PT / 72 * fig.dpi)
        cw = round(COLORBAR_WIDTH_PT / 72 * fig.dpi)
        if getattr(cax, "_paper_location", "right") == "top":
            cax.set_position((left / W, (bottom + height + gap) / H, width / W, cw / H))
        else:
            cax.set_position(((left + width + gap) / W, bottom / H, cw / W, height / H))


def fit_layout(fig, ax, cax=None, clearance_mm=DEFAULT_CLEARANCE_MM, fixed_side_px=None,
               max_iter=8, grow_height=True):
    """Fit the data box so the outermost rendered ink is ``clearance_mm`` from each edge.

    Margins are measured on the actual Agg raster after drawing, so text
    descenders, tick marks, legend and colour-bar artwork are all included.
    With ``fixed_side_px`` the data box is a square of exactly that many device
    pixels (native image pixels map 1:1); only left/bottom are then fitted and
    any remaining right/top space is reported as a clearance exception.
    All box edges are snapped to whole device pixels.
    """
    W, H = fig.canvas.get_width_height()
    target = clearance_mm / 25.4 * fig.dpi
    L, B, R, T = 0.2 * W, 0.18 * H, 0.06 * W, 0.04 * H
    if cax is not None and getattr(cax, "_paper_location", "right") == "right":
        R = 0.25 * W
    elif cax is not None:
        T = 0.2 * H
    history = []
    for _ in range(max_iter):
        Li, Bi = round(L), round(B)
        if fixed_side_px:
            width = height = int(fixed_side_px)
        else:
            width, height = W - Li - round(R), H - Bi - round(T)
        _place(fig, ax, cax, Li, Bi, width, height)
        rgb = render_rgb(fig)
        gaps = edge_clearance_px(rgb)
        history.append(gaps)
        d = {k: target - v for k, v in gaps.items()}
        L += d["left"]
        B += d["bottom"]
        if not fixed_side_px:
            R += d["right"]
            T += d["top"]
            if max(abs(v) for v in d.values()) <= 1:
                break
        elif abs(d["left"]) <= 1 and abs(d["bottom"]) <= 1:
            break
    gaps = edge_clearance_px(rgb)
    if fixed_side_px and (gaps["right"] < 0.5 * target or gaps["top"] < 0.5 * target):
        raise RuntimeError(f"Fixed {fixed_side_px}px data box does not fit the canvas: {gaps}")
    if grow_height and not fixed_side_px:
        # Spec: start at 60/105 mm and adjust the height to the content. A vertical
        # axis or colour-bar label longer than the data box would overrun it (and,
        # at 12 pt, the canvas); grow the canvas until every one fits the box.
        need = vertical_label_excess_px(fig, ax, cax)
        if need > 0:
            step = HEIGHT_STEP_MM / 25.4 * fig.dpi
            add = math.ceil(need / step) * step
            w_px, h_px = fig.canvas.get_width_height()
            new_h = round(h_px + add)
            fig.set_size_inches(w_px / fig.dpi, new_h / fig.dpi)
            w_mm, h_mm = getattr(fig, "_paper_target_mm", (w_px / fig.dpi * 25.4, h_px / fig.dpi * 25.4))
            fig._paper_target_mm = (w_mm, round(h_mm + add / fig.dpi * 25.4, 1))
            res = fit_layout(fig, ax, cax, clearance_mm, None, max_iter, grow_height=True)
            res["height_grown_mm"] = round(add / fig.dpi * 25.4 + res.get("height_grown_mm", 0), 2)
            return res
    close_spine_corners(ax)
    rgb = render_rgb(fig)
    gaps = edge_clearance_px(rgb)
    return {"clearance_px": gaps,
            "clearance_mm": {k: v / fig.dpi * 25.4 for k, v in gaps.items()},
            "iterations": len(history)}


HEIGHT_STEP_MM = 1.0        # canvas height grows in whole-mm steps
LABEL_BOX_SLACK_MM = 1.0    # a vertical label must be this much shorter than its box


def vertical_label_lengths_in(fig, ax, cax=None):
    """Rendered length (inches) of the y-axis label and right colour-bar label."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    out = {}
    pairs = [("y", ax, ax.yaxis.label)]
    if cax is not None and cax.get_visible() and getattr(cax, "_paper_location", "right") == "right":
        pairs.append(("colorbar", cax, cax.yaxis.label))
    for key, host, label in pairs:
        if label.get_visible() and label.get_text() and host.yaxis.get_visible():
            out[key] = label.get_window_extent(renderer).height / fig.dpi
    return out


def vertical_label_excess_px(fig, ax, cax=None):
    """Device px by which the longest vertical label exceeds its box height (minus slack)."""
    renderer = fig.canvas.get_renderer()
    slack = LABEL_BOX_SLACK_MM / 25.4 * fig.dpi
    worst = 0.0
    pairs = [(ax, ax.yaxis.label)]
    if cax is not None and cax.get_visible() and getattr(cax, "_paper_location", "right") == "right":
        pairs.append((cax, cax.yaxis.label))
    for host, label in pairs:
        if not (label.get_visible() and label.get_text() and host.yaxis.get_visible()):
            continue
        length = label.get_window_extent(renderer).height
        box = host.get_window_extent(renderer).height
        worst = max(worst, length + slack - box)
    return worst


def max_square_side_in(fig, ax, cax, clearance_mm=DEFAULT_CLEARANCE_MM):
    """Largest square data box (inches) that fits with the given decorations."""
    W, H = fig.canvas.get_width_height()
    side = 0.5 * W
    target = clearance_mm / 25.4 * fig.dpi
    L, B = 0.2 * W, 0.15 * H
    for _ in range(8):
        s = int(side)
        _place(fig, ax, cax, round(L), round(B), s, s)
        gaps = edge_clearance_px(render_rgb(fig))
        L += target - gaps["left"]
        B += target - gaps["bottom"]
        slack = min(gaps["right"] - target + (gaps["left"] - target),
                    gaps["top"] - target + (gaps["bottom"] - target))
        side += slack
        if abs(slack) <= 1:
            break
    return int(side) / fig.dpi


def _tick_label_overlaps(ax, axis_obj, renderer, pad_pt=1.0):
    pad = pad_pt / 72 * ax.figure.dpi
    lo, hi = sorted(axis_obj.get_view_interval())
    boxes = []
    for t in axis_obj.get_major_ticks():
        if lo <= t.get_loc() <= hi and t.label1.get_visible() and t.label1.get_text():
            boxes.append(t.label1.get_window_extent(renderer))
    horizontal = axis_obj is ax.xaxis
    boxes.sort(key=lambda b: b.x0 if horizontal else b.y0)
    for a, b in zip(boxes, boxes[1:]):
        if (b.x0 - a.x1 if horizontal else b.y0 - a.y1) < pad:
            return True
    return False


def thin_ticks(ax, skip=(), max_rounds=6):
    """Reduce major tick density on any axis whose tick labels collide (spec: avoid collisions).

    Axes listed in ``skip`` (user-set major step) are left alone. Returns the changes.
    """
    from matplotlib.ticker import LogLocator, MaxNLocator
    fig = ax.figure
    changes = {}
    for name, axis_obj in (("x", ax.xaxis), ("y", ax.yaxis)):
        if name in skip:
            continue
        for _ in range(max_rounds):
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            if not _tick_label_overlaps(ax, axis_obj, renderer):
                break
            lo, hi = sorted(axis_obj.get_view_interval())
            n = sum(lo <= v <= hi for v in axis_obj.get_majorticklocs())
            if n <= 2:
                break
            if axis_obj.get_scale() == "log":
                step = changes.get(name, {}).get("decade_step", 1) + 1
                axis_obj.set_major_locator(LogLocator(base=10 ** step, numticks=30))
                changes[name] = {"decade_step": step}
            else:
                axis_obj.set_major_locator(MaxNLocator(nbins=max(1, n - 2), steps=[1, 2, 2.5, 5, 10]))
                changes[name] = {"max_bins": max(1, n - 2)}
    return changes


LEGEND_LOCATIONS = ("upper right", "center right", "upper center", "lower left", "lower right",
                    "center left", "upper left", "lower center", "center")


def legend_data_hits(ax, legend, renderer=None, samples=4000):
    """Number of plotted data points (densely resampled along each line) inside the legend box."""
    renderer = renderer or ax.figure.canvas.get_renderer()
    lb = legend.get_window_extent(renderer)
    hits = 0
    box = ax.get_window_extent(renderer)
    if lb.x0 < box.x0 or lb.x1 > box.x1 or lb.y0 < box.y0 or lb.y1 > box.y1:
        hits += 10 ** 6  # legend does not fit inside the data box (would touch the frame)
    for line in ax.lines:
        xy = np.column_stack(line.get_data()).astype(float)
        pts = line.get_transform().transform(xy)
        if len(pts) > 1:  # include the segments between samples
            t = np.linspace(0, len(pts) - 1, max(samples, len(pts)))
            i = np.minimum(t.astype(int), len(pts) - 2)
            f = (t - i)[:, None]
            pts = pts[i] * (1 - f) + pts[i + 1] * f
        hits += int(((pts[:, 0] >= lb.x0) & (pts[:, 0] <= lb.x1) &
                     (pts[:, 1] >= lb.y0) & (pts[:, 1] <= lb.y1)).sum())
    return hits


def place_legend_clear(ax, candidates=LEGEND_LOCATIONS):
    """Move the legend to the first standard location where it covers no data.

    Call after the final data box is set. Returns {"loc", "hits", "tried"}.
    """
    legend = ax.get_legend()
    if legend is None:
        return None
    fig = ax.figure
    tried = []
    for loc in candidates:
        legend.set_loc(loc)
        fig.canvas.draw()
        hits = legend_data_hits(ax, legend)
        tried.append([loc, hits])
        if hits == 0:
            return {"loc": loc, "hits": 0, "tried": tried}
    # No free corner at this box size (narrow composite panels): add display headroom
    # above the data (limits only; data untouched) until an upper location is clear.
    y0, y1 = ax.get_ylim()
    if ax.get_yscale() == "linear" and y1 > y0:
        span = y1 - y0
        for k in range(1, 13):
            ax.set_ylim(y0, y1 + 0.06 * k * span)
            for loc in ("upper right", "upper left", "upper center"):
                legend.set_loc(loc)
                fig.canvas.draw()
                hits = legend_data_hits(ax, legend)
                tried.append([f"{loc} +{6 * k}% headroom", hits])
                if hits == 0:
                    return {"loc": loc, "hits": 0, "tried": tried, "headroom_fraction": 0.06 * k,
                            "ylim": [float(v) for v in ax.get_ylim()]}
        ax.set_ylim(y0, y1)
    best = min(tried, key=lambda t: t[1])
    legend.set_loc(best[0].split(" +")[0])
    fig.canvas.draw()
    return {"loc": best[0], "hits": best[1], "tried": tried}


# --------------------------------------------------------------------- export

def export_tiff(fig, path):
    """Save the fixed, uncropped canvas as RGB LZW TIFF with resolution tags and sRGB ICC."""
    rgb = render_rgb(fig)
    dpi = float(fig.dpi)
    Image.fromarray(rgb, mode="RGB").save(path, format="TIFF", compression="tiff_lzw",
                                          dpi=(dpi, dpi), icc_profile=srgb_icc_bytes())
    return rgb


def square_box_extents_in(fig, ax, cax=None, probe_side_frac=0.5):
    """Ink overhang (inches) beyond a square data box on each side.

    Text and tick sizes are in points, so the overhang does not depend on the
    box size or dpi; the caller derives the square side and canvas height.
    """
    W, H = fig.canvas.get_width_height()
    s = int(probe_side_frac * min(W, H))
    L, B = (W - s) // 3, (H - s) // 3
    _place(fig, ax, cax, L, B, s, s)
    x0, y0, x1, y1 = ink_bbox(render_rgb(fig))
    d = fig.dpi
    return {"left": (L - x0) / d, "right": (x1 + 1 - (L + s)) / d,
            "top": ((H - B - s) - y0) / d, "bottom": (y1 + 1 - (H - B)) / d}


# ------------------------------------------------------------------- evidence

def _bbox_px(artist, renderer, H):
    bb = artist.get_window_extent(renderer)
    return [float(bb.x0), float(H - bb.y1), float(bb.x1), float(H - bb.y0)]


def _visible_texts(fig):
    texts = []
    for ax in fig.axes:
        role = "colorbar" if ax.get_label() == "<colorbar>" else "axes"
        texts += [(f"{role}.xlabel", ax.xaxis.label), (f"{role}.ylabel", ax.yaxis.label),
                  (f"{role}.title", ax.title), (f"{role}.title_left", ax._left_title),
                  (f"{role}.title_right", ax._right_title),
                  (f"{role}.xoffset", ax.xaxis.offsetText),
                  (f"{role}.yoffset", ax.yaxis.offsetText)]
        for axis_name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            lo, hi = sorted(axis.get_view_interval())
            for which, ticks in (("major", axis.get_major_ticks()), ("minor", axis.get_minor_ticks())):
                for tick in ticks:
                    if not (lo - 1e-9 * abs(hi - lo) <= tick.get_loc() <= hi + 1e-9 * abs(hi - lo)):
                        continue
                    for lab_name, lab in (("label1", tick.label1), ("label2", tick.label2)):
                        texts.append((f"{role}.{axis_name}tick.{which}.{lab_name}", lab))
        legend = ax.get_legend()
        if legend is not None:
            texts += [(f"{role}.legend", t) for t in legend.get_texts()]
            if legend.get_title().get_text():
                texts.append((f"{role}.legend_title", legend.get_title()))
        texts += [(f"{role}.annotation", t) for t in ax.texts]
    texts += [("figure.text", t) for t in fig.texts]
    if getattr(fig, "_suptitle", None) is not None:
        texts.append(("figure.suptitle", fig._suptitle))
    return [(role, t) for role, t in texts if t.get_visible() and t.get_text()]


def _mathtext_glyph_fonts(text_artist, dpi):
    """Resolve each glyph of a mathtext string to its font file and position."""
    s = text_artist.get_text()
    prop = text_artist.get_fontproperties()
    glyphs = []
    # The "path" parser exposes every glyph as (font, fontsize, codepoint, x, y).
    out = MathTextParser("path").parse(s, dpi=72, prop=prop)
    for item in out.glyphs:
        # Matplotlib >= 3.10: (font, size, codepoint, glyph_index, x, y); older: no glyph_index.
        font, size, num, ox, oy = (item[0], item[1], item[2], item[-2], item[-1])
        glyphs.append({"char": chr(num), "font_path": font.fname,
                       "family": font.family_name, "style": font.style_name,
                       "size_pt": float(size), "x": float(ox), "y": float(oy)})
    return glyphs


def describe_text(role, text, font: FontInfo, renderer, H, dpi):
    s = text.get_text()
    prop = text.get_fontproperties()
    is_math = bool(text._preprocess_math(s)[1])
    try:
        resolved = font_manager.findfont(prop, fallback_to_default=False)
    except ValueError:
        resolved = None
    record = {"role": role, "text": s, "size_pt": float(prop.get_size_in_points()),
              "weight": prop.get_weight(), "family_requested": list(prop.get_family()),
              "resolved_path": resolved, "mathtext": bool(is_math),
              "bbox_px": _bbox_px(text, renderer, H)}
    if is_math:
        glyphs = _mathtext_glyph_fonts(text, dpi)
        record["glyphs"] = glyphs
        record["glyph_font_paths"] = sorted({g["font_path"] for g in glyphs})
        chars = [g["char"] for g in glyphs]
    else:
        record["glyph_font_paths"] = [resolved] if resolved else []
        chars = [c for c in s if not c.isspace()]
    record["missing_glyphs"] = sorted({c for c in chars if ord(c) not in font.cmap})
    record["all_glyphs_in_resolved_face"] = (
        bool(record["glyph_font_paths"]) and
        all(Path(p).resolve() == Path(font.path).resolve() for p in record["glyph_font_paths"])
        and not record["missing_glyphs"])
    return record


def _overlap(a, b, tol=0.0):
    return (min(a[2], b[2]) - max(a[0], b[0]) > tol) and (min(a[3], b[3]) - max(a[1], b[1]) > tol)


def describe_figure(fig, font: FontInfo, kind):
    """Collect artist-level evidence; the audits re-check it against the TIFF."""
    renderer = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    texts = [describe_text(role, t, font, renderer, H, fig.dpi) for role, t in _visible_texts(fig)]
    main = fig.axes[0]
    cax = next((a for a in fig.axes if a.get_label() == "<colorbar>"), None)

    strokes = []
    for ax in fig.axes:
        role = "colorbar" if ax is cax else "axes"
        for line in ax.lines:
            if line.get_visible():
                strokes.append({"role": f"{role}.data_line", "label": line.get_label(),
                                "linewidth_pt": float(line.get_linewidth()),
                                "linestyle": str(line.get_linestyle()), "color": line.get_color()})
        for name, spine in ax.spines.items():
            if spine.get_visible():
                strokes.append({"role": f"{role}.spine.{name}",
                                "linewidth_pt": float(spine.get_linewidth())})
        for axis_name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            lo, hi = sorted(axis.get_view_interval())
            for which, ticks in (("major", axis.get_major_ticks()), ("minor", axis.get_minor_ticks())):
                for tick in ticks:
                    if not (lo <= tick.get_loc() <= hi):
                        continue
                    for side, tl in (("1", tick.tick1line), ("2", tick.tick2line)):
                        if tl.get_visible():
                            strokes.append({"role": f"{role}.{axis_name}tick.{which}.tick{side}",
                                            "linewidth_pt": float(tl.get_markeredgewidth())})
        legend = ax.get_legend()
        if legend is not None:
            for h in legend.legend_handles:
                if isinstance(h, Line2D):
                    strokes.append({"role": f"{role}.legend_sample",
                                    "linewidth_pt": float(h.get_linewidth()),
                                    "linestyle": str(h.get_linestyle())})

    def side_ticks(ax):
        out = {}
        for axis_name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            for which, ticks in (("major", axis.get_major_ticks()), ("minor", axis.get_minor_ticks())):
                out[f"{axis_name}_{which}_tick2_visible"] = sum(t.tick2line.get_visible() for t in ticks)
                out[f"{axis_name}_{which}_label2_visible"] = sum(
                    t.label2.get_visible() and bool(t.label2.get_text()) for t in ticks)
                out[f"{axis_name}_{which}_tick1_visible"] = sum(t.tick1line.get_visible() for t in ticks)
        out["spines_visible"] = {k: s.get_visible() for k, s in ax.spines.items()}
        return out

    # Collisions between visible text boxes (ignoring each text's own pieces).
    collisions = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if _overlap(texts[i]["bbox_px"], texts[j]["bbox_px"], tol=0.5):
                collisions.append([texts[i]["role"] + ":" + texts[i]["text"],
                                   texts[j]["role"] + ":" + texts[j]["text"]])
    # Legend versus plotted data.
    legend_hits = []
    legend = main.get_legend()
    if legend is not None:
        lb = legend.get_window_extent(renderer)
        for line in main.lines:
            pts = line.get_transform().transform(np.column_stack(line.get_data()))
            inside = ((pts[:, 0] >= lb.x0) & (pts[:, 0] <= lb.x1) &
                      (pts[:, 1] >= lb.y0) & (pts[:, 1] <= lb.y1))
            if inside.any():
                legend_hits.append({"line": line.get_label(), "points_inside": int(inside.sum())})
        dense = legend_data_hits(main, legend, renderer)
        if dense and not legend_hits:
            legend_hits.append({"line": "segments between samples", "points_inside": dense})
    # Text outside canvas.
    outside = [t["role"] for t in texts
               if t["bbox_px"][0] < 0 or t["bbox_px"][1] < 0 or t["bbox_px"][2] > W or t["bbox_px"][3] > H]

    def box_px(ax):
        bb = ax.get_window_extent(renderer)
        return {"x0": float(bb.x0), "x1": float(bb.x1), "top": float(H - bb.y1),
                "bottom": float(H - bb.y0), "width": float(bb.width), "height": float(bb.height)}

    def tick_px(ax):
        out = {}
        for axis_name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            lo, hi = sorted(axis.get_view_interval())
            locs = [t for t in axis.get_majorticklocs() if lo <= t <= hi]
            pts = ax.transData.transform([(t, ax.get_ylim()[0]) if axis_name == "x" else
                                          (ax.get_xlim()[0], t) for t in locs])
            out[axis_name] = [float(p[0]) if axis_name == "x" else float(H - p[1]) for p in pts]
        return out

    record = {
        "kind": kind,
        "dpi": float(fig.dpi),
        "canvas_in": [float(v) for v in fig.get_size_inches()],
        "canvas_px": [W, H],
        "font": font.as_dict(),
        "texts": texts,
        "strokes": strokes,
        "titles": [t["text"] for t in texts if "title" in t["role"]],
        "main_axes": {"box_px": box_px(main), "xlim": [float(v) for v in main.get_xlim()],
                      "ylim": [float(v) for v in main.get_ylim()],
                      "xscale": main.get_xscale(), "yscale": main.get_yscale(),
                      "major_tick_px": tick_px(main),
                      **side_ticks(main)},
        "colorbar": None if cax is None else {"box_px": box_px(cax), **side_ticks(cax),
                                              "location": getattr(cax, "_paper_location", "right"),
                                              "outline_linewidth_pt": float(cax.spines["outline"].get_linewidth()),
                                              "ylim": [float(v) for v in cax.get_ylim()]},
        "text_collisions": collisions,
        "legend_data_overlap": legend_hits,
        "text_outside_canvas": outside,
    }
    return record
