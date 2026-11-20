"""Build the composite figures (both input sets, 89 mm and 183 mm).

    python run_composites.py --data data --out OUT/composite [--manifest FILE]
                             [--config-dir DIR | default: no saved overrides]

Set 1: data panels 01, 03, 04, 05 re-rendered through the pipeline at their final
       placement size (89 mm: one column; 183 mm: 2 x 2).
Set 2: imported artwork only - TIFF, PNG and PDF panels generated in
       <out>/test_inputs/<width>/ at their exact placement width so they are placed
       whole at scale 1.0 (``--artwork-scale native``); baked-in type therefore
       stays 12/10 pt. Each input carries a ``<file>.evidence.json`` renderer record
       for the text-fit QA.
         89 mm : 01_IR.tiff, 04_TPC_overlay_logtime.png, 07_mean_spectrum_vector.pdf
         183 mm: the same three plus 03_TPC_overlay.tiff (fills the 2 x 2 grid)
Default composites ignore saved menu overrides (``--no-config``) unless
--config-dir is given; panel labels then use the spec defaults (a) / 14 pt Arial
Bold (override with --label-format / --label-pt). Prints measured widths from each saved TIFF.

Batch 5 layout acceptance (``--layout-acceptance``; the example sets above are then
skipped unless ``--with-examples``): runs make_composite.py through its real CLI
(subprocess) on data panels only:
  * auto layout for 4, 6, 7 and 8 panels at 89 and 183 mm; the 7-panel case is the
    requested geometry "a=row + 2 x 3 body" (``--cols 2 --span a=row``, 2 x 4 grid);
  * ``--force`` on no-fit cases (4 panels at 89 mm, 7 panels at 183 mm);
  * a multi-row span (a=1x2), an auto layout with a legend in an empty cell, and a
    manual layout with a full-row span plus a legend;
  * invalid input: malformed, duplicate and nonexistent spans, a span wider than the
    manual grid, a 05 span, a legend without a free cell / in an occupied cell /
    without entries, and an auto label conflict (each must exit 2 with no TIFF).
Every published TIFF is checked from its tags (RGB, LZW, sRGB ICC, >= 600 dpi,
width within one pixel, height <= 247 mm unless forced) and by
text_fit_composite_labels.label_check (with composite_fit); a no-fit case must print
the WARNING with a suggestion, exit 4 and leave no TIFF. Writes
<qa-dir>/layout_acceptance.json and .md and PNG previews to <preview-dir>.
Exit 0 only if every case behaves as expected.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np  # noqa: F401
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
Image.MAX_IMAGE_PIXELS = None

INPUT_DPI = 600
INPUT_CLEARANCE_MM = 0.25   # artwork margin; the composite adds its own 1.5 mm edge clearance
GAP_MM = 3.0
EDGE_MM = 1.5
AA_PX = 2


def placement_width_mm(width_mm, ncol):
    """Width (mm, whole px at INPUT_DPI) that make_composite gives each imported panel."""
    px = lambda mm: int(round(mm / 25.4 * INPUT_DPI))  # noqa: E731
    # make_composite reserves a 2 px anti-aliasing allowance on each side of every box.
    w = (px(width_mm) - 2 * px(EDGE_MM) - (ncol - 1) * px(GAP_MM) - ncol * 2 * AA_PX) // ncol
    return w / INPUT_DPI * 25.4


def make_test_inputs(data, ti, width_mm, names):
    """Render TIFF/PNG (pipeline) and a vector PDF at the placement width, with evidence."""
    import matplotlib.pyplot as plt

    import paper_style as ps
    import plot_figures as pf
    ti.mkdir(parents=True, exist_ok=True)
    font = ps.resolve_font("Arial")
    ps.apply_style(font)
    work = ti / "_render"
    ctx = pf.Context(data=Path(data).resolve(), out=work, dpi=INPUT_DPI, font=font,
                     clearance_mm=INPUT_CLEARANCE_MM, width_mm=width_mm, only=set(names["tiff"] + names["png"]),
                     use_configs=False, write_provenance=False)
    pf.render_all(ctx)
    out = []
    for n in names["tiff"]:
        dst = ti / f"{n}.tiff"
        shutil.copyfile(work / f"{n}.tiff", dst)
        shutil.copyfile(work / "qa" / f"{n}.style.json", ti / f"{n}.tiff.evidence.json")
        out.append(dst)
    for n in names["png"]:
        dst = ti / f"{n}.png"
        with Image.open(work / f"{n}.tiff") as im:
            im.convert("RGB").save(dst, dpi=im.info["dpi"], icc_profile=im.info.get("icc_profile"))
        shutil.copyfile(work / "qa" / f"{n}.style.json", ti / f"{n}.png.evidence.json")
        out.append(dst)
    # Vector PDF: 07 mean spectrum (all acquisitions averaged) in the house style.
    sheets = pf.cached(Path(data) / "in situ PL.xlsx", pf._load_in_situ)
    d = next(df for _, df in sheets if not df.empty)
    wl = d.iloc[5:, 0].to_numpy(dtype=float)
    mean = d.iloc[5:, 1:].to_numpy(dtype=float).mean(axis=1)
    fig, ax = ps.new_figure(INPUT_DPI, width_mm, ps.DEFAULT_HEIGHT_MM[ps.SINGLE_COLUMN_MM])
    ax.xaxis.set_major_locator(pf.MaxNLocator(nbins=5, min_n_ticks=3, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_locator(pf.MaxNLocator(nbins=5, min_n_ticks=3, steps=[1, 2, 5, 10]))
    ax.plot(wl, mean, color=pf.BLUE, linewidth=ps.DENSE_LINE_PT)
    ax.set(xlabel="Wavelength (nm)", ylabel="Mean PL intensity (counts)")
    ax.set_xlim(wl.min(), wl.max())
    layout = ps.fit_layout(fig, ax, clearance_mm=INPUT_CLEARANCE_MM)
    if ps.thin_ticks(ax):
        layout = ps.fit_layout(fig, ax, clearance_mm=INPUT_CLEARANCE_MM)
    pdf = ti / "07_mean_spectrum_vector.pdf"
    fig.canvas.draw()   # evidence from the final layout at the 600 dpi placement density, before the PDF save
    rec = ps.describe_figure(fig, font, "spectrum")
    fig.savefig(pdf, format="pdf")
    rec.update({"figure": "07_mean_spectrum_vector", "file": pdf.name, "layout": layout,
                "target_mm": list(fig._paper_target_mm),
                "evidence_note": "Agg renderer boxes of the same Figure object saved to this PDF"})
    (ti / f"{pdf.name}.evidence.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    plt.close(fig)
    out.append(pdf)
    return out


def measure(path):
    with Image.open(path) as im:
        dpi = float(im.info["dpi"][0])
        return {"px": im.size, "dpi": dpi, "mm": [round(v / dpi * 25.4, 3) for v in im.size],
                "compression": im.info.get("compression"), "icc": bool(im.info.get("icc_profile"))}


# ------------------------------------------------------------ Batch 5 acceptance
P4 = ["01_IR", "03_TPC_overlay", "04_TPC_overlay_logtime", "05_PL_image"]
P6 = ["01_IR", "02_XRD", "03_TPC_overlay", "04_TPC_overlay_logtime", "07_in_situ_PL_mean_spectrum",
      "10_in_situ_PL_normalized_mean_spectrum"]
P7 = ["06_in_situ_PL_heatmap"] + P6
P8 = ["01_IR", "02_XRD", "03_TPC_overlay", "04_TPC_overlay_logtime", "06_in_situ_PL_heatmap",
      "07_in_situ_PL_mean_spectrum", "08_in_situ_PL_normalized_global", "10_in_situ_PL_normalized_mean_spectrum"]
LEGEND = ["--legend-entry", "Sample 1=#2166AC:solid", "--legend-entry", "Sample 2=#B35806:dashed"]


def acceptance_cases():
    """(case, width_mm, panels, extra args, expectation: 'auto' | 'fit' | 'force' | 'error', requested geometry)."""
    cases = []
    for w in (89, 183):
        for n, panels, extra, req in ((4, P4, [], "auto search"), (6, P6, [], "auto search"),
                                      (7, P7, ["--cols", "2", "--span", "a=row"],
                                       "2x4: a spans the full first row, 6 panels in a 2-column x 3-row body"),
                                      (8, P8, [], "auto search")):
            cases.append((f"auto_{n}p_{w}mm", w, panels, ["--layout", "auto", *extra], "auto", req))
    cases += [
        ("force_4p_89mm", 89, P4, ["--layout", "auto", "--force"], "force", "auto search, --force fallback"),
        ("force_7p_183mm", 183, P7, ["--layout", "auto", "--cols", "2", "--span", "a=row", "--force"], "force",
         "2x4 (a=row + 2x3 body), --force fallback"),
        ("span_multirow_183mm", 183, ["06_in_situ_PL_heatmap", "01_IR", "03_TPC_overlay", "04_TPC_overlay_logtime",
                                      "07_in_situ_PL_mean_spectrum"], ["--layout", "auto", "--span", "a=1x2"], "fit",
         "a spans 1 column x 2 rows"),
        ("legend_auto_183mm", 183, ["06_in_situ_PL_heatmap", "03_TPC_overlay", "04_TPC_overlay_logtime",
                                    "07_in_situ_PL_mean_spectrum"],
         ["--layout", "auto", "--span", "a=1x2", "--empty-cells", "legend", *LEGEND], "fit",
         "a=1x2, legend in the auto-selected empty cell"),
        ("legend_manual_rowspan_183mm", 183, ["06_in_situ_PL_heatmap", "03_TPC_overlay", "04_TPC_overlay_logtime",
                                              "07_in_situ_PL_mean_spectrum"],
         ["--layout", "manual", "--cols", "2", "--span", "a=row", "--empty-cells", "legend", "--legend-cell", "3,2",
          *LEGEND], "fit", "manual 2 columns, a=row, legend at row 3 col 2"),
        ("invalid_malformed_span", 183, P4, ["--layout", "auto", "--span", "a=3"], "error", "a=3"),
        ("invalid_duplicate_span", 183, P4, ["--layout", "auto", "--span", "a=row", "--span", "a=2x1"], "error",
         "a twice"),
        ("invalid_nonexistent_panel", 183, P4, ["--layout", "auto", "--span", "h=row"], "error", "h (4 panels)"),
        ("invalid_span_wider_than_grid", 89, P4[:3], ["--layout", "manual", "--cols", "1", "--span", "a=2x1"],
         "error", "a=2x1 on 1 column"),
        ("invalid_pl_image_span", 183, P4, ["--layout", "auto", "--span", "d=2x1"], "error", "05 d=2x1"),
        ("invalid_legend_no_free_cell", 183, P4, ["--layout", "manual", "--cols", "2", "--empty-cells", "legend",
                                                  *LEGEND], "error", "2x2 full, legend"),
        ("invalid_legend_cell_occupied", 183, P4[:3], ["--layout", "manual", "--cols", "2", "--empty-cells",
                                                       "legend", "--legend-cell", "1,1", *LEGEND], "error",
         "legend at 1,1 (occupied)"),
        ("invalid_legend_without_entries", 183, P4, ["--layout", "auto", "--empty-cells", "legend"], "error",
         "legend, no entries"),
        ("invalid_auto_label_conflict", 183, P4, ["--layout", "auto", "--label-pt", "12"], "error",
         "auto with --label-pt 12"),
    ]
    return cases


def tiff_tags(path):
    """Size and export facts read from the TIFF tags themselves."""
    with Image.open(path) as im:
        t = im.tag_v2
        xr, yr = float(t.get(282)), float(t.get(283))
        w, h = int(t.get(256)), int(t.get(257))
        icc = t.get(34675) or im.info.get("icc_profile")
        desc = None
        if icc:
            from PIL import ImageCms
            import io
            desc = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(bytes(icc)))).strip()
        return {"px": [w, h], "x_res": xr, "y_res": yr, "res_unit": int(t.get(296, 2)),
                "compression": int(t.get(259)), "photometric": int(t.get(262)), "mode": im.mode,
                "samples_per_pixel": int(t.get(277, 3)), "icc_bytes": len(icc) if icc else 0,
                "icc_description": desc,
                "mm": [round(w / xr * 25.4, 3), round(h / yr * 25.4, 3)] if int(t.get(296, 2)) == 2 else None}


def write_acceptance_md(res, qa):
    """layout_acceptance.md from the JSON result (one row per case; N/A when not measurable)."""
    rows, ok_all = res["rows"], res["all_pass"]
    na = lambda v: "N/A" if v is None else v  # noqa: E731
    md = ["# Layout acceptance (Batch 5)", "",
          f"Data: `{res['data']}`. Every row ran `make_composite.py` through its CLI. Logs: `{qa / 'logs'}`. "
          "height_mm and grid come from the published TIFF tags/JSON; N/A after a warning-only or error exit "
          "(no TIFF). For no-fit cases the requested geometry and every tried candidate are in "
          "`layout_acceptance.json` and the linked `.nofit.json`.", "",
          "| case | width | n | requested geometry | grid | spans | height_mm | fits | warning | text_fit pass | exit "
          "| result | evidence |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r_ in rows:
        grid = "N/A" if not r_["grid"] else f"{r_['grid'][0]}x{r_['grid'][1]}"
        warn = r_["warning"] or r_["error"]
        warn = "N/A" if not warn else warn.replace("|", "/")[:160] + ("..." if len(warn) > 160 else "")
        ev = r_["output"] or r_.get("nofit_json") or r_["log"]
        md.append(f"| {r_['case']} | {r_['width']} | {r_['n']} | {r_.get('requested_geometry') or '-'} | {grid} | "
                  f"{', '.join(r_['spans']) or '-'} | "
                  f"{na(r_['height_mm'])} | {na(r_['fits'])}{' (FORCED)' if r_['forced'] else ''} | {warn} | "
                  f"{na(r_['text_fit_pass'])} | {r_['exit']} | {'PASS' if r_['pass'] else 'FAIL'} | "
                  f"[{Path(ev).name}]({ev}) |")
    md += ["", f"All cases as expected: **{ok_all}**", ""]
    (qa / "layout_acceptance.md").write_text("\n".join(md))


def run_acceptance(a):
    import text_fit_composite_labels as tfl
    out = a.out.resolve()
    qa = (a.qa_dir or out.parent / "qa").resolve()
    prev = (a.preview_dir or out.parent / "preview").resolve()
    for d in (out, qa, prev):
        d.mkdir(parents=True, exist_ok=True)
    rows, ok_all = [], True
    for case, width, panels, extra, expect, requested in acceptance_cases():
        tif = out / f"{case}.tiff"
        log = qa / "logs" / f"{case}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(HERE / "make_composite.py"), "--data", str(a.data), "--out", str(tif),
               "--no-config", *extra, "--panels", *panels]
        if width == 183:
            cmd.append("--double-column")
        if a.manifest:
            cmd += ["--manifest", str(a.manifest)]
        print("$", " ".join(cmd), flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True)
        log.write_text("$ " + " ".join(cmd) + "\n" + r.stdout + "\n--- stderr ---\n" + r.stderr
                       + f"\nEXIT {r.returncode}\n")
        spans = [x for i, x in enumerate(extra) if i and extra[i - 1] == "--span"]
        row = {"case": case, "width": width, "n": len(panels), "panels": panels, "grid": None, "spans": spans,
               "requested_geometry": requested, "height_mm": None, "fits": None, "warning": None,
               "text_fit_pass": None, "exit": r.returncode, "expect": expect, "forced": False,
               "output": None, "json": None, "log": str(log), "tiff_checks": None, "error": None}
        warn = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("WARNING: no auto layout")]
        err = [ln for ln in r.stderr.splitlines() if ln.startswith("ERROR:")]
        if tif.exists():
            rec = json.loads(tif.with_suffix(".json").read_text())
            auto = rec.get("auto_layout") or {}
            tags = tiff_tags(tif)
            dpi = min(tags["x_res"], tags["y_res"])
            tc = {**tags,
                  "rgb": tags["mode"] == "RGB" and tags["photometric"] == 2 and tags["samples_per_pixel"] == 3,
                  "lzw": tags["compression"] == 5, "srgb_icc": bool(tags["icc_bytes"]) and
                  "srgb" in (tags["icc_description"] or "").lower(),
                  "dpi_ge_600": dpi >= 600 - 1e-6,
                  "width_exact": abs(tags["mm"][0] - width) <= 25.4 / tags["x_res"] + 1e-6,
                  "height_le_247": tags["mm"][1] <= 247.0 + 1e-6}
            core = ("rgb", "lzw", "srgb_icc", "dpi_ge_600", "width_exact")
            tc["pass"] = all(tc[k] for k in core) and (tc["height_le_247"] or auto.get("forced", False))
            lab = tfl.label_check(tif, "(a)", 14.0)
            row.update({"grid": rec["grid"], "height_mm": tags["mm"][1], "fits": not auto.get("forced", False)
                        and tc["height_le_247"], "text_fit_pass": lab["pass"], "output": str(tif),
                        "json": str(tif.with_suffix(".json")), "tiff_checks": tc, "forced": auto.get("forced", False),
                        "failed_criteria": auto.get("failed_criteria"),
                        "selection_reason": auto.get("selection_reason"),
                        "positions": rec.get("positions"), "empty_cells": rec.get("empty_cells"),
                        "legend": None if not rec.get("legend") else {
                            "cell_rc_1based": rec["legend"]["cell_rc_1based"], "text_sizes_pt":
                            rec["legend"]["text_sizes_pt"], "inside_cell": rec["legend"]["inside_cell"],
                            "selected_by": rec["legend"]["selected_by"]},
                        "label_font": {k: lab["label_font"][k] for k in ("family", "style", "actual_pt", "texts")},
                        "other_text_sizes_pt": lab["other_text_sizes_pt"],
                        "label_overlaps": sum(len(x["overlaps"]) for x in lab["labels"]),
                        "text_collisions": len(lab["full_text_fit"]["text_collisions"]),
                        "clipped": len(lab["full_text_fit"]["clipped_canvas"]) + len(lab["full_text_fit"]["clipped_crop"]),
                        "baked_in_text_without_evidence": lab["baked_in_text_without_evidence"]})
            if forced := auto.get("forced"):
                row["warning"] = warn[0] if warn else None
            with Image.open(tif) as im:
                s = 150 / float(im.info["dpi"][0])
                pv = prev / f"{case}.png"
                im.convert("RGB").resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                                         Image.LANCZOS).save(pv, dpi=(150, 150))
            row["preview"] = str(pv)
            good = r.returncode == 0 and tc["pass"] and lab["pass"]
            if expect == "error":
                good = False
            elif expect == "force":
                good = good and bool(forced) == bool(warn)
            elif expect == "fit":
                good = good and not forced
        else:
            nofit = tif.with_suffix(".nofit.json")
            row["fits"] = False if warn else None
            if warn:
                row["warning"] = warn[0]
                m = re.search(r"Suggestion: (.*)$", warn[0])
                row["suggestion"] = m.group(1) if m else None
                row["nofit_json"] = str(nofit) if nofit.exists() else None
                if nofit.exists():
                    nf = json.loads(nofit.read_text())
                    row["candidates"] = [{"grid": c["grid"], "planned_height_mm": c["planned_height_mm"],
                                          "reason": c["reason"]} for c in nf["auto_layout"]["candidates"]]
            row["error"] = err[0] if err else None
            if expect == "error":
                good = r.returncode == 2 and bool(err)
            elif expect == "auto":
                good = r.returncode == 4 and bool(warn) and nofit.exists() and bool(row.get("suggestion"))
            else:
                good = False
        row["pass"] = bool(good)
        ok_all = ok_all and row["pass"]
        rows.append(row)
        print(f"{'PASS' if row['pass'] else 'FAIL'} case {case}: exit {r.returncode}, grid {row['grid']}, "
              f"height {row['height_mm']} mm, fits {row['fits']}, text_fit {row['text_fit_pass']}"
              f"{', FORCED' if row['forced'] else ''}{', WARNING' if row['warning'] else ''}"
              f"{', ' + row['error'] if row['error'] else ''}", flush=True)
    res = {"tool": "run_composites.py --layout-acceptance", "data": str(a.data), "manifest": str(a.manifest),
           "out": str(out), "rows": rows, "all_pass": ok_all,
           "notes": ["height_mm and grid are null after a warning-only or error exit (no TIFF published)",
                     "fits = published without --force and height <= 247 mm from the TIFF tags",
                     "text_fit_pass = text_fit_composite_labels.label_check (includes composite_fit)"]}
    (qa / "layout_acceptance.json").write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    write_acceptance_md(res, qa)
    print("LAYOUT ACCEPTANCE " + ("ALL PASS" if ok_all else "SOME CASES FAILED"), flush=True)
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--config-dir", type=Path, default=None,
                    help="apply saved axis overrides from DIR (default: none, spec defaults)")
    ap.add_argument("--manifest", type=Path, default=None, help="reference SHA-256 manifest for --data")
    ap.add_argument("--label-format", default=None,
                    help="panel label style passed to make_composite.py (default (a), or saved composite config)")
    ap.add_argument("--label-pt", type=float, default=None,
                    help="panel label size in pt passed to make_composite.py (default 14, or saved config)")
    ap.add_argument("--layout-acceptance", action="store_true",
                    help="Batch 5: run the auto-layout/span/legend acceptance cases (see module doc)")
    ap.add_argument("--with-examples", action="store_true",
                    help="with --layout-acceptance: also build the example sets")
    ap.add_argument("--qa-dir", type=Path, default=None, help="acceptance QA directory (default OUT/../qa)")
    ap.add_argument("--preview-dir", type=Path, default=None,
                    help="acceptance PNG previews (default OUT/../preview)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.layout_acceptance:
        rc_acc = run_acceptance(a)
        if not a.with_examples:
            return rc_acc
    else:
        rc_acc = 0
    jobs = []
    for double, tag, ncol in ((False, "89mm", 1), (True, "183mm", 2)):
        width = 183.0 if double else 89.0
        names = {"tiff": ["01_IR"] + (["03_TPC_overlay"] if double else []), "png": ["04_TPC_overlay_logtime"]}
        ti = a.out / "test_inputs" / tag
        files = make_test_inputs(a.data, ti, placement_width_mm(width, ncol), names)
        tiffs = [f for f in files if f.suffix == ".tiff"]
        others = [f for f in files if f.suffix != ".tiff"]
        set2 = [str(tiffs[0]), str(others[0]), str(others[1])] + [str(t) for t in tiffs[1:]]
        jobs.append(("set1_data", tag, double, ncol,
                     ["01_IR", "03_TPC_overlay", "04_TPC_overlay_logtime", "05_PL_image"], []))
        jobs.append(("set2_images", tag, double, ncol, set2, ["--artwork-scale", "native"]))
    rc = 0
    for set_name, tag, double, ncol, panels, extra in jobs:
        out = a.out / f"{set_name}_{tag}.tiff"
        cmd = [sys.executable, str(HERE / "make_composite.py"), "--data", str(a.data),
               "--out", str(out), "--cols", str(ncol), "--gap-mm", str(GAP_MM),
               "--clearance-mm", str(EDGE_MM), *extra, "--panels", *panels]
        if double:
            cmd.append("--double-column")
        if a.manifest:
            cmd += ["--manifest", str(a.manifest)]
        cmd += ["--config-dir", str(a.config_dir)] if a.config_dir else ["--no-config"]
        if a.label_format:
            cmd += ["--label-format", a.label_format]
        if a.label_pt is not None:
            cmd += ["--label-pt", f"{a.label_pt:g}"]
        print("$", " ".join(cmd), flush=True)
        r = subprocess.run(cmd)
        rc = rc or r.returncode
        if r.returncode != 0:
            print(f"FAILED {out.name} (exit {r.returncode})", flush=True)
            continue
        m = measure(out)
        print(f"MEASURED {out.name}: {m['px'][0]}x{m['px'][1]} px @ {m['dpi']:g} dpi = "
              f"{m['mm'][0]} x {m['mm'][1]} mm, {m['compression']}, ICC={m['icc']}", flush=True)
    return rc or rc_acc


if __name__ == "__main__":
    sys.exit(main())
