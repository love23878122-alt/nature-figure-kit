"""Single entry point: verify raw inputs, render the figures as RGB LZW TIFF (sRGB ICC).

    python make_figures.py --data DIR --out DIR [--double-column] [--only NAMES]
                           [--manifest FILE] [--dpi N] [--font Arial]
                           [--font-substitute FAMILY] [--clearance-mm 1.5]
                           [--failure-report FILE] [--config-dir DIR] [--no-config]
                           [--palette NAME]

--palette NAME (for example nature-6c-2; list: python palettes.py) switches the
series colours of the line figures for this run; a figure config "palette" key
wins. Without it the figures keep their spec colours.

Saved axis overrides (written by figmenu.py) are loaded automatically from
--config-dir (default: $FIGSTYLE_CONFIG_DIR or figure_configs/ next to this
tool) as <config-dir>/<figure>.json; unset options keep the spec defaults.

Canvas: 89 mm wide (single column, default; starts at 60 mm tall) or 183 mm with
--double-column (starts at 105 mm); 05 derives its height from the square image.
The height grows in 1 mm steps when a vertical axis or colour-bar label would be
longer than its data box. Type at final size: Arial Bold 12 pt axis and
colour-bar labels; 10 pt tick labels, scientific offsets, legends, annotations.

Exit codes: 0 rendered, 2 source verification failed (nothing rendered),
3 font unavailable, 1 other error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DEFAULT_MANIFEST = HERE / "qa" / "data_manifest.json"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sources(data_dir, manifest_path, names):
    """Return (digests, problems); problems lists every missing/unreadable/mismatched item."""
    problems, digests = [], {}
    try:
        reference = json.loads(Path(manifest_path).read_text(encoding="utf-8"))["source_sha256"]
    except Exception as exc:  # unreadable manifest or missing key
        return {}, [{"file": str(manifest_path), "reason": f"manifest unreadable: {type(exc).__name__}: {exc}"}]
    for name in names:
        expected = reference.get(name)
        if not expected:
            problems.append({"file": name, "reason": "reference digest missing from manifest"})
        try:
            digests[name] = sha256(Path(data_dir) / name)
        except OSError as exc:
            problems.append({"file": name, "reason": f"input unreadable: {exc.strerror or exc}"})
            continue
        if expected and digests[name] != expected:
            problems.append({"file": name, "reason": "SHA-256 mismatch",
                             "expected": expected, "actual": digests[name]})
    return digests, problems


def write_failure_report(path, stage, problems, args):
    lines = ["# Figure run stopped", "",
             f"- Time: {dt.datetime.now().isoformat(timespec='seconds')}",
             f"- Stage: {stage}", f"- Data: `{args.data}`", f"- Manifest: `{args.manifest}`", "",
             "| File | Reason |", "|---|---|"]
    lines += [f"| `{p['file']}` | {p['reason']} |" for p in problems]
    lines += ["", "No figures were rendered from unverified inputs."]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    import plot_figures as pf

    import paper_style as _ps
    ps_single = _ps.SINGLE_COLUMN_MM
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, type=Path, help="directory holding the six raw inputs (read-only)")
    parser.add_argument("--out", required=True, type=Path, help="output directory (TIFFs; qa/ and source_data/ inside)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help="JSON with source_sha256 {filename: digest} (default: qa/data_manifest.json next to this tool)")
    parser.add_argument("--double-column", action="store_true",
                        help=f"183 mm wide canvas (default {ps_single} mm single column)")
    parser.add_argument("--only", default=None,
                        help="comma-separated figure basenames to render (default: all ten)")
    parser.add_argument("--dpi", type=int, default=600,
                        help="minimum TIFF density (>= 600); image figures raise it to resolve native pixels 1:1")
    parser.add_argument("--font", default="Arial", help="required font family (bold face is used)")
    parser.add_argument("--font-substitute", default=None,
                        help="explicitly accepted stand-in if --font is missing; output is flagged as non-compliant")
    parser.add_argument("--clearance-mm", type=float, default=1.5, help="target ink-to-edge clearance")
    parser.add_argument("--failure-report", type=Path, default=None,
                        help="markdown file to write when verification or font resolution stops the run")
    parser.add_argument("--config-dir", type=Path, default=None,
                        help="per-figure axis override JSON directory (default: $FIGSTYLE_CONFIG_DIR "
                             "or figure_configs/ next to this tool)")
    parser.add_argument("--no-config", action="store_true",
                        help="ignore saved axis overrides and render spec defaults")
    parser.add_argument("--palette", default=None,
                        help="series palette id for the line figures (e.g. nature-6c-2, okabe-ito; "
                             "list: python palettes.py); a figure config 'palette' key wins")
    args = parser.parse_args(argv)
    if args.palette is not None:
        import palettes
        try:
            args.palette = palettes.validate_name(args.palette)
        except palettes.PaletteError as exc:
            parser.error(str(exc))

    args.data, args.out, args.manifest = args.data.resolve(), args.out.resolve(), args.manifest.resolve()
    if args.out == args.data or args.data in args.out.parents:
        parser.error("--out must not be inside --data (inputs are read-only)")

    # 1. Raw-data preflight.
    before, problems = verify_sources(args.data, args.manifest, pf.INPUT_FILES)
    if problems:
        print("SOURCE VERIFICATION FAILED:", json.dumps(problems, indent=2), file=sys.stderr)
        if args.failure_report:
            write_failure_report(args.failure_report, "raw-data preflight", problems, args)
        return 2
    print("SOURCE VERIFICATION PASS (6/6 SHA-256 match manifest)", flush=True)

    # 2. Font and style.
    import matplotlib
    import numpy
    import pandas
    import PIL
    import paper_style as ps
    try:
        font = ps.resolve_font(args.font, args.font_substitute)
    except ps.FontUnavailable as exc:
        print(f"FONT UNAVAILABLE: {exc}", file=sys.stderr)
        if args.failure_report:
            write_failure_report(args.failure_report, "font resolution",
                                 [{"file": args.font, "reason": str(exc)}], args)
        return 3
    ps.apply_style(font)
    if font.substitute:
        print(f"WARNING: {args.font} Bold not found; rendering with explicit substitute "
              f"{font.full_name} ({font.path}). Output is NOT Arial-compliant.", flush=True)
    else:
        print(f"FONT: {font.full_name} ({font.path})", flush=True)

    # 3. Canvas and density. Line plots use --dpi; 05 raises its own density so
    #    each native PL pixel maps to exactly one device pixel.
    if args.dpi < ps.MIN_DPI:
        parser.error(f"--dpi must be >= {ps.MIN_DPI}")
    only = None
    if args.only:
        only = {n.strip() for n in args.only.split(",") if n.strip()}
        unknown = only - set(pf.FIGURE_NAMES)
        if unknown:
            parser.error(f"unknown figure names: {sorted(unknown)}")
    width_mm = ps.DOUBLE_COLUMN_MM if args.double_column else ps.SINGLE_COLUMN_MM
    ctx = pf.Context(data=args.data, out=args.out, dpi=args.dpi, font=font,
                     clearance_mm=args.clearance_mm, width_mm=width_mm, only=only,
                     use_configs=not args.no_config, config_dir=args.config_dir, palette=args.palette)
    import figure_config as fc
    cfg_dir = fc.config_dir(args.config_dir).resolve()
    if args.no_config:
        print("AXIS OVERRIDES: disabled (--no-config)", flush=True)
    else:
        found = [n for n in pf.FIGURE_NAMES if (only is None or n in only) and fc.config_path(n, cfg_dir).exists()]
        print(f"AXIS OVERRIDES: {cfg_dir} -> {', '.join(found) if found else 'none saved (spec defaults)'}", flush=True)
    if args.palette:
        import palettes
        print(f"PALETTE (session): {palettes.describe(args.palette)}", flush=True)
    print(f"CANVAS: {width_mm:g} mm wide, default height {ctx.height_mm:g} mm; base dpi {ctx.dpi}; "
          f"figures: {'all' if only is None else ','.join(sorted(only))}", flush=True)

    # 4. Render.
    pf.render_all(ctx)

    # 5. Recheck hashes and write the run manifest.
    after, problems_after = verify_sources(args.data, args.manifest, pf.INPUT_FILES)
    unchanged = before == after and not problems_after
    manifest = {
        "tool": "make_figures.py", "created": dt.datetime.now().isoformat(timespec="seconds"),
        "command": [Path(sys.executable).name, *sys.argv],
        "data_dir": str(args.data), "reference_manifest": str(args.manifest),
        "source_sha256": before, "source_sha256_after_render": after, "sources_unchanged": unchanged,
        "base_dpi": ctx.dpi, "width_mm": width_mm, "default_height_mm": ctx.height_mm,
        "double_column": bool(args.double_column), "only": None if only is None else sorted(only),
        "font": font.as_dict(), "clearance_target_mm": args.clearance_mm, "session_palette": args.palette,
        "config_dir": None if args.no_config else str(cfg_dir), "axis_overrides": ctx.applied_configs,
        "empty_sheets": ctx.empty_sheets, "figures": ctx.records,
        "versions": {"python": platform.python_version(), "matplotlib": matplotlib.__version__,
                     "numpy": numpy.__version__, "pandas": pandas.__version__, "pillow": PIL.__version__},
    }
    (ctx.qa / "data_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not unchanged:
        print("ERROR: source files changed during rendering", file=sys.stderr)
        return 1
    print(f"RENDER COMPLETE: {len(ctx.records)} TIFFs in {ctx.out}; sources unchanged.", flush=True)
    print(f"Next: python verify_figures.py --out {ctx.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
