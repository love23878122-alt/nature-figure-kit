""""Same sample name, same colour" self-test on SYNTHETIC series only (no input files).

    python demo/test_samecolor.py [--out demo_out/samecolor_test] [--font Arial]

Design: names are resolved once for the whole run with sample_colors.resolve
(all panels' names collected first), each synthetic panel is rendered in the
house style (paper_style) as its own TIFF + evidence sidecar, and the two
panels are assembled by the kit's composite code (make_composite.py, 183 mm,
2 columns, --artwork-scale native so the panel pixels are placed 1:1).

1. Mapping: panel (a) ["MeO-2PACz", "2PACz", "Me-4PACz"], panel (b)
   ["Me-4PACz", "MeO-2PACz"] with nature-6c-2 and no pins resolve to
   MeO-2PACz=#3B549D, 2PACz=#D3272B, Me-4PACz=#6BBC46 (first appearance).
2. Same name = same hex in both panels, via the style JSON of each panel and
   via exact pixels in each panel region of the composite TIFF (2PACz's colour
   is absent from panel b).
3. Pin {"Me-4PACz": "#3B549D"}: Me-4PACz is #3B549D and no other name has it.
4. Overflow: 8 distinct names with nature-6c-2 give one WARNING; names 7-8
   cycle the first colours with dashed lines, identical in both panels (the
   second panel shows the names in reverse order).
5. Map file: validation (unknown key, bad hex), uppercase on save, the saved
   order reproduces the composite colours in a single-panel run, whitespace
   match without case folding, duplicate-pin WARNING, no palette + no pins =
   inactive.
Exit 0 = all checks pass (PASS/FAIL lines are printed, JSON in --out).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))

import numpy as np  # noqa: E402

import palettes  # noqa: E402
import sample_colors as sc  # noqa: E402

PALETTE = "nature-6c-2"
PANEL_A = ["MeO-2PACz", "2PACz", "Me-4PACz"]
PANEL_B = ["Me-4PACz", "MeO-2PACz"]
EXPECT = {"MeO-2PACz": "#3B549D", "2PACz": "#D3272B", "Me-4PACz": "#6BBC46"}
PANEL_MM = 88.0   # rendered at the 183 mm two-column cell width, placed 1:1


def hex_rgb(h):
    return np.array([int(h[k:k + 2], 16) for k in (1, 3, 5)], dtype=np.uint8)


def table_style(names, table, spec_styles=None):
    """Colours/linestyles per series from the run table (spec linestyle while it fits)."""
    colors, styles = [], []
    for i, n in enumerate(names):
        e = table[sc.clean_name(n)]
        colors.append(e["color"])
        styles.append(palettes.MPL_LINESTYLE[e["linestyle"]] if e["linestyle"]
                      else (spec_styles[i] if spec_styles else "-"))
    return colors, styles


def render_panel(out, stem, names, table, font, resolution):
    """One synthetic line panel in the house style; returns its style record."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_hex

    import paper_style as ps
    fig, ax = ps.new_figure(ps.MIN_DPI, PANEL_MM)
    x = np.linspace(0.0, 10.0, 400)
    colors, styles = table_style(names, table)
    for i, (n, c, ls) in enumerate(zip(names, colors, styles)):
        # synthetic: separated offset sines keyed to the name, not to the position
        k = sum(map(ord, n)) % 7
        ax.plot(x, 1.3 * i + 0.4 * np.sin(x + 0.5 * k), color=c, linestyle=ls,
                linewidth=ps.DATA_LINE_PT, label=n)
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.8, 1.3 * len(names) + 2.2)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Signal (a.u.)")
    ax.tick_params(which="both", top=False, right=False, labeltop=False, labelright=False)
    ax.legend(loc="upper right", ncol=2 if len(names) > 4 else 1, handlelength=2.0)
    layout = ps.fit_layout(fig, ax)
    path = out / f"{stem}.tiff"
    ps.export_tiff(fig, path)
    evidence = ps.describe_figure(fig, font, "spectrum")
    lines = [ln for ln in ax.get_lines() if not ln.get_label().startswith("_")]
    handles = [{"label": ln.get_label(), "color": to_hex(ln.get_color()).upper(),
                "linestyle": palettes.MPL_TO_NAME.get(ln.get_linestyle(), ln.get_linestyle())} for ln in lines]
    plt.close(fig)
    (out / f"{stem}.tiff.evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    rec = {"tiff": path.name, "synthetic": True, "palette": PALETTE, "series_names": names,
           "line_handles": handles, "sample_colors": {n: table[n] for n in names},
           "resolution": resolution, "clearance_mm": layout.get("clearance_mm")}
    (out / f"{stem}.style.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return rec


def compose(out, stem, tiffs, font_name):
    import make_composite as mc
    tif = out / f"{stem}.tiff"
    rc = mc.main(["--panels", *map(str, tiffs), "--out", str(tif), "--double-column", "--cols", "2",
                  "--artwork-scale", "native", "--no-config", "--font", font_name])
    rec = json.loads(tif.with_suffix(".json").read_text()) if tif.with_suffix(".json").exists() else None
    return rc, tif, rec


def region_counts(tif, rec, hexes):
    """Exact-pixel counts of each hex inside each panel's placed box (composite TIFF)."""
    from PIL import Image
    with Image.open(tif) as im:
        rgb = np.asarray(im.convert("RGB"))
    counts = {}
    for p in rec["panels"]:
        x0, y0, w, h = p["box_px"]
        sub = rgb[y0:y0 + h, x0:x0 + w].reshape(-1, 3)
        counts[p["label"]] = {hx: int((sub == hex_rgb(hx)).all(axis=1).sum()) for hx in hexes}
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=KIT / "demo_out" / "samecolor_test")
    ap.add_argument("--font", default="Arial")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    import paper_style as ps
    font = ps.resolve_font(a.font)
    ps.apply_style(font)
    checks = {}

    # 1. Mapping: all names first (panel order, then series order), then colours.
    names = sc.first_appearance([PANEL_A, PANEL_B])
    table, warns = sc.resolve(names, PALETTE)
    res = sc.resolution_record(PALETTE, names, table, warns, {}, [])
    checks["mapping: first-appearance table MeO-2PACz=#3B549D 2PACz=#D3272B Me-4PACz=#6BBC46"] = \
        {n: e["color"] for n, e in table.items()} == EXPECT and not warns
    checks["mapping: palette fits, figure linestyle kept (linestyle None), source palette"] = all(
        e["linestyle"] is None and e["source"] == "palette" for e in table.values())

    # 2. Render the two panels and compose them (183 mm, kit composite code).
    ra = render_panel(out, "panel_a", PANEL_A, table, font, res)
    rb = render_panel(out, "panel_b", PANEL_B, table, font, res)
    hx = lambda r: {h["label"]: h["color"] for h in r["line_handles"]}  # noqa: E731
    checks["JSON: panel a line colours follow the names"] = hx(ra) == {n: EXPECT[n] for n in PANEL_A}
    checks["JSON: panel b line colours follow the names (order differs, 2PACz missing)"] = \
        hx(rb) == {n: EXPECT[n] for n in PANEL_B}
    checks["JSON: same name = same hex in both panels"] = all(hx(ra)[n] == hx(rb)[n] for n in PANEL_B)
    rc, tif, crec = compose(out, "samecolor_composite_183mm", [out / "panel_a.tiff", out / "panel_b.tiff"], a.font)
    checks["composite: make_composite exit 0, 183 mm, 2 panels"] = (rc == 0 and crec is not None
                                                                   and abs(crec["width_mm"] - 183) < 1e-6
                                                                   and len(crec["panels"]) == 2)
    counts = region_counts(tif, crec, list(EXPECT.values())) if crec else {}
    pa, pb = counts.get("a", {}), counts.get("b", {})
    checks["TIFF pixels: panel a region holds exact #3B549D, #D3272B, #6BBC46"] = all(
        pa.get(EXPECT[n], 0) > 50 for n in PANEL_A)
    checks["TIFF pixels: panel b region holds exact #6BBC46 and #3B549D"] = all(
        pb.get(EXPECT[n], 0) > 50 for n in PANEL_B)
    checks["TIFF pixels: 2PACz colour #D3272B absent from panel b"] = pb.get(EXPECT["2PACz"], 1) == 0
    checks["composite: panels placed 1:1 (no resampling)"] = bool(crec) and all(
        p.get("resampled") in (None, "none (1:1)") for p in crec["panels"])
    with Image_open(tif) as im:
        checks["composite TIFF: >= 600 dpi, LZW, sRGB ICC"] = (min(im.info.get("dpi", (0, 0))) >= 600
                                                             and im.info.get("compression") == "tiff_lzw"
                                                             and bool(im.info.get("icc_profile")))

    # 3. Pin test.
    pins = {"Me-4PACz": "#3B549D"}
    ptable, pwarns = sc.resolve(names, PALETTE, pins=pins)
    checks["pin: Me-4PACz = #3B549D (source pin)"] = ptable["Me-4PACz"] == {
        "color": "#3B549D", "linestyle": None, "source": "pin", "slot": None}
    checks["pin: no other name gets #3B549D"] = all(e["color"] != "#3B549D" for n, e in ptable.items()
                                                   if n != "Me-4PACz")
    checks["pin: others take the next free colours (MeO-2PACz=#D3272B, 2PACz=#6BBC46)"] = (
        ptable["MeO-2PACz"]["color"] == "#D3272B" and ptable["2PACz"]["color"] == "#6BBC46")

    # 4. Overflow: 8 distinct names, second panel in reverse order.
    eight = [f"Sample {i}" for i in range(1, 9)]
    otable, owarns = sc.resolve(sc.first_appearance([eight, eight[::-1]]), PALETTE)
    ores = sc.resolution_record(PALETTE, eight, otable, owarns, {}, [])
    for w in owarns:
        print(w, file=sys.stderr, flush=True)
    base = palettes.get_palette(PALETTE)
    checks["overflow: exactly one WARNING"] = len(owarns) == 1 and owarns[0].startswith("WARNING")
    checks["overflow: names 7-8 cycle colours 1-2 with dashed lines"] = (
        [otable[n]["color"] for n in eight[6:]] == base[:2]
        and [otable[n]["linestyle"] for n in eight[6:]] == ["dashed", "dashed"])
    checks["overflow: names 1-6 solid, one colour each"] = (
        [otable[n]["color"] for n in eight[:6]] == base and all(otable[n]["linestyle"] == "solid" for n in eight[:6]))
    oa = render_panel(out, "overflow_panel_a", eight, otable, font, ores)
    ob = render_panel(out, "overflow_panel_b", eight[::-1], otable, font, ores)
    sty = lambda r: {h["label"]: (h["color"], h["linestyle"]) for h in r["line_handles"]}  # noqa: E731
    checks["overflow: same colour + linestyle per name in both panels"] = sty(oa) == sty(ob) and len(sty(oa)) == 8
    import contextlib
    import io
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        orc, otif, orec = compose(out, "overflow_composite_183mm",
                                  [out / "overflow_panel_a.tiff", out / "overflow_panel_b.tiff"], a.font)
    checks["overflow: composite renders (no crash)"] = orc == 0 and orec is not None

    # 5. Map file behaviour.
    mfile = out / "sample_colors.json"
    sc.save_map(mfile, {"pins": {" Me-4PACz ": "#3b549d"}, "order": []})
    saved = json.loads(mfile.read_text())
    checks["map: hex saved uppercase, name stripped"] = saved == {"pins": {"Me-4PACz": "#3B549D"}, "order": []}
    rej = []
    for bad in ({"pins": {}, "colours": {}}, {"pins": {"A": "red"}}, {"pins": {"A": "#12345"}}, {"order": "A"}):
        try:
            sc.validate_map(bad)
        except sc.SampleColorError as exc:
            rej.append(str(exc))
    checks["map: unknown key / bad hex / bad order rejected with a message"] = len(rej) == 4 and "unknown" in rej[0]
    ofile = out / "sample_colors_order.json"
    sc.save_map(ofile, {})
    _, order = sc.save_order(ofile, names)
    doc = sc.load_map(ofile)
    single, _ = sc.resolve(PANEL_B, PALETTE, pins=doc["pins"], order=doc["order"])
    checks["map: saved order reproduces the composite colours in a panel-b-only run"] = (
        order == names and all(single[n]["color"] == EXPECT[n] for n in PANEL_B))
    alone, _ = sc.resolve(PANEL_B, PALETTE)
    checks["map: without the saved order a panel-b-only run would differ (first appearance)"] = (
        alone["Me-4PACz"]["color"] == "#3B549D")
    ws, _ = sc.resolve(["  MeO-2PACz ", "meo-2pacz"], PALETTE)
    checks["names: exact after stripping whitespace, no case folding"] = list(ws) == ["MeO-2PACz", "meo-2pacz"]
    _, dw = sc.resolve(names, PALETTE, pins={"MeO-2PACz": "#123456", "2PACz": "#123456"})
    checks["pins: two pins with one colour give a WARNING"] = len(dw) == 1 and "share the colour" in dw[0]
    inactive, iw = sc.resolve(names, None)
    checks["no palette and no pins: inactive (spec colours by position)"] = (
        not sc.is_active(None, {}) and all(e["source"] == "spec" and e["color"] is None for e in inactive.values()))
    pinonly, _ = sc.resolve(names, None, pins=pins)
    checks["pins without palette: pinned name pinned, others spec"] = (
        pinonly["Me-4PACz"]["color"] == "#3B549D" and pinonly["MeO-2PACz"]["source"] == "spec")

    for k, v in checks.items():
        print(f"{'PASS' if v else 'FAIL'} samecolor: {k}")
    summary = {"checks": checks, "palette": PALETTE, "names_in_order": names,
               "table": table, "panel_tables": {"a": ra["sample_colors"], "b": rb["sample_colors"]},
               "composite": str(tif), "pixel_counts_per_panel": counts, "pin_table": ptable,
               "overflow_table": otable, "overflow_warnings": owarns, "out": str(out),
               "pass": all(checks.values())}
    (out / "test_samecolor.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"SAMECOLOR TEST {'OK' if summary['pass'] else 'FAILED'}: {sum(checks.values())}/{len(checks)} "
          f"checks; evidence {out / 'test_samecolor.json'}")
    return 0 if summary["pass"] else 1


def Image_open(path):
    from PIL import Image
    return Image.open(path)


if __name__ == "__main__":
    sys.exit(main())
