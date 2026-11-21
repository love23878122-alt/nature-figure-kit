"""Palette self-test on SYNTHETIC series only (no input files are read).

    python demo/test_palettes.py [--out demo_out/palette_test] [--font Arial]

1. nature-6c-2: six synthetic sine series at 89 mm in the house style, exported
   as TIFF + style JSON. The recorded line colours must be exactly
   #3B549D #D3272B #6BBC46 #9EAAD1 #F29091 #B4DEA2, and each colour must be
   present as exact pixels in the TIFF.
2. Overflow: 7 series from nature-3c-1 (3 colours) must warn and return cycled
   colours with solid -> dashed -> dotted linestyles (also rendered).
3. An unknown palette name must raise a clear error listing valid ids.
4. okabe-ito is selectable by name and returns its eight hex values.
5. Every catalog id loads; 36 nature-* palettes with 270 hex plus okabe-ito.
Exit 0 = all checks pass (PASS/FAIL lines are printed, JSON in --out).
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))

import numpy as np  # noqa: E402

import palettes  # noqa: E402

EXPECT_6C2 = ["#3B549D", "#D3272B", "#6BBC46", "#9EAAD1", "#F29091", "#B4DEA2"]
EXPECT_OKABE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9", "#E69F00", "#F0E442", "#000000"]


def render(out, stem, assignment, font):
    """Draw len(colors) synthetic series with the kit style; return the style record."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_hex
    from PIL import Image

    import paper_style as ps
    fig, ax = ps.new_figure(ps.MIN_DPI, ps.SINGLE_COLUMN_MM)
    x = np.linspace(0.0, 10.0, 400)
    n = assignment["n_series"]
    for i, (c, ls) in enumerate(zip(assignment["colors"], assignment["mpl_linestyles"])):
        # synthetic: well separated offset sines, no data files involved
        ax.plot(x, 1.2 * i + 0.4 * np.sin(x + 0.6 * i), color=c, linestyle=ls,
                linewidth=ps.DATA_LINE_PT, label=f"S{i + 1}")
    ax.set_xlim(0, 10)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Signal (a.u.)")
    ax.tick_params(which="both", top=False, right=False, labeltop=False, labelright=False)
    layout = ps.fit_layout(fig, ax)
    path = out / f"{stem}.tiff"
    ps.export_tiff(fig, path)
    lines = ax.get_lines()
    recorded = [to_hex(ln.get_color()).upper() for ln in lines]
    styles = [ln.get_linestyle() for ln in lines]
    plt.close(fig)
    with Image.open(path) as im:
        rgb = np.asarray(im.convert("RGB")).reshape(-1, 3)
        dpi = im.info.get("dpi")
        compression = im.info.get("compression")
    exact = {}
    for h in dict.fromkeys(recorded):
        target = np.array([int(h[k:k + 2], 16) for k in (1, 3, 5)], dtype=np.uint8)
        exact[h] = int((rgb == target).all(axis=1).sum())
    rec = {"tiff": path.name, "palette": assignment["palette"], "n_series": n,
           "palette_hex_used": recorded, "linestyles": styles,
           "assignment_linestyles": assignment["linestyles"], "overflow": assignment["overflow"],
           "warning": assignment["warning"], "exact_pixel_counts": exact,
           "dpi": [float(v) for v in dpi] if dpi else None, "compression": compression,
           "clearance_mm": layout.get("clearance_mm"), "synthetic": True}
    (out / f"{stem}.style.json").write_text(json.dumps(rec, indent=2))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=KIT / "demo_out" / "palette_test")
    ap.add_argument("--font", default="Arial")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    import paper_style as ps
    font = ps.resolve_font(a.font)
    ps.apply_style(font)

    checks = {}
    # 1. nature-6c-2 render
    asg = palettes.assign_series(6, "nature-6c-2")
    r6 = render(out, "nature-6c-2_six_series", asg, font)
    checks["nature-6c-2 get_palette == expected six hex"] = palettes.get_palette("nature-6c-2") == EXPECT_6C2
    checks["nature-6c-2 recorded line colours == expected"] = r6["palette_hex_used"] == EXPECT_6C2
    checks["nature-6c-2 every colour present as exact TIFF pixels"] = all(r6["exact_pixel_counts"][h] > 0
                                                                          for h in EXPECT_6C2)
    checks["nature-6c-2 fits: all solid, no warning"] = (r6["linestyles"] == ["-"] * 6 and not asg["overflow"]
                                                         and asg["warning"] is None)
    checks["TIFF >= 600 dpi, LZW"] = (r6["dpi"] and min(r6["dpi"]) >= 600 and r6["compression"] == "tiff_lzw")

    # 2. overflow
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ov = palettes.assign_series(7, "nature-3c-1")
    base = palettes.get_palette("nature-3c-1")
    ro = render(out, "nature-3c-1_overflow_7_series", ov, font)
    checks["overflow: PaletteOverflowWarning emitted"] = any(issubclass(w.category, palettes.PaletteOverflowWarning)
                                                            for w in caught)
    checks["overflow: colours cycle"] = ov["colors"] == [base[i % 3] for i in range(7)]
    checks["overflow: linestyle advances solid/dashed/dotted"] = ov["linestyles"] == (
        ["solid"] * 3 + ["dashed"] * 3 + ["dotted"])
    checks["overflow: warning recorded in style JSON"] = bool(ro["warning"]) and "WARNING" in ro["warning"]
    checks["overflow: rendered linestyles"] = ro["linestyles"] == ["-"] * 3 + ["--"] * 3 + [":"]

    # 3. unknown name
    try:
        palettes.get_palette("nature-99c-1")
        unknown = None
    except palettes.PaletteError as exc:
        unknown = str(exc)
    checks["unknown name raises PaletteError listing valid ids"] = bool(unknown) and "valid ids" in unknown \
        and "okabe-ito" in unknown
    try:
        palettes.assign_series(3, None)
        none_err = None
    except palettes.PaletteError as exc:
        none_err = str(exc)
    checks["assign_series requires a name"] = bool(none_err)

    # 4. okabe-ito by name
    checks["okabe-ito selectable by name, eight hex in order"] = palettes.get_palette("okabe-ito") == EXPECT_OKABE

    # 5. catalog
    ids = palettes.list_palettes()
    nat = [i for i in ids if i.startswith("nature-")]
    checks["catalog: 36 nature-* + okabe-ito, 270 nature hex"] = (len(nat) == 36 and "okabe-ito" in ids
                                                                  and len(ids) == 37
                                                                  and sum(len(palettes.get_palette(i)) for i in nat) == 270)
    checks["catalog: n matches hex length for every id"] = all(palettes.palette_info(i)["n"] == len(palettes.get_palette(i))
                                                              for i in ids)

    for k, v in checks.items():
        print(f"{'PASS' if v else 'FAIL'} palette: {k}")
    summary = {"checks": checks, "nature-6c-2": r6, "overflow": ro, "unknown_error": unknown,
               "out": str(out), "pass": all(checks.values())}
    (out / "test_palettes.json").write_text(json.dumps(summary, indent=2))
    print(f"PALETTE TEST {'OK' if summary['pass'] else 'FAILED'}: {sum(checks.values())}/{len(checks)} "
          f"checks; evidence {out / 'test_palettes.json'}")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
