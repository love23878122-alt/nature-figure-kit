"""Plain terminal menu for per-figure axis settings (VS Code terminal friendly).

    python figmenu.py --data DIR [--out DIR] [--config-dir DIR] [--double-column]
                      [--script FILE] [--transcript FILE]

Pick a figure (1-10), then its x axis, y axis or colour bar (where present):

    v  show/hide the axis            M  toggle major ticks     m  toggle minor ticks
    t  major tick step (or 'auto')   n  minimum (or 'auto')     x  maximum (or 'auto')
    h  hide tick numbers only (toggle): tick marks and the axis label stay; the
       numeric offset (x10^n), when present, is hidden with the numbers
    l  label: name, then unit (saved as xlabel / ylabel / cbar_label). Each
       prompt takes text, 'auto' (= spec default) or Enter (= keep); the unit also
       takes 'none' (no unit). Mathtext works: cm$^{-1}$, 2$\theta$, x$_{2}$; the
       Unicode superscripts cm⁻¹ (U+207B U+00B9) are converted to cm$^{-1}$, and a
       superscript minus is set as the halfwidth hyphen. The final label is
       measured; a WARNING names the figure and axis if it is longer than its span.

Figure level: r render, s save config, l reload saved config, d reset to spec
defaults, p print settings, b back. Also, where the figure has them:
    g  legend text (03/04): 'Control; Target' (one per line), 'auto' = defaults
    i  acquisition interval in s (06/08/09): x becomes Time (s), or Time (min)
       when the span exceeds 300 s; 'auto' = acquisition number
Main level: q quit.

Main level ``c``: composite settings (all composites, 89 and 183 mm):

    f  label format: (a)  a  a)  a.  (A)  A  A)  A.   (or 'auto' = default (a))
    z  label size in pt, 6-24 (or 'auto' = default 14 pt)
    a  layout: manual / auto (or 'default' = manual). Auto fixes labels at (a) 14 pt;
       differing label settings stay saved but are shown as ignored.
    g  spans: 'a=row' or 'b=2x1' adds/replaces one, 'a=' removes a, 'none' clears all
       (ids are the input-order letters of --composite-panels, whatever the label format)
    e  empty cells: blank / legend (or 'default' = blank)
    k  legend cell: auto (last empty cell in reading order) or ROW,COL (1-based)
    o  legend entries: 'Label=color[:style[:marker]]; ...' or 'none'
       (with a shared legend: 'none' = use the panel line handles)
    h  shared legend: on / off (or 'default' = off). On = one legend in an empty
       cell for the whole figure, per-panel legends suppressed, entries default
       to the panel line handles; user entries are checked against them
    r  render a composite preview (--composite-panels, default 01_IR 03_TPC_overlay)
    s  save   l  reload saved   d  reset to defaults   p  print   b  back

Saved as <config-dir>/composite.json and applied by make_composite.py (and
run_composites.py --config-dir) unless --no-config or explicit CLI flags. The
preview always passes every displayed value explicitly (labels, --layout, --span
or --span none, --empty-cells, --legend-cell, --legend-entry), so an unsaved reset
renders the displayed defaults even when an older composite.json is on disk.
Invalid values are rejected with the validation message and the previous
settings are kept; a failed render (for example no auto layout fits) is reported
and the menu stays open.

Spec defaults (shown in the menu header, taken from paper_style): 89 mm wide
(183 mm with --double-column), Arial Bold 12 pt axis/colour-bar labels and 10 pt
tick labels, offsets, legends and annotations at final size. The menu only
changes axis visibility, ticks, tick numbers, step, limits, label text, legend
text and the heatmap interval; type sizes stay at the spec.

Configs are saved as <config-dir>/<figure>.json (default $FIGSTYLE_CONFIG_DIR or
figure_configs/ next to this tool) and are loaded automatically by
make_figures.py and make_composite.py. Renders go to --out (default menu_out/).

Non-interactive use: pipe the keystrokes (``python figmenu.py ... < keys.txt``) or
pass ``--script keys.txt``; blank lines and lines starting with '#' are ignored
in scripts. Every prompt and answer is echoed so the session forms a transcript.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import figure_config as fc  # noqa: E402

AXIS_KEYS = {"x": "x", "y": "y", "c": "colorbar"}
# Spec-default tick state per axis where it differs from "major on, minor off".
DEFAULT_MINOR = {("04_TPC_overlay_logtime", "x"): True}


def spec_defaults_line(double_column=False):
    import paper_style as ps
    width = ps.DOUBLE_COLUMN_MM if double_column else ps.SINGLE_COLUMN_MM
    return (f"Spec defaults: {width:g} mm wide, Arial Bold {ps.AXIS_LABEL_PT:g} pt axis/colour-bar labels, "
            f"{ps.TICK_PT:g} pt ticks/offsets/legends/annotations, >= {ps.MIN_DPI} dpi RGB TIFF (LZW, sRGB)")


class Session:
    def __init__(self, args, lines=None):
        self.args = args
        self.lines = lines
        self.log = open(args.transcript, "w", encoding="utf-8") if args.transcript else None
        self.renderer = None

    # ---------------------------------------------------------------- io
    def say(self, text=""):
        print(text, flush=True)
        if self.log:
            self.log.write(text + "\n")
            self.log.flush()

    def ask(self, prompt):
        if self.lines is not None:
            while self.lines:
                line = self.lines.pop(0).rstrip("\n")
                if line.strip() and not line.lstrip().startswith("#"):
                    break
            else:
                line = "q"
            self.say(f"{prompt}{line}")
            return line.strip()
        try:
            line = input(prompt)
        except EOFError:
            line = "q"
            print()
        if self.log:
            self.log.write(f"{prompt}{line}\n")
        if not sys.stdin.isatty():
            print(line, flush=True)  # echo piped input so stdout reads as a transcript
        return line.strip()

    # ------------------------------------------------------------ render
    def render(self, name, cfg):
        if self.renderer is None:
            self.renderer = Renderer(self.args)
        path = self.renderer.render(name, cfg)
        self.say(f"  rendered {path}")
        for w in self.renderer.last_warnings:
            self.say(f"  {w}")

    # -------------------------------------------------------------- menus
    def run(self):
        names = list(fc.AXES)
        self.say(f"Figure axis menu. Config dir: {fc.config_dir(self.args.config_dir).resolve()}")
        self.say(spec_defaults_line(self.args.double_column))
        while True:
            self.say("")
            self.say("== Figures ==")
            for i, n in enumerate(names, 1):
                saved = " [saved config]" if fc.config_path(n, self.args.config_dir).exists() else ""
                self.say(f" {i:2d}) {n}{saved}")
            saved = " [saved config]" if fc.composite_config_path(self.args.config_dir).exists() else ""
            self.say(f"  c) composite labels, layout and spans{saved}")
            self.say("  q) quit")
            choice = self.ask("figure> ")
            if choice.lower() in ("q", "quit", "exit"):
                self.say("bye")
                return 0
            if choice == "c":
                self.composite_menu()
                continue
            if choice in names:
                self.figure_menu(choice)
            elif choice.isdigit() and 1 <= int(choice) <= len(names):
                self.figure_menu(names[int(choice) - 1])
            else:
                self.say(f"  ! unknown choice {choice!r}")

    def figure_menu(self, name):
        try:
            cfg = fc.load(name, self.args.config_dir) or fc.empty(name)
            if cfg["axes"] or any(k in cfg for k in ("labels", "legend", "heatmap")):
                self.say(f"  loaded saved config {fc.config_path(name, self.args.config_dir)}")
        except (fc.ConfigError, ValueError) as exc:
            self.say(f"  ! saved config invalid ({exc}); starting from spec defaults")
            cfg = fc.empty(name)
        axes = fc.AXES[name]
        while True:
            self.say("")
            self.say(f"== {name} ==")
            self.say(fc.describe(name, cfg))
            opts = "  x) x axis   y) y axis" + ("   c) colour bar" if "colorbar" in axes else "")
            if name in fc.DEFAULT_LEGEND:
                opts += "   g) legend text"
            if name in fc.HEATMAPS:
                opts += "   i) acquisition interval"
            self.say(opts)
            self.say("  r) render   s) save   l) reload saved   d) reset to defaults   p) print   b) back")
            choice = self.ask(f"{name}> ")
            if choice in AXIS_KEYS and AXIS_KEYS[choice] in axes:
                self.axis_menu(name, cfg, AXIS_KEYS[choice])
            elif choice == "g" and name in fc.DEFAULT_LEGEND:
                self.legend_text(name, cfg)
            elif choice == "i" and name in fc.HEATMAPS:
                self.heatmap_interval(name, cfg)
            elif choice == "r":
                try:
                    self.render(name, cfg)
                except Exception as exc:  # report and stay in the menu
                    self.say(f"  ! render failed: {type(exc).__name__}: {exc}")
            elif choice == "s":
                path = fc.save(cfg, self.args.config_dir)
                self.say(f"  saved {path}")
            elif choice == "l":
                loaded = fc.load(name, self.args.config_dir)
                cfg = loaded or fc.empty(name)
                self.say("  reloaded saved config" if loaded else "  no saved config; spec defaults")
            elif choice == "d":
                cfg = fc.empty(name)
                self.say("  reset to spec defaults (not saved)")
            elif choice == "p":
                self.say(fc.describe(name, cfg))
            elif choice in ("b", "back", "q"):
                return
            else:
                self.say(f"  ! unknown choice {choice!r}")

    def legend_text(self, name, cfg):
        n = len(fc.DEFAULT_LEGEND[name])
        raw = self.ask(f"  legend text ({n} labels separated by ';', 'auto' = "
                       f"{'; '.join(fc.DEFAULT_LEGEND[name])})> ")
        new = copy.deepcopy(cfg)
        if raw.lower() in ("auto", "default", ""):
            new.pop("legend", None)
        else:
            new["legend"] = {"labels": [t.strip() for t in raw.split(";")]}
        try:
            clean = fc.validate(new)
        except fc.ConfigError as exc:
            self.say(f"  ! rejected: {exc}")
            return
        cfg.clear()
        cfg.update(clean)
        self.say(f"  legend text: {'; '.join(fc.legend_labels(name, cfg))}")

    def heatmap_interval(self, name, cfg):
        raw = self.ask("  acquisition interval in s (number, optional start: '2' or '2 start=10'; "
                       "'auto' = acquisition number)> ")
        new = copy.deepcopy(cfg)
        if raw.lower() in ("auto", "default", "none", ""):
            new.pop("heatmap", None)
        else:
            parts = raw.split()
            try:
                h = {"interval_s": float(parts[0])}
                for extra in parts[1:]:
                    k, _, v = extra.partition("=")
                    if k not in ("start", "start_s"):
                        raise ValueError(extra)
                    h["start_s"] = float(v)
            except ValueError:
                self.say(f"  ! not a number: {raw!r}")
                return
            new["heatmap"] = h
        try:
            clean = fc.validate(new)
        except fc.ConfigError as exc:
            self.say(f"  ! rejected: {exc}")
            return
        cfg.clear()
        cfg.update(clean)
        h = cfg.get("heatmap")
        self.say(f"  x axis: {'elapsed time, interval %g s' % h['interval_s'] if h else 'acquisition number'}")

    def composite_menu(self):
        d = self.args.config_dir
        n_panels = len(self.args.composite_panels)
        try:
            cfg = fc.load_composite(d) or {}
            if cfg:
                self.say(f"  loaded saved config {fc.composite_config_path(d)}")
        except (fc.ConfigError, ValueError) as exc:
            self.say(f"  ! saved composite config invalid ({exc}); starting from spec defaults")
            cfg = {}
        while True:
            self.say("")
            self.say("== composite labels, layout and spans ==")
            self.say(fc.describe_composite(cfg))
            self.say(f"  preview panels: {' '.join(f'{fc.PANEL_IDS[i]}={p}' for i, p in enumerate(self.args.composite_panels))}"
                     f"   width: {'183' if self.args.double_column else '89'} mm")
            self.say(f"  f) format {'/'.join(fc.LABEL_FORMATS)}   z) size (pt, "
                     f"{fc.LABEL_PT_RANGE[0]:g}-{fc.LABEL_PT_RANGE[1]:g})   a) layout manual/auto")
            self.say("  g) spans (a=row, b=2x1, a=, none)   e) empty cells blank/legend   k) legend cell   "
                     "o) legend entries   h) shared legend on/off")
            self.say("  r) render composite   s) save   l) reload saved   d) reset to defaults   p) print   b) back")
            choice = self.ask("composite> ")
            new = copy.deepcopy(cfg)
            if choice in ("f", "z"):
                key = "label_format" if choice == "f" else "label_pt"
                raw = self.ask(f"  {key} ({'one of ' + ' '.join(fc.LABEL_FORMATS) if choice == 'f' else 'pt'}"
                               f" or 'auto')> ")
                if raw.lower() in ("auto", "default", ""):
                    new.pop(key, None)
                elif key == "label_pt":
                    try:
                        new[key] = float(raw)
                    except ValueError:
                        self.say(f"  ! not a number: {raw!r}")
                        continue
                else:
                    new[key] = raw
            elif choice == "a":
                raw = self.ask("  layout (manual, auto or 'default')> ").lower()
                if raw in ("default", ""):
                    new.pop("layout", None)
                else:
                    new["layout"] = raw
            elif choice == "g":
                raw = self.ask("  span (ID=row | ID=COLSxROWS | ID= to remove | none)> ")
                spans = dict(new.get("spans") or {})
                if raw.lower() in ("none", "clear"):
                    spans = {}
                elif "=" in raw and not raw.split("=", 1)[1].strip():
                    pid = raw.split("=", 1)[0].strip()
                    if pid not in spans:
                        self.say(f"  ! no span for {pid!r} to remove")
                        continue
                    spans.pop(pid)
                else:
                    try:
                        spans.update(fc.parse_span_items([raw]))
                    except fc.ConfigError as exc:
                        self.say(f"  ! rejected: {exc}")
                        continue
                new["spans"] = spans
                if not spans:
                    new.pop("spans")
            elif choice == "e":
                raw = self.ask("  empty cells (blank, legend or 'default')> ").lower()
                if raw in ("default", ""):
                    new.pop("empty_cells", None)
                else:
                    new["empty_cells"] = raw
            elif choice == "k":
                raw = self.ask("  legend cell (auto or ROW,COL)> ")
                if raw.lower() in ("default", ""):
                    new.pop("legend_cell", None)
                else:
                    new["legend_cell"] = raw
            elif choice == "h":
                raw = self.ask("  shared legend (on, off or 'default')> ").lower()
                if raw in ("default", ""):
                    new.pop("shared_legend", None)
                elif raw in ("on", "off", "true", "false", "yes", "no"):
                    new["shared_legend"] = raw in ("on", "true", "yes")
                else:
                    self.say(f"  ! rejected: shared legend must be on or off, not {raw!r}")
                    continue
            elif choice == "o":
                raw = self.ask("  legend entries ('Label=color[:style]; ...' or none)> ")
                if raw.lower() in ("none", "default", ""):
                    new.pop("legend_entries", None)
                else:
                    new["legend_entries"] = [e.strip() for e in raw.split(";") if e.strip()]
            elif choice == "r":
                try:
                    self.render_composite(cfg)
                except (Exception, SystemExit) as exc:  # report and stay in the menu
                    self.say(f"  ! render failed: {type(exc).__name__}: {exc}")
                continue
            elif choice == "s":
                try:
                    self.say(f"  saved {fc.save_composite(cfg, d)}")
                except fc.ConfigError as exc:
                    self.say(f"  ! not saved: {exc}")
                continue
            elif choice == "l":
                try:
                    loaded = fc.load_composite(d)
                except (fc.ConfigError, ValueError) as exc:
                    self.say(f"  ! saved composite config invalid ({exc}); settings unchanged")
                    continue
                cfg = loaded or {}
                self.say("  reloaded saved config" if loaded is not None else "  no saved config; spec defaults")
                continue
            elif choice == "d":
                cfg = {}
                self.say("  reset to spec defaults (not saved)")
                continue
            elif choice == "p":
                self.say(fc.describe_composite(cfg))
                continue
            elif choice in ("b", "back", "q"):
                return
            else:
                self.say(f"  ! unknown choice {choice!r}")
                continue
            try:
                cfg = fc.validate_composite(new, n_panels=n_panels)
            except fc.ConfigError as exc:
                self.say(f"  ! rejected: {exc}")

    def render_composite(self, cfg):
        import json

        import make_composite as mc
        out_dir = Path(self.args.out).resolve()
        n = 1   # never overwrite an earlier preview: composite_preview_01.tiff, _02 ...
        while (out_dir / f"composite_preview_{n:02d}.tiff").exists() or \
                (out_dir / f"composite_preview_{n:02d}.nofit.json").exists():
            n += 1
        out = out_dir / f"composite_preview_{n:02d}.tiff"
        argv = ["--data", str(self.args.data), "--manifest", str(self.args.manifest), "--out", str(out),
                "--font", self.args.font, "--panels", *self.args.composite_panels]
        if self.args.double_column:
            argv.append("--double-column")
        argv += ["--config-dir", str(fc.config_dir(self.args.config_dir))]
        # Always pass the values the menu shows (unset = default), so an unsaved reset
        # to defaults is not overridden by an older saved composite.json.
        layout = cfg.get("layout", fc.LAYOUT_DEFAULT)
        argv += ["--layout", layout]
        if layout == "manual":
            argv += ["--label-format", cfg.get("label_format", fc.LABEL_FORMAT_DEFAULT),
                     "--label-pt", f"{cfg.get('label_pt', fc.LABEL_PT_DEFAULT):g}"]
        else:   # auto fixes (a) / 14 pt; displayed label settings are shown as ignored
            argv += ["--label-format", fc.LABEL_FORMAT_DEFAULT, "--label-pt", f"{fc.LABEL_PT_DEFAULT:g}"]
        spans = cfg.get("spans") or {}
        argv += [a for k, v in spans.items() for a in ("--span", f"{k}={v}")] if spans else ["--span", "none"]
        argv += ["--empty-cells", cfg.get("empty_cells", fc.EMPTY_CELLS_DEFAULT),
                 "--legend-cell", cfg.get("legend_cell", fc.LEGEND_CELL_DEFAULT)]
        for e in cfg.get("legend_entries") or []:
            argv += ["--legend-entry", e]
        argv.append("--shared-legend" if cfg.get("shared_legend") else "--no-shared-legend")
        self.say(f"  make_composite {' '.join(argv[argv.index('--layout'):])}")
        rc = mc.main(argv)
        if rc != 0 and not out.exists():
            nofit = out.with_suffix(".nofit.json")
            if nofit.exists():
                w = json.loads(nofit.read_text())["warning"]
                self.say(f"  ! render failed (rc={rc}): {w}")
            else:
                self.say(f"  ! render failed (rc={rc}): {mc.LAST_ERROR or 'see the messages above'}")
            return
        rec = json.loads(out.with_suffix(".json").read_text())
        lab = rec["label"]
        auto = rec.get("auto_layout") or {}
        self.say(f"  rendered {out} (rc={rc}): {rec['width_mm']:g} x {rec['height_mm']:.1f} mm, grid "
                 f"{rec['grid'][0]}x{rec['grid'][1]}, layout {'auto' if auto else 'manual'}"
                 f"{' (FORCED)' if auto.get('forced') else ''}")
        self.say(f"    labels {lab['texts']} {lab['font_family']} {lab['font_style']} "
                 f"{lab['actual_pt']:.3f} pt ({lab['truetype_px']} px @ composite dpi)")
        pos = ", ".join(f"{p['panel']}@{p['row'] + 1},{p['col'] + 1}"
                        f"{'' if (p['col_span'], p['row_span']) == (1, 1) else ' %dx%d' % (p['col_span'], p['row_span'])}"
                        for p in rec["positions"])
        ec = rec["empty_cells"]
        self.say(f"    positions {pos}; empty cells {ec['cells_rc_1based'] or 'none'} ({ec['use']}"
                 f"{', legend at %d,%d' % tuple(rec['legend']['cell_rc_1based']) if rec.get('legend') else ''})")
        if rec.get("legend"):
            leg = rec["legend"]
            self.say(f"    legend: {'shared, ' if leg.get('shared_legend') else ''}entries from "
                     f"{leg.get('entries_source') or 'legend_entries'}: "
                     f"{'; '.join(t['text'] for t in leg['texts'])}")
            for w in leg.get("mismatch_warnings") or []:
                self.say(f"    {w}")
        for w in rec.get("label_warnings") or []:
            self.say(f"    {w}")
        if auto:
            self.say(f"    auto: {auto['selection_reason']}")
        # PNG preview for quick viewing (TIFF stays the deliverable).
        from PIL import Image
        with Image.open(out) as im:
            s = 150 / float(im.info["dpi"][0])
            im.convert("RGB").resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                                     Image.LANCZOS).save(out.with_suffix(".preview.png"), dpi=(150, 150))
        self.say(f"    preview {out.with_suffix('.preview.png')}")

    def axis_menu(self, name, cfg, axis):
        geo = fc.AXES[name][axis]
        while True:
            s = cfg["axes"].get(axis, {})
            minor_default = DEFAULT_MINOR.get((name, axis), False)
            state = lambda k, d: ("on" if s[k] else "off") if k in s else f"default ({'on' if d else 'off'})"  # noqa: E731
            num = lambda k: f"{s[k]:g}" if k in s else "auto"  # noqa: E731
            self.say("")
            self.say(f"== {name} / {axis} [{geo['scale']}, {geo['direction']}] ==")
            self.say(f"  v) visible: {state('visible', True)}   M) major ticks: {state('major_ticks', True)}"
                     f"   m) minor ticks: {state('minor_ticks', minor_default)}")
            step_unit = " decades" if geo["scale"] == "log" else ""
            self.say(f"  t) major step: {num('major_step')}{step_unit}   n) min: {num('min')}   x) max: {num('max')}")
            hide = "on" if s.get("tick_labels") is False else "off"
            lkey = fc.AXIS_LABEL_KEY[axis]
            lab = (cfg.get("labels") or {}).get(lkey)
            self.say(f"  h) hide tick numbers only: {hide}{'' if 'tick_labels' in s else ' (default)'}"
                     f"   l) label ({lkey}): '{fc.label_for(name, lkey, cfg)}'{'' if lab else ' (default)'}")
            self.say("  b) back")
            choice = self.ask(f"{name}/{axis}> ")
            new = dict(s)
            if choice == "v":
                new["visible"] = not s.get("visible", True)
            elif choice == "M":
                new["major_ticks"] = not s.get("major_ticks", True)
            elif choice == "m":
                new["minor_ticks"] = not s.get("minor_ticks", minor_default)
            elif choice in ("t", "n", "x"):
                key = {"t": "major_step", "n": "min", "x": "max"}[choice]
                raw = self.ask(f"  {key} (number or 'auto')> ")
                if raw.lower() in ("auto", "default", ""):
                    new.pop(key, None)
                else:
                    try:
                        new[key] = float(raw)
                    except ValueError:
                        self.say(f"  ! not a number: {raw!r}")
                        continue
            elif choice == "h":
                # stored as tick_labels: false (absent = numbers shown)
                if s.get("tick_labels") is False:
                    new.pop("tick_labels", None)
                else:
                    new["tick_labels"] = False
            elif choice == "l":
                self.edit_label(name, cfg, fc.AXIS_LABEL_KEY[axis])
                continue
            elif choice in ("b", "back", "q"):
                return
            else:
                self.say(f"  ! unknown choice {choice!r}")
                continue
            try:
                cleaned = fc.validate_axis(name, axis, new)
            except fc.ConfigError as exc:
                self.say(f"  ! rejected: {exc}")
                continue
            if cleaned:
                cfg["axes"][axis] = cleaned
            else:
                cfg["axes"].pop(axis, None)


    def edit_label(self, name, cfg, key):
        d_name, d_unit = fc.default_label(name, key)
        cur = dict((cfg.get("labels") or {}).get(key) or {})
        raw = self.ask(f"  {key} name (text, 'auto' = '{d_name}', Enter = keep '{cur.get('name', d_name)}')> ")
        if raw.lower() in ("auto", "default"):
            cur.pop("name", None)
        elif raw:
            cur["name"] = raw
        raw = self.ask(f"  {key} unit (text, 'none' = no unit, 'auto' = '{d_unit or 'none'}', "
                       f"Enter = keep '{cur.get('unit', d_unit) or 'none'}')> ")
        if raw.lower() in ("auto", "default"):
            cur.pop("unit", None)
        elif raw.lower() == "none":
            cur["unit"] = ""
        elif raw:
            cur["unit"] = raw
        labels = dict(cfg.get("labels") or {})
        if cur:
            labels[key] = cur
        else:
            labels.pop(key, None)
        try:
            clean = fc.validate_labels(name, labels)
        except fc.ConfigError as exc:
            self.say(f"  ! rejected: {exc}")
            return
        if clean:
            cfg["labels"] = clean
        else:
            cfg.pop("labels", None)
        self.say(f"  {key}: '{fc.label_for(name, key, cfg)}'{' (default)' if key not in clean else ''}")


class Renderer:
    """Re-render one figure through the make_figures pipeline with given overrides."""

    def __init__(self, args):
        import make_figures as mf
        import paper_style as ps
        import plot_figures as pf
        self.pf, self.ps = pf, ps
        _, problems = mf.verify_sources(args.data, args.manifest, pf.INPUT_FILES)
        if problems:
            raise RuntimeError(f"source verification failed: {problems}")
        self.last_warnings = []
        self.font = ps.resolve_font(args.font)
        ps.apply_style(self.font)
        self.args = args

    def render(self, name, cfg):
        pf, ps = self.pf, self.ps
        ps.apply_style(self.font)
        width = ps.DOUBLE_COLUMN_MM if self.args.double_column else ps.SINGLE_COLUMN_MM
        ctx = pf.Context(data=Path(self.args.data).resolve(), out=Path(self.args.out).resolve(),
                         dpi=ps.MIN_DPI, font=self.font, width_mm=width, only={name},
                         overrides={name: copy.deepcopy(cfg)})
        pf.render_all(ctx)
        self.last_warnings = list(ctx.warnings)
        return ctx.out / f"{name}.tiff"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=HERE / "data", help="raw-data directory (read-only)")
    ap.add_argument("--out", type=Path, default=HERE / "menu_out", help="render output directory")
    ap.add_argument("--config-dir", type=Path, default=None,
                    help="config directory (default $FIGSTYLE_CONFIG_DIR or figure_configs/)")
    ap.add_argument("--manifest", type=Path, default=HERE / "qa" / "data_manifest.json")
    ap.add_argument("--double-column", action="store_true", help="render previews at 183 mm")
    ap.add_argument("--composite-panels", nargs="+", default=["01_IR", "03_TPC_overlay"],
                    help="panels for the composite-label preview render (as make_composite.py --panels)")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--script", type=Path, default=None, help="file of menu keystrokes (one per line)")
    ap.add_argument("--transcript", type=Path, default=None, help="also write the session to this file")
    args = ap.parse_args(argv)
    lines = args.script.read_text(encoding="utf-8").splitlines() if args.script else None
    return Session(args, lines).run()


if __name__ == "__main__":
    sys.exit(main())
