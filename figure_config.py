"""Per-figure axis overrides: schema, validation, load/save and application.

A config is a small JSON file ``<config_dir>/<figure>.json``::

    {"figure": "01_IR",
     "axes": {"x": {"visible": true, "major_ticks": true, "minor_ticks": true,
                    "major_step": 500, "min": 500, "max": 3500},
              "y": {...}, "colorbar": {...}}}

Every key is optional; an unset key keeps the spec default. ``min``/``max`` are
numeric bounds; the axis direction (for example the descending IR wavenumber
axis) and scale (linear or log) are preserved. On a log axis ``major_step`` is
a whole number of decades. Colour-bar ``min``/``max`` set the colour limits.

Semantics at render time:
* ``visible: false`` hides that axis' tick marks, tick labels and label (the
  four-sided frame stays); for the colour bar it removes the bar entirely.
* ``major_ticks`` / ``minor_ticks`` toggle the tick marks of that level; major
  tick labels follow the major ticks, minor ticks never carry labels.
* Top and right spines never receive ticks or labels.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG_DIR = HERE / "figure_configs"
CONFIG_ENV = "FIGSTYLE_CONFIG_DIR"

# Axis geometry of every figure (scale, direction, hard bounds of meaningful limits).
_PIX = (-0.5, 3535.5)
AXES = {
    "01_IR": {"x": {"scale": "linear", "direction": "descending", "label": "Wavenumber"},
              "y": {"scale": "linear", "direction": "ascending", "label": "Transmittance"}},
    "02_XRD": {"x": {"scale": "linear", "direction": "ascending", "label": "2theta"},
               "y": {"scale": "linear", "direction": "ascending", "label": "Intensity"}},
    "03_TPC_overlay": {"x": {"scale": "linear", "direction": "ascending", "label": "Time"},
                       "y": {"scale": "linear", "direction": "ascending", "label": "Normalized current"}},
    "04_TPC_overlay_logtime": {"x": {"scale": "log", "direction": "ascending", "label": "Time (log)"},
                               "y": {"scale": "linear", "direction": "ascending", "label": "Normalized current"}},
    "05_PL_image": {"x": {"scale": "linear", "direction": "ascending", "label": "Column index", "bounds": _PIX},
                    "y": {"scale": "linear", "direction": "descending", "label": "Row index", "bounds": _PIX},
                    "colorbar": {"scale": "linear", "direction": "ascending", "label": "Intensity"}},
    "06_in_situ_PL_heatmap": {"x": {"scale": "linear", "direction": "ascending", "label": "Acquisition"},
                              "y": {"scale": "linear", "direction": "ascending", "label": "Wavelength"},
                              "colorbar": {"scale": "linear", "direction": "ascending", "label": "Counts"}},
    "07_in_situ_PL_mean_spectrum": {"x": {"scale": "linear", "direction": "ascending", "label": "Wavelength"},
                                    "y": {"scale": "linear", "direction": "ascending", "label": "Mean PL"}},
    "08_in_situ_PL_normalized_global": {"x": {"scale": "linear", "direction": "ascending", "label": "Acquisition"},
                                        "y": {"scale": "linear", "direction": "ascending", "label": "Wavelength"},
                                        "colorbar": {"scale": "linear", "direction": "ascending", "label": "Normalized"}},
    "09_in_situ_PL_normalized_per_scan": {"x": {"scale": "linear", "direction": "ascending", "label": "Acquisition"},
                                          "y": {"scale": "linear", "direction": "ascending", "label": "Wavelength"},
                                          "colorbar": {"scale": "linear", "direction": "ascending", "label": "Normalized"}},
    "10_in_situ_PL_normalized_mean_spectrum": {"x": {"scale": "linear", "direction": "ascending", "label": "Wavelength"},
                                               "y": {"scale": "linear", "direction": "ascending", "label": "Normalized mean PL"}},
}
KEYS = ("visible", "major_ticks", "minor_ticks", "major_step", "min", "max", "tick_labels")
MAX_MAJOR_TICKS = 40

# ---------------------------------------------------------- labels (Batch 6)
# Spec-default axis and colour-bar labels as (name, unit); the rendered text is
# "name (unit)" or just "name" when the unit is empty. Mathtext is allowed
# (cm$^{\text{-1}}$, 2$\theta$). Overrides are saved per figure under "labels":
#     {"labels": {"xlabel": {"name": "Wavenumber", "unit": "cm$^{-1}$"},
#                 "ylabel": {"unit": "a.u."}, "cbar_label": {"name": "Counts"}}}
# A missing name or unit keeps the default part; "unit": "" removes the unit.
LABEL_KEYS = ("xlabel", "ylabel", "cbar_label")
LABEL_AXIS = {"xlabel": "x", "ylabel": "y", "cbar_label": "colorbar"}
AXIS_LABEL_KEY = {v: k for k, v in LABEL_AXIS.items()}
_CM1 = r"cm$^{\text{-1}}$"
_HEAT = {"xlabel": ("Acquisition number", ""), "ylabel": ("Wavelength", "nm")}
DEFAULT_LABELS = {
    "01_IR": {"xlabel": ("Wavenumber", _CM1), "ylabel": ("Transmittance", "%")},
    "02_XRD": {"xlabel": ("2θ", "°"), "ylabel": ("Intensity", "a.u.")},
    "03_TPC_overlay": {"xlabel": ("Time", "µs"), "ylabel": ("Normalized current", "")},
    "04_TPC_overlay_logtime": {"xlabel": ("Time", "µs"), "ylabel": ("Normalized current", "")},
    "05_PL_image": {"xlabel": ("Column index", "pixel"), "ylabel": ("Row index", "pixel"),
                    "cbar_label": ("Intensity", "source units")},
    "06_in_situ_PL_heatmap": {**_HEAT, "cbar_label": ("PL intensity", "counts")},
    "07_in_situ_PL_mean_spectrum": {"xlabel": ("Wavelength", "nm"), "ylabel": ("Mean PL intensity", "counts")},
    "08_in_situ_PL_normalized_global": {**_HEAT, "cbar_label": ("Normalized PL intensity", "")},
    "09_in_situ_PL_normalized_per_scan": {**_HEAT, "cbar_label": ("Normalized PL intensity", "")},
    "10_in_situ_PL_normalized_mean_spectrum": {"xlabel": ("Wavelength", "nm"),
                                               "ylabel": ("Normalized mean PL intensity", "")},
}
LABEL_MAX_CHARS = 80
# Unicode super/subscripts typed by the user become true mathtext scripts; the
# minus (U+207B, U+2212) becomes the spec halfwidth hyphen.
_SUPER = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ", "0123456789+-=()n"))
_SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎", "0123456789+-=()"))

# Legend text (Batch 6): figures with plotted line labels and their defaults.
DEFAULT_LEGEND = {"03_TPC_overlay": ["TPC 1 (D1-1)", "TPC 2 (D2-1)"],
                  "04_TPC_overlay_logtime": ["TPC 1 (D1-1)", "TPC 2 (D2-1)"]}
# Heatmap acquisition interval (Batch 6): {"heatmap": {"interval_s": 2.0, "start_s": 0.0}}.
HEATMAPS = ("06_in_situ_PL_heatmap", "08_in_situ_PL_normalized_global", "09_in_situ_PL_normalized_per_scan")
HEATMAP_KEYS = ("interval_s", "start_s")
MINUTES_ABOVE_S = 300.0   # x span above ~300 s is shown in minutes
FIGURE_KEYS = ("figure", "axes", "labels", "legend", "heatmap", "palette")
# Series palette (figure level): {"palette": "nature-6c-2"}. Any id from
# palettes.list_palettes(); naming one switches the series colours of that
# figure. Absent = no palette named: the figure keeps its spec colours.


class ConfigError(ValueError):
    pass


def config_dir(explicit=None):
    if explicit:
        return Path(explicit)
    env = os.environ.get(CONFIG_ENV)
    return Path(env) if env else DEFAULT_CONFIG_DIR


def config_path(name, directory=None):
    return config_dir(directory) / f"{name}.json"


def empty(name):
    return {"figure": name, "axes": {}}


def validate_axis(name, axis, settings):
    """Raise ConfigError for any invalid value; return a cleaned copy."""
    if name not in AXES:
        raise ConfigError(f"unknown figure {name!r}")
    if axis not in AXES[name]:
        raise ConfigError(f"{name} has no {axis!r} axis (available: {', '.join(AXES[name])})")
    geo = AXES[name][axis]
    out = {}
    for key, value in settings.items():
        if key not in KEYS:
            raise ConfigError(f"unknown setting {key!r} (allowed: {', '.join(KEYS)})")
        if value is None:
            continue
        if key in ("visible", "major_ticks", "minor_ticks", "tick_labels"):
            if not isinstance(value, bool):
                raise ConfigError(f"{axis}.{key} must be true/false")
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ConfigError(f"{axis}.{key} must be a finite number")
            value = float(value)
        out[key] = value
    lo, hi = out.get("min"), out.get("max")
    if geo["scale"] == "log":
        for key in ("min", "max"):
            if key in out and out[key] <= 0:
                raise ConfigError(f"{axis}.{key} must be > 0 on a log axis")
        if "major_step" in out and (out["major_step"] < 1 or out["major_step"] != int(out["major_step"])):
            raise ConfigError(f"{axis}.major_step on a log axis is a whole number of decades (>= 1)")
    elif "major_step" in out and out["major_step"] <= 0:
        raise ConfigError(f"{axis}.major_step must be > 0")
    if lo is not None and hi is not None and not lo < hi:
        raise ConfigError(f"{axis}: min ({lo:g}) must be smaller than max ({hi:g})")
    bounds = geo.get("bounds")
    if bounds:
        for key in ("min", "max"):
            if key in out and not bounds[0] <= out[key] <= bounds[1]:
                raise ConfigError(f"{axis}.{key} must lie inside the image extent {bounds}")
    if "major_step" in out and lo is not None and hi is not None and geo["scale"] == "linear":
        if (hi - lo) / out["major_step"] > MAX_MAJOR_TICKS:
            raise ConfigError(f"{axis}.major_step too small: more than {MAX_MAJOR_TICKS} ticks in [{lo:g}, {hi:g}]")
    return out


def normalize_label(text):
    """User label text -> mathtext the renderer sets as true scripts.

    * Unicode superscripts/subscripts (``cm⁻¹``, U+207B U+00B9) become
      ``cm$^{\\text{-1}}$``; ``x₂`` becomes ``x$_{2}$``.
    * Inside ``$...$`` every bare ``-`` (and U+2212) is set as the halfwidth
      hyphen ``\\text{-}`` (spec: halfwidth hyphens), so ``cm$^{-1}$`` renders like
      the built-in default.
    Raises ConfigError for unbalanced ``$`` or mathtext the parser rejects.
    """
    import re
    if not isinstance(text, str):
        raise ConfigError("label text must be a string")
    s = text.strip().replace("\u2212", "-")
    out, i = [], 0
    while i < len(s):
        for table, op in ((_SUPER, "^"), (_SUB, "_")):
            if s[i] in table:
                j = i
                while j < len(s) and s[j] in table:
                    j += 1
                out.append(f"${op}{{{''.join(table[c] for c in s[i:j])}}}$")
                i = j
                break
        else:
            out.append(s[i])
            i += 1
    s = "".join(out).replace("$$", "")   # adjacent math runs merge
    parts = re.split(r"(?<!\\)\$", s)
    if len(parts) % 2 == 0:
        raise ConfigError(f"label {text!r}: unbalanced '$' (mathtext needs pairs, e.g. cm$^{{-1}}$)")
    for k in range(1, len(parts), 2):
        seg = parts[k].replace("\\text{-", "\0TXT")
        seg = re.sub(r"-(\d*)", r"\\text{-\1}", seg).replace("\0TXT", "\\text{-")
        parts[k] = seg
    s = "$".join(parts)
    if len(s) > LABEL_MAX_CHARS * 2 or len(text) > LABEL_MAX_CHARS:
        raise ConfigError(f"label {text!r}: longer than {LABEL_MAX_CHARS} characters")
    if "$" in s:
        from matplotlib.mathtext import MathTextParser
        try:
            MathTextParser("path").parse(s, dpi=72)
        except ValueError as exc:
            raise ConfigError(f"label {text!r}: mathtext error: {' '.join(str(exc).split())[:120]}") from None
    return s


def compose_label(name, unit):
    return f"{name} ({unit})" if unit else name


def default_label(name, key):
    """Spec-default (name, unit) for figure ``name`` and label key (xlabel/ylabel/cbar_label)."""
    return DEFAULT_LABELS[name][key]


def validate_labels(name, labels):
    if not isinstance(labels, dict):
        raise ConfigError("labels must be an object {xlabel|ylabel|cbar_label: {name, unit}}")
    out = {}
    for key, v in labels.items():
        if key not in LABEL_KEYS:
            raise ConfigError(f"unknown label {key!r} (allowed: {', '.join(LABEL_KEYS)})")
        if key not in DEFAULT_LABELS[name]:
            raise ConfigError(f"{name} has no {key}")
        if v is None:
            continue
        if not isinstance(v, dict) or set(v) - {"name", "unit"}:
            raise ConfigError(f"{key} must be an object with optional 'name' and 'unit'")
        clean = {}
        for part in ("name", "unit"):
            if v.get(part) is None:
                continue
            if part == "name" and not str(v[part]).strip():
                raise ConfigError(f"{key}.name must not be empty (use 'auto' to restore the default)")
            clean[part] = normalize_label(v[part]) if v[part] != "" else ""
        if clean:
            out[key] = clean
    return out


def label_for(name, key, cfg=None, default=None):
    """Final label text for ``key``: saved/explicit overrides over the default.

    ``default`` (name, unit) replaces the spec default, e.g. ('Time', 's') for a
    heatmap with an acquisition interval.
    """
    d_name, d_unit = default or DEFAULT_LABELS[name][key]
    o = ((cfg or {}).get("labels") or {}).get(key) or {}
    return compose_label(o.get("name", d_name), o.get("unit", d_unit))


def validate_legend(name, legend):
    if name not in DEFAULT_LEGEND:
        raise ConfigError(f"{name} has no legend (legend text applies to {', '.join(DEFAULT_LEGEND)})")
    if not isinstance(legend, dict) or set(legend) - {"labels"}:
        raise ConfigError("legend must be an object {\"labels\": [text, ...]}")
    labels = legend.get("labels")
    if labels is None:
        return {}
    n = len(DEFAULT_LEGEND[name])
    if not isinstance(labels, list) or len(labels) != n:
        raise ConfigError(f"{name} legend needs exactly {n} labels (one per plotted line), got "
                          f"{len(labels) if isinstance(labels, list) else labels!r}")
    clean = []
    for t in labels:
        if t is None or (isinstance(t, str) and t.strip().lower() in ("", "auto")):
            clean.append(None)   # keep the default for this line
        else:
            clean.append(normalize_label(str(t)))
    return {"labels": clean} if any(c is not None for c in clean) else {}


def legend_labels(name, cfg=None):
    """Plotted line labels for ``name`` (defaults with per-line overrides)."""
    labels = list(DEFAULT_LEGEND[name])
    for i, t in enumerate(((cfg or {}).get("legend") or {}).get("labels") or []):
        if t is not None:
            labels[i] = t
    return labels


def validate_heatmap(name, h):
    if name not in HEATMAPS:
        raise ConfigError(f"{name} is not a heatmap (interval applies to {', '.join(HEATMAPS)})")
    if not isinstance(h, dict):
        raise ConfigError("heatmap must be an object {\"interval_s\": seconds, \"start_s\": seconds}")
    out = {}
    for key, v in h.items():
        if key not in HEATMAP_KEYS:
            raise ConfigError(f"unknown heatmap setting {key!r} (allowed: {', '.join(HEATMAP_KEYS)})")
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ConfigError(f"heatmap.{key} must be a finite number")
        if key == "interval_s" and v <= 0:
            raise ConfigError("heatmap.interval_s must be > 0 seconds")
        if key == "start_s" and v < 0:
            raise ConfigError("heatmap.start_s must be >= 0 seconds")
        out[key] = float(v)
    if "start_s" in out and "interval_s" not in out:
        raise ConfigError("heatmap.start_s needs heatmap.interval_s")
    return out


def heatmap_x(name, cfg, n):
    """Plotted x coordinate for an ``n``-acquisition heatmap.

    Default: acquisition numbers 1..n, label 'Acquisition number'. With
    ``interval_s``: elapsed time start_s + (k - 1) * interval_s, in s, or in min
    when the span exceeds MINUTES_ABOVE_S. Returns (x, default (name, unit), info).
    """
    import numpy as np
    h = (cfg or {}).get("heatmap") or {}
    scans = np.arange(1, n + 1, dtype=float)
    if "interval_s" not in h:
        return scans, DEFAULT_LABELS[name]["xlabel"], {"coordinate": "acquisition_number", "unit": None,
                                                        "start": 1.0}
    t = h.get("start_s", 0.0) + (scans - 1) * h["interval_s"]
    span = float(t[-1] - t[0])
    unit, div = ("min", 60.0) if span > MINUTES_ABOVE_S else ("s", 1.0)
    return t / div, ("Time", unit), {"coordinate": "elapsed_time", "unit": unit, "interval_s": h["interval_s"],
                                     "start_s": h.get("start_s", 0.0), "span_s": span,
                                     "start": float(t[0] / div), "rule": f"minutes when span > {MINUTES_ABOVE_S:g} s"}


def validate(cfg):
    name = cfg.get("figure")
    if name not in AXES:
        raise ConfigError(f"unknown figure {name!r}")
    extra = set(cfg) - set(FIGURE_KEYS)
    if extra:
        raise ConfigError(f"unknown config key(s) {', '.join(sorted(extra))} (allowed: {', '.join(FIGURE_KEYS)})")
    axes = {a: validate_axis(name, a, s) for a, s in (cfg.get("axes") or {}).items()}
    out = {"figure": name, "axes": {a: s for a, s in axes.items() if s}}
    # Older configs (Batch 1-5) only carry "axes"; the Batch 6 keys are optional.
    if cfg.get("labels"):
        lab = validate_labels(name, cfg["labels"])
        if lab:
            out["labels"] = lab
    if cfg.get("legend"):
        leg = validate_legend(name, cfg["legend"])
        if leg:
            out["legend"] = leg
    if cfg.get("heatmap"):
        hm = validate_heatmap(name, cfg["heatmap"])
        if hm:
            out["heatmap"] = hm
    if cfg.get("palette") is not None:
        out["palette"] = validate_palette(cfg["palette"], name)
    return out


def has_series(name):
    """True for line figures (series palettes apply); image/heatmap figures keep their colormap."""
    return "colorbar" not in AXES[name]


def validate_palette(value, name=None):
    """A known palette id (see palettes.list_palettes()); raises ConfigError otherwise."""
    import palettes
    if name is not None and not has_series(name):
        raise ConfigError(f"{name} is a colormap figure; palettes apply to line figures only "
                          f"({', '.join(n for n in AXES if has_series(n))})")
    try:
        return palettes.validate_name(value)
    except palettes.PaletteError as exc:
        raise ConfigError(str(exc)) from None


def load(name, directory=None):
    """Return the validated saved config for ``name`` or None if no file exists."""
    path = config_path(name, directory)
    if not path.exists():
        return None
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("figure") != name:
        raise ConfigError(f"{path}: figure field {cfg.get('figure')!r} does not match {name!r}")
    return validate(cfg)


def save(cfg, directory=None):
    cfg = validate(cfg)
    path = config_path(cfg["figure"], directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------ apply

def _set_limits(ax, axis, geo, lo, hi):
    get = ax.get_xlim if axis == "x" else ax.get_ylim
    setter = ax.set_xlim if axis == "x" else ax.set_ylim
    cur = get()
    cur_lo, cur_hi = min(cur), max(cur)
    lo = cur_lo if lo is None else lo
    hi = cur_hi if hi is None else hi
    if not lo < hi:
        raise ConfigError(f"{axis}: resulting limits [{lo:g}, {hi:g}] are empty")
    descending = cur[0] > cur[1]  # keep the existing direction
    setter((hi, lo) if descending else (lo, hi))


def _apply_axis(ax, axis_obj, axis, geo, s):
    from matplotlib.ticker import AutoMinorLocator, LogLocator, MultipleLocator, NullFormatter, NullLocator
    if "min" in s or "max" in s:
        _set_limits(ax, axis, geo, s.get("min"), s.get("max"))
    if "major_step" in s:
        if geo["scale"] == "log":
            axis_obj.set_major_locator(LogLocator(base=10 ** int(s["major_step"]), numticks=30))
        else:
            axis_obj.set_major_locator(MultipleLocator(s["major_step"]))
    if s.get("minor_ticks") is True:
        if geo["scale"] == "log":
            axis_obj.set_minor_locator(LogLocator(base=10, subs=tuple(range(2, 10)), numticks=30))
        else:
            axis_obj.set_minor_locator(AutoMinorLocator())
        axis_obj.set_minor_formatter(NullFormatter())
    elif s.get("minor_ticks") is False:
        axis_obj.set_minor_locator(NullLocator())
    first = "bottom" if axis == "x" else "left"
    if s.get("major_ticks") is False:
        ax.tick_params(axis=axis, which="major", **{first: False, "label" + first: False})
    if s.get("tick_labels") is False:
        # "hide tick numbers only": tick marks and the axis label stay; the
        # numeric offset (x10^n / +c) belongs to the numbers and is hidden too.
        ax.tick_params(axis=axis, which="both", **{"label" + first: False})
        axis_obj.offsetText.set_visible(False)
        axis_obj._paper_hide_offset = True
    if s.get("visible") is False:
        ax.tick_params(axis=axis, which="both", **{first: False, "label" + first: False})
        axis_obj.label.set_visible(False)
        axis_obj.offsetText.set_visible(False)


def _apply_colorbar(cb, s):
    from matplotlib.ticker import AutoMinorLocator, MultipleLocator, NullLocator
    if s.get("visible") is False:
        cb.ax.set_visible(False)
        return
    if "min" in s or "max" in s:
        lo, hi = cb.mappable.get_clim()
        lo = s.get("min", lo)
        hi = s.get("max", hi)
        if not lo < hi:
            raise ConfigError(f"colorbar: limits [{lo:g}, {hi:g}] are empty")
        cb.mappable.set_clim(lo, hi)
    if "major_step" in s:
        cb.locator = MultipleLocator(s["major_step"])
    cb.update_ticks()
    long_axis = cb.ax.yaxis if cb.orientation == "vertical" else cb.ax.xaxis
    if s.get("minor_ticks") is True:
        long_axis.set_minor_locator(AutoMinorLocator())
    elif s.get("minor_ticks") is False:
        long_axis.set_minor_locator(NullLocator())
    if s.get("major_ticks") is False:
        cb.ax.tick_params(which="major", length=0, labelright=False, labelleft=False,
                          labelbottom=False, labeltop=False)
    if s.get("tick_labels") is False:
        cb.ax.tick_params(which="both", labelright=False, labelleft=False, labelbottom=False, labeltop=False)
        long_axis.offsetText.set_visible(False)
        long_axis._paper_hide_offset = True


def apply(name, cfg, fig, ax, cb=None):
    """Apply a validated config to a drawn figure (before layout fitting)."""
    defaults = getattr(fig, "_paper_label_defaults", {})
    # Labels (Batch 6): always set from the defaults + overrides, so the code
    # holds no hard-coded label text and an old config (no "labels") renders
    # the spec defaults.
    cfg = validate(cfg) if cfg else {"figure": name, "axes": {}}
    for key, default in DEFAULT_LABELS[name].items():
        text = label_for(name, key, cfg, defaults.get(key))
        if key == "xlabel":
            ax.xaxis.label.set_text(text)
        elif key == "ylabel":
            ax.yaxis.label.set_text(text)
        elif cb is not None:
            (cb.ax.yaxis if cb.orientation == "vertical" else cb.ax.xaxis).label.set_text(text)
    if not (cfg["axes"] or cfg.get("labels") or cfg.get("legend") or cfg.get("heatmap") or cfg.get("palette")):
        ax.tick_params(which="both", top=False, right=False, labeltop=False, labelright=False)
        return {}
    for axis, s in cfg["axes"].items():
        geo = AXES[name][axis]
        if axis == "colorbar":
            if cb is not None:
                _apply_colorbar(cb, s)
        else:
            _apply_axis(ax, ax.xaxis if axis == "x" else ax.yaxis, axis, geo, s)
    # Spec: top and right spines stay visible and never carry ticks or labels.
    ax.tick_params(which="both", top=False, right=False, labeltop=False, labelright=False)
    applied = dict(cfg["axes"])
    for key in ("labels", "legend", "heatmap", "palette"):
        if cfg.get(key):
            applied[key] = cfg[key]
    return applied


def describe(name, cfg):
    lines = []
    axes = (cfg or {}).get("axes", {})
    for axis in AXES[name]:
        s = axes.get(axis, {})
        shown = ", ".join(f"{k}={s[k]}" for k in KEYS if k in s) or "spec defaults"
        key = AXIS_LABEL_KEY[axis]
        lab = ((cfg or {}).get("labels") or {}).get(key)
        default = None
        if key == "xlabel" and name in HEATMAPS and ((cfg or {}).get("heatmap") or {}).get("interval_s"):
            default = ("Time", "s; min if span > 300 s")
        lines.append(f"  {axis:9s} [{AXES[name][axis]['scale']}, {AXES[name][axis]['direction']}]: {shown}"
                     f"; {key}: '{label_for(name, key, cfg, default)}'{' (default)' if not lab else ''}")
    if name in DEFAULT_LEGEND:
        lines.append(f"  legend text: {'; '.join(legend_labels(name, cfg))}"
                     f"{' (default)' if not (cfg or {}).get('legend') else ''}")
    pal = (cfg or {}).get("palette")
    if has_series(name):
        lines.append(f"  palette: {pal if pal else 'none named (spec colours)'}")
    if name in HEATMAPS:
        h = (cfg or {}).get("heatmap") or {}
        lines.append("  acquisition interval: " + (f"{h['interval_s']:g} s (start {h.get('start_s', 0):g} s) -> "
                                                   "Time (s), or Time (min) above 300 s" if h
                                                   else "none (x = acquisition number)"))
    return "\n".join(lines)


# ------------------------------------------- composite labels, layout, spans
# Saved as <config_dir>/composite.json inside the existing {"composite": {...}} schema:
#     {"composite": {"label_format": "(a)", "label_pt": 14.0,
#                    "layout": "auto", "spans": {"a": "row", "c": "1x2"},
#                    "empty_cells": "legend", "legend_cell": "auto",
#                    "legend_entries": ["Sample A=#2166AC:solid", "Sample B=#B35806:dashed"],
#                    "shared_legend": true}}
# Batch 6: ``shared_legend`` true = one legend for the whole figure in an empty
# cell; per-panel legends are suppressed and the entries default to the panel
# line handles (label, colour, marker, linestyle). User ``legend_entries`` are
# compared against those handles and every count/style mismatch is a WARNING.
# Entry syntax: 'Label=color[:style[:marker]]' (marker: none, o, s, ^, v, D, x, +, *, .).
# Every key is optional (a label-only file stays valid); unset keys fall back to
# the defaults below (2026-11-20 01:53: panel labels (a) 14 pt per user; layout
# manual; no spans; empty cells blank; legend cell auto). Read by
# make_composite.py, written by figmenu.py. Explicit CLI flags win per key;
# ``--span`` (any) replaces the saved spans as a whole and ``--span none`` clears them.
COMPOSITE_CONFIG_NAME = "composite.json"
LABEL_FORMAT_DEFAULT = "(a)"
LABEL_PT_DEFAULT = 14.0
LABEL_FORMATS = ("(a)", "a", "a)", "a.", "(A)", "A", "A)", "A.")
LABEL_PT_RANGE = (6.0, 24.0)
LAYOUT_MODES = ("manual", "auto")
LAYOUT_DEFAULT = "manual"
EMPTY_CELL_USES = ("blank", "legend")
EMPTY_CELLS_DEFAULT = "blank"
LEGEND_CELL_DEFAULT = "auto"
LEGEND_STYLES = ("solid", "dashed", "dotted", "dashdot")
LEGEND_MARKERS = ("none", "o", "s", "^", "v", "D", "x", "+", "*", ".")
COMPOSITE_KEYS = ("label_format", "label_pt", "layout", "spans", "empty_cells", "legend_cell",
                  "legend_entries", "shared_legend")
COMPOSITE_DEFAULTS = {"label_format": LABEL_FORMAT_DEFAULT, "label_pt": LABEL_PT_DEFAULT,
                      "layout": LAYOUT_DEFAULT, "spans": {}, "empty_cells": EMPTY_CELLS_DEFAULT,
                      "legend_cell": LEGEND_CELL_DEFAULT, "legend_entries": [], "shared_legend": False}
PANEL_IDS = "abcdefghijklmnopqrstuvwxyz"


def format_panel_label(fmt, index):
    """Label text for panel ``index`` (0-based) in style ``fmt``: '(a)', 0 -> '(a)'; 'A.', 1 -> 'B.'."""
    if fmt not in LABEL_FORMATS:
        raise ConfigError(f"label_format must be one of {', '.join(LABEL_FORMATS)}")
    if not 0 <= index < 26:
        raise ConfigError("at most 26 panels can be labelled")
    letter = "abcdefghijklmnopqrstuvwxyz"[index]
    return fmt.replace("a", letter) if "a" in fmt else fmt.replace("A", letter.upper())


def parse_span_value(pid, value):
    """'row' -> ('row', 1); '2x1' -> (2, 1) as (columns, rows). Raises ConfigError."""
    v = str(value).strip().lower()
    if v == "row":
        return ("row", 1)
    parts = v.split("x")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ConfigError(f"span {pid}={value!r}: use 'row' (full row) or COLSxROWS such as 2x1")
    cs, rs = int(parts[0]), int(parts[1])
    if cs < 1 or rs < 1 or cs > 26 or rs > 26:
        raise ConfigError(f"span {pid}={value!r}: columns and rows must be 1-26")
    return (cs, rs)


def parse_span_items(items):
    """CLI ``--span`` values ('a=row', 'b=2x1', or 'none') -> {id: value}. Duplicates are errors."""
    out = {}
    for item in items or []:
        if str(item).strip().lower() == "none":
            continue
        if "=" not in item:
            raise ConfigError(f"span {item!r}: use ID=row or ID=COLSxROWS (for example a=row, b=2x1)")
        pid, value = (x.strip() for x in item.split("=", 1))
        if pid in out:
            raise ConfigError(f"duplicate span for panel {pid!r}")
        out[pid] = value
    return out


def parse_legend_entry(entry):
    """'Label=color[:style]' -> (label, color, style). Raises ConfigError."""
    e = parse_legend_entry_full(entry)
    return e["label"], e["color"], e["linestyle"]


def parse_legend_entry_full(entry):
    """'Label=color[:style[:marker]]' -> {label, color, linestyle, marker}. Raises ConfigError."""
    if isinstance(entry, dict):
        entry = (f"{entry['label']}={entry['color']}:{entry.get('linestyle', 'solid')}"
                 f":{entry.get('marker', 'none')}")
    if not isinstance(entry, str) or "=" not in entry:
        raise ConfigError(f"legend entry {entry!r}: use 'Label=color[:style[:marker]]'")
    label, rest = entry.rsplit("=", 1)
    color, _, style = rest.partition(":")
    style, _, marker = style.partition(":")
    marker = marker.strip() or "none"
    if marker not in LEGEND_MARKERS:
        raise ConfigError(f"legend entry {entry!r}: marker must be one of {', '.join(LEGEND_MARKERS)}")
    style = style.strip() or "solid"
    label, color = label.strip(), color.strip()
    if not label:
        raise ConfigError(f"legend entry {entry!r}: empty label")
    from matplotlib.colors import is_color_like
    if not is_color_like(color):
        raise ConfigError(f"legend entry {entry!r}: {color!r} is not a colour")
    if style not in LEGEND_STYLES:
        raise ConfigError(f"legend entry {entry!r}: style must be one of {', '.join(LEGEND_STYLES)}")
    return {"label": label, "color": color, "linestyle": style, "marker": marker}


def parse_legend_cell(value):
    """'auto' -> 'auto'; 'R,C' (1-based) -> (R, C)."""
    v = str(value).strip().lower()
    if v == "auto":
        return "auto"
    parts = [x.strip() for x in v.split(",")]
    if len(parts) != 2 or not all(x.isdigit() and int(x) >= 1 for x in parts):
        raise ConfigError(f"legend_cell {value!r}: use 'auto' or ROW,COL (1-based, e.g. 4,2)")
    return (int(parts[0]), int(parts[1]))


def validate_composite(settings, n_panels=None):
    """Raise ConfigError for invalid composite settings; return a cleaned copy.

    ``n_panels`` (when known) also checks that every span names an existing panel.
    """
    out = {}
    for key, value in (settings or {}).items():
        if key not in COMPOSITE_KEYS:
            raise ConfigError(f"unknown composite setting {key!r} (allowed: {', '.join(COMPOSITE_KEYS)})")
        if value is None:
            continue
        if key == "label_format":
            if value not in LABEL_FORMATS:
                raise ConfigError(f"label_format must be one of {', '.join(LABEL_FORMATS)}")
        elif key == "label_pt":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ConfigError("label_pt must be a finite number")
            value = float(value)
            if not LABEL_PT_RANGE[0] <= value <= LABEL_PT_RANGE[1]:
                raise ConfigError(f"label_pt must lie in {LABEL_PT_RANGE[0]:g}-{LABEL_PT_RANGE[1]:g} pt")
        elif key == "layout":
            if value not in LAYOUT_MODES:
                raise ConfigError(f"layout must be one of {', '.join(LAYOUT_MODES)}")
        elif key == "spans":
            if not isinstance(value, dict):
                raise ConfigError("spans must be an object {panel id: 'row' | 'COLSxROWS'}")
            clean = {}
            for pid, v in value.items():
                if not (isinstance(pid, str) and len(pid) == 1 and pid in PANEL_IDS):
                    raise ConfigError(f"span panel id {pid!r} must be one lowercase letter a-z "
                                      "(input order, independent of the label format)")
                if n_panels is not None and PANEL_IDS.index(pid) >= n_panels:
                    raise ConfigError(f"span {pid}={v}: there is no panel {pid!r} "
                                      f"(only {n_panels} panels: a-{PANEL_IDS[n_panels - 1]})")
                cs, rs = parse_span_value(pid, v)
                clean[pid] = "row" if cs == "row" else f"{cs}x{rs}"
            value = dict(sorted(clean.items()))
        elif key == "empty_cells":
            if value not in EMPTY_CELL_USES:
                raise ConfigError(f"empty_cells must be one of {', '.join(EMPTY_CELL_USES)}")
        elif key == "legend_cell":
            c = parse_legend_cell(value)
            value = "auto" if c == "auto" else f"{c[0]},{c[1]}"
        elif key == "shared_legend":
            if not isinstance(value, bool):
                raise ConfigError("shared_legend must be true/false")
        elif key == "legend_entries":
            if not isinstance(value, list):
                raise ConfigError("legend_entries must be a list of 'Label=color[:style]' strings")
            for e in value:
                parse_legend_entry(e)
            value = list(value)
        out[key] = value
    if out.get("empty_cells") == "legend" and not out.get("legend_entries") and not out.get("shared_legend"):
        raise ConfigError("empty_cells 'legend' needs legend_entries ('Label=color[:style]', at least one)")
    return out


def composite_config_path(directory=None):
    return config_dir(directory) / COMPOSITE_CONFIG_NAME


def load_composite(directory=None):
    """Saved composite settings (validated) or None if no file exists."""
    path = composite_config_path(directory)
    if not path.exists():
        return None
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return validate_composite(cfg.get("composite") or {})


def save_composite(settings, directory=None):
    """Write the validated settings; empty spans/entries are dropped so the file only holds real choices."""
    settings = validate_composite(settings)
    settings = {k: v for k, v in settings.items() if v not in ({}, [])}
    path = composite_config_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"composite": settings}, indent=2) + "\n", encoding="utf-8")
    return path


def describe_composite(settings):
    s = settings or {}
    fmt = s.get("label_format")
    pt = s.get("label_pt")
    layout = s.get("layout", LAYOUT_DEFAULT)
    ign = "  [ignored in auto: (a) 14 pt]" if layout == "auto" and (
        (fmt and fmt != LABEL_FORMAT_DEFAULT) or (pt is not None and pt != LABEL_PT_DEFAULT)) else ""
    lines = [f"  label format: {fmt if fmt else 'default (' + LABEL_FORMAT_DEFAULT + ')'}"
             f"   label size: {f'{pt:g} pt' if pt is not None else f'default ({LABEL_PT_DEFAULT:g} pt)'}{ign}"]
    spans = s.get("spans") or {}
    lines.append(f"  layout: {layout if 'layout' in s else 'default (' + LAYOUT_DEFAULT + ')'}"
                 f"   spans: {', '.join(f'{k}={v}' for k, v in spans.items()) if spans else 'none'}")
    entries = s.get("legend_entries") or []
    shared = s.get("shared_legend")
    lines.append(f"  shared legend: {'on' if shared else 'off' if shared is False else 'default (off)'}"
                 + ("  (per-panel legends suppressed; entries default to the panel line handles; "
                    "uses an empty cell)" if shared else ""))
    lines.append(f"  empty cells: {'legend (shared legend)' if shared else s.get('empty_cells', 'default (' + EMPTY_CELLS_DEFAULT + ')')}"
                 f"   legend cell: {s.get('legend_cell', 'default (' + LEGEND_CELL_DEFAULT + ')')}"
                 f"   legend entries: {'; '.join(entries) if entries else ('panel line handles' if shared else 'none')}")
    return "\n".join(lines)
