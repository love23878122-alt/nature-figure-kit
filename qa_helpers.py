"""QA helpers used by verify_figures.py (colour LUT, data-box geometry, heatmap-cell audit).

Derived from an earlier stand-alone audit script; its command-line mode still
checks the superseded 203.2 mm canvas and is not part of this kit's workflow.
Use ``verify_figures.py`` for the current specification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import colormaps
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plot_figures import FIGURE_NAMES, INPUT_FILES  # noqa: E402

CANVAS_MM = 203.2


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lut_colors(values, vmin, vmax, cmap="viridis"):
    norm = (np.asarray(values, dtype=float) - vmin) / (vmax - vmin)
    return colormaps[cmap](norm, bytes=True)[..., :3]


def data_box(record):
    b = record["main_axes"]["box_px"]
    return int(round(b["x0"])), int(round(b["top"])), int(round(b["x1"])), int(round(b["bottom"]))


def audit_tiff(path, record):
    img = Image.open(path)
    tags = img.tag_v2
    dpi = img.info.get("dpi", (0, 0))
    res_unit = tags.get(296)
    w, h = img.size
    # Nature widths only: 89 mm (single) or 183 mm (double column); height is content-derived.
    expected = (min((round(mm / 25.4 * float(dpi[0])) for mm in (89.0, 183.0)), key=lambda e: abs(e - w))
                if dpi[0] else None)
    row = {
        "mode": img.mode, "compression": img.info.get("compression"), "compression_tag_259": tags.get(259),
        "dpi": [float(dpi[0]), float(dpi[1])], "resolution_unit_296": res_unit,
        "pixels": [w, h],
        "canvas_mm": [w / float(dpi[0]) * 25.4, h / float(dpi[1]) * 25.4] if dpi[0] else None,
        "file_bytes": path.stat().st_size,
    }
    row["rgb"] = img.mode == "RGB"
    row["lzw"] = row["compression"] == "tiff_lzw" and row["compression_tag_259"] == 5
    row["dpi_ge_600"] = res_unit == 2 and min(row["dpi"]) >= 600
    row["canvas_203_2mm"] = bool(row["canvas_mm"]) and all(abs(v - CANVAS_MM) <= 0.05 for v in row["canvas_mm"])
    row["pixels_within_1"] = expected is not None and abs(w - expected) <= 1
    row["matches_render_record"] = [w, h] == record["canvas_px"] and float(dpi[0]) == record["dpi"]
    rgb = np.asarray(img.convert("RGB"))
    return row, rgb


def clearance(rgb, dpi, record):
    mask = np.any(rgb != 255, axis=2)
    rows, cols = np.flatnonzero(mask.any(1)), np.flatnonzero(mask.any(0))
    H, W = mask.shape
    gaps = {"left": cols[0], "right": W - 1 - cols[-1], "top": rows[0], "bottom": H - 1 - rows[-1]}
    mm = {k: float(v) / dpi * 25.4 for k, v in gaps.items()}
    within = {k: 0.9 <= v <= 2.6 for k, v in mm.items()}
    exceptions = {k: round(v, 2) for k, v in mm.items() if not within[k]}
    return {"clearance_mm": {k: round(v, 3) for k, v in mm.items()},
            "all_sides_1_to_2mm": all(within.values()), "exceptions_mm": exceptions,
            "no_clipping": all(v >= 1 for v in gaps.values())}


def audit_image(rgb, record, source_dir):
    r = record["raster"]
    data = np.load(source_dir / r["npz"])[r["key"]]
    k = int(r["device_pixels_per_source_pixel"])
    x0, top, x1, bottom = data_box(record)
    crop = rgb[top:bottom, x0:x1]
    expected = lut_colors(data, r["vmin"], r["vmax"])
    if r["origin"] != "upper":
        expected = expected[::-1]
    expected = np.repeat(np.repeat(expected, k, axis=0), k, axis=1)
    out = {"source_shape": list(data.shape), "data_area_px": list(crop.shape[:2][::-1]),
           "device_pixels_per_source_pixel": k}
    out["data_area_matches_native_grid"] = crop.shape[:2] == expected.shape[:2]
    if out["data_area_matches_native_grid"]:
        diff = np.abs(crop.astype(int) - expected.astype(int)).max(axis=2)
        out["pixels_differing"] = int((diff > 1).sum())
        out["max_channel_difference"] = int(diff.max())
        out["unique_colours_rendered"] = int(len(np.unique(crop.reshape(-1, 3), axis=0)))
        out["unique_source_values"] = int(len(np.unique(data)))
        out["pixel_exact"] = out["pixels_differing"] == 0
    else:
        out["pixel_exact"] = False
    return out


def audit_mesh(rgb, record, source_dir):
    r = record["raster"]
    values = np.load(source_dir / r["npz"])[r["key"]]
    xs = np.load(source_dir / r["x_npz"])[r["x_key"]].astype(float)
    ys = np.load(source_dir / r["x_npz"])[r["y_key"]].astype(float)
    x0, top, x1, bottom = data_box(record)
    xlim, ylim = record["main_axes"]["xlim"], record["main_axes"]["ylim"]
    crop = rgb[top:bottom, x0:x1].astype(int)
    nrow, ncol = crop.shape[:2]

    def edges(c):
        mid = (c[1:] + c[:-1]) / 2
        return np.concatenate([[c[0] - (c[1] - c[0]) / 2], mid, [c[-1] + (c[-1] - c[-2]) / 2]])

    xe, ye = edges(xs), edges(ys)
    px_x = xlim[0] + (np.arange(ncol) + 0.5) / ncol * (xlim[1] - xlim[0])
    px_y = ylim[1] - (np.arange(nrow) + 0.5) / nrow * (ylim[1] - ylim[0])
    ci = np.clip(np.searchsorted(xe, px_x) - 1, 0, len(xs) - 1)
    ri = np.clip(np.searchsorted(ye, px_y) - 1, 0, len(ys) - 1)
    lut = lut_colors(values, r["vmin"], r["vmax"]).astype(int)
    expected = lut[ri][:, ci]
    match = np.abs(crop - expected).max(axis=2) <= 1
    cell_id = ri[:, None] * len(xs) + ci[None, :]
    hits = np.bincount(cell_id[match].ravel(), minlength=values.size)
    px_per_col = np.bincount(ci, minlength=len(xs))
    px_per_row = np.bincount(ri, minlength=len(ys))
    dmin = float(np.diff(ys).min())
    return {"cells": list(values.shape), "data_area_px": [ncol, nrow],
            "limits_cover_full_mesh": bool(np.isclose(sorted(xlim)[0], xe[0]) and np.isclose(sorted(xlim)[1], xe[-1])
                                           and np.isclose(sorted(ylim)[0], ye[0]) and np.isclose(sorted(ylim)[1], ye[-1])),
            "smallest_wavelength_step_nm": dmin,
            "smallest_cell_height_px": float(dmin / (ylim[1] - ylim[0]) * nrow),
            "min_pixel_rows_per_wavelength_cell": int(px_per_row.min()),
            "min_pixel_cols_per_scan_cell": int(px_per_col.min()),
            "pixels_matching_expected_colour_fraction": float(match.mean()),
            "cells_present": int((hits > 0).sum()), "cells_total": int(values.size),
            "every_cell_resolved": bool((hits > 0).all() and px_per_row.min() >= 1 and px_per_col.min() >= 1)}


def compare_source_data(out_src, base_src):
    rows, ok = [], True
    for base in sorted(b for b in base_src.glob("*.npz") if not b.name.startswith("._")):
        new = out_src / base.name
        if not new.exists():
            rows.append({"file": base.name, "equal": False, "reason": "missing"}); ok = False; continue
        a, b = np.load(base, allow_pickle=False), np.load(new, allow_pickle=False)
        keys_equal = sorted(a.files) == sorted(b.files)
        arrays_equal = keys_equal and all(np.array_equal(a[k], b[k]) for k in a.files)
        rows.append({"file": base.name, "keys": sorted(a.files), "equal": bool(arrays_equal),
                     "shapes": {k: list(a[k].shape) for k in a.files}})
        ok &= arrays_equal
    for base in sorted(b for b in base_src.glob("*.csv") if not b.name.startswith("._")):
        new = out_src / base.name
        eq = new.exists() and pd.read_csv(base).equals(pd.read_csv(new))
        rows.append({"file": base.name, "equal": bool(eq)})
        ok &= eq
    return ok, rows


COMPARE_KEYS = ("source", "sources", "sheet", "rows_plotted", "shape", "pixels_plotted", "observations_plotted",
                "observations_used", "transform", "range", "color_limits", "global_maximum_counts",
                "divisor_counts", "renormalized", "baseline_subtracted", "assumption", "excluded_observations")


def compare_manifest(new_manifest, base_manifest):
    base = {f["figure"]: f for f in base_manifest.get("figures", [])}
    rows, ok = [], True
    for fig in new_manifest.get("figures", []):
        ref = base.get(fig["figure"], {})
        diffs = {k: [ref.get(k), fig.get(k)] for k in COMPARE_KEYS
                 if (k in ref or k in fig) and ref.get(k) != fig.get(k)}
        rows.append({"figure": fig["figure"], "matches_baseline": not diffs, "differences": diffs})
        ok &= not diffs
    return ok, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--baseline", type=Path, default=HERE, help="dir holding baseline source_data/ and qa/data_manifest.json")
    ap.add_argument("--data", type=Path, default=None, help="raw data dir (default: as recorded in the run manifest)")
    ap.add_argument("--manifest", type=Path, default=None, help="reference hash manifest (default: baseline qa/data_manifest.json)")
    args = ap.parse_args(argv)
    out = args.out.resolve()
    qa, src = out / "qa", out / "source_data"
    run_manifest = json.loads((qa / "data_manifest.json").read_text())
    ref_manifest_path = args.manifest or (args.baseline / "qa" / "data_manifest.json")
    base_manifest = json.loads(Path(args.baseline / "qa" / "data_manifest.json").read_text())
    ref_hashes = json.loads(Path(ref_manifest_path).read_text())["source_sha256"]
    data_dir = args.data or Path(run_manifest["data_dir"])

    summary = {"out": str(out), "figures": [], "checks": {}}
    failed = False

    # TIFF-only output.
    present = sorted(p.name for p in out.iterdir() if p.is_file())
    expected = sorted(f"{n}.tiff" for n in FIGURE_NAMES)
    summary["output_files"] = present
    summary["checks"]["tiff_only_ten_basenames"] = present == expected
    failed |= present != expected

    for name in FIGURE_NAMES:
        path = out / f"{name}.tiff"
        record = json.loads((qa / f"{name}.style.json").read_text())
        row = {"figure": name}
        if not path.exists():
            row["error"] = "missing TIFF"; failed = True; summary["figures"].append(row); continue
        tiff, rgb = audit_tiff(path, record)
        row["tiff"] = tiff
        row["layout"] = clearance(rgb, tiff["dpi"][0], record)
        raster = record.get("raster")
        if raster and raster["type"] == "image":
            row["raster"] = audit_image(rgb, record, src)
            raster_ok = row["raster"]["pixel_exact"]
        elif raster and raster["type"] == "mesh":
            row["raster"] = audit_mesh(rgb, record, src)
            raster_ok = row["raster"]["every_cell_resolved"] and row["raster"]["limits_cover_full_mesh"]
        else:
            raster_ok = True
        hard = [tiff["rgb"], tiff["lzw"], tiff["dpi_ge_600"], tiff["canvas_203_2mm"], tiff["pixels_within_1"],
                tiff["matches_render_record"], row["layout"]["no_clipping"], raster_ok]
        row["passed"] = all(hard)
        row["clearance_exception"] = not row["layout"]["all_sides_1_to_2mm"]
        failed |= not row["passed"]
        summary["figures"].append(row)
        print(f"{name}: {'PASS' if row['passed'] else 'FAIL'}  dpi={tiff['dpi'][0]:.0f} px={tiff['pixels']} "
              f"mm={tiff['canvas_mm'][0]:.3f} LZW={tiff['lzw']} RGB={tiff['rgb']} "
              f"clear={row['layout']['clearance_mm']}"
              + (f" raster={ {k: v for k, v in row['raster'].items() if k in ('pixel_exact','every_cell_resolved','pixels_differing','min_pixel_rows_per_wavelength_cell','min_pixel_cols_per_scan_cell','cells_present')} }" if raster else ""),
              flush=True)

    ok, rows = compare_source_data(src, args.baseline / "source_data")
    summary["checks"]["source_data_equals_baseline"] = ok
    summary["source_data_comparison"] = rows
    failed |= not ok
    ok, rows = compare_manifest(run_manifest, base_manifest)
    summary["checks"]["observations_transforms_divisors_match_baseline"] = ok
    summary["manifest_comparison"] = rows
    failed |= not ok
    now = {}
    for n in INPUT_FILES:
        try:
            now[n] = sha256(Path(data_dir) / n)
        except OSError as exc:
            now[n] = f"unreadable: {exc}"
    hashes_ok = now == ref_hashes == run_manifest["source_sha256"]
    summary["checks"]["raw_input_hashes_unchanged"] = hashes_ok
    summary["raw_input_sha256"] = now
    failed |= not hashes_ok
    summary["checks"]["clearance_exceptions"] = [f["figure"] for f in summary["figures"] if f.get("clearance_exception")]
    summary["passed"] = not failed
    (qa / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=float))
    for k, v in summary["checks"].items():
        print(f"{k}: {v}")
    print("EXPORT/DATA AUDIT:", "PASS" if not failed else "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
