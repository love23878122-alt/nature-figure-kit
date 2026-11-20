"""Shared verification helpers used by verify_figures.py (TIFF facts, renderer
evidence vs. spec, heatmap/PL pixel checks, final-size overview). Also runnable:

    python verify_core.py --out OUT [--sheet-width-mm 390]

Reads the saved TIFFs (size, dpi, compression, ICC, mode) and pairs them with
renderer evidence (``qa/<name>.style.json``: glyph-level font files, text sizes,
stroke widths, ticks, collisions). Heatmap cells and the PL image are checked
against the stored native arrays. Composite panels use their per-panel render
records; fonts and strokes inside imported artwork are reported as
"unverified" (embedded PDF font names are listed where PyMuPDF can read them).

Writes <out>/qa/verify_core.json and <out>/qa/overview_final_size.tiff.
Exit 0 when every check passes.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qa_helpers as af  # noqa: E402
import paper_style as ps  # noqa: E402
from plot_figures import FIGURE_NAMES  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
DENSE = {"07_in_situ_PL_mean_spectrum", "10_in_situ_PL_normalized_mean_spectrum"}
HEATMAPS = {"06_in_situ_PL_heatmap", "08_in_situ_PL_normalized_global", "09_in_situ_PL_normalized_per_scan"}


def tiff_facts(path):
    with Image.open(path) as im:
        dpi = tuple(float(v) for v in im.info.get("dpi", (0, 0)))
        icc = im.info.get("icc_profile")
        desc = (ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
                if icc else None)
        w, h = im.size
        r = {"path": str(path), "mode": im.mode, "px": [w, h], "dpi": list(dpi),
             "mm": [round(w / dpi[0] * 25.4, 3), round(h / dpi[1] * 25.4, 3)] if dpi[0] else None,
             "compression": im.info.get("compression"), "icc_profile": desc}
    r["export_pass"] = (r["mode"] == "RGB" and r["compression"] == "tiff_lzw" and min(dpi) >= 600
                        and bool(desc) and "srgb" in desc.lower())
    r["nature_width"] = bool(r["mm"]) and min(abs(r["mm"][0] - 89), abs(r["mm"][0] - 183)) <= 25.4 / dpi[0]
    return r


def font_and_strokes(rec, name, overrides=None):
    """Summarize renderer evidence and check it against the spec."""
    problems = []
    font_path = str(Path(rec["font"]["path"]).resolve())
    fonts = sorted({str(Path(p).resolve()) for t in rec["texts"] for p in t["glyph_font_paths"]})
    for t in rec["texts"]:
        if {str(Path(p).resolve()) for p in t["glyph_font_paths"]} != {font_path} or t["missing_glyphs"]:
            problems.append(f"font {t['role']} {t['text']!r}")
        want = ps.AXIS_LABEL_PT if t["role"].endswith(("xlabel", "ylabel")) else ps.TICK_PT
        if abs(t["size_pt"] - want) > 1e-6:
            problems.append(f"size {t['role']} {t['text']!r} {t['size_pt']} != {want}")
    if rec["titles"]:
        problems.append(f"titles {rec['titles']}")
    line_pt = ps.DENSE_LINE_PT if name in DENSE else ps.DATA_LINE_PT
    widths = {}
    for s in rec["strokes"]:
        role = s["role"]
        key = ("data_line" if "data_line" in role else "legend_sample" if "legend_sample" in role
               else "spine" if ".spine." in role else "tick" if "tick" in role else role)
        widths.setdefault(key, set()).add(round(s["linewidth_pt"], 4))
        want = {"data_line": line_pt, "legend_sample": line_pt, "spine": ps.SPINE_PT, "tick": ps.TICK_WIDTH_PT}.get(key)
        if want is not None and abs(s["linewidth_pt"] - want) > 1e-6:
            problems.append(f"stroke {role} {s['linewidth_pt']} != {want}")
    m = rec["main_axes"]
    side = {k: v for k, v in m.items() if "tick2_visible" in k or "label2_visible" in k}
    if any(side.values()):
        problems.append(f"top/right ticks {side}")
    if not all(m["spines_visible"].values()):
        problems.append("spine hidden")
    hidden = {a for a, s in (overrides or {}).items() if s.get("visible") is False or s.get("major_ticks") is False}
    if "x" not in hidden and not m["x_major_tick1_visible"]:
        problems.append("bottom major ticks missing")
    if "y" not in hidden and not m["y_major_tick1_visible"]:
        problems.append("left major ticks missing")
    if rec["colorbar"] and abs(rec["colorbar"]["outline_linewidth_pt"] - ps.SPINE_PT) > 1e-6:
        problems.append("colour-bar outline width")
    for key in ("text_collisions", "legend_data_overlap", "text_outside_canvas"):
        if rec[key]:
            problems.append(f"{key}: {rec[key]}")
    return {"fonts_actual": fonts, "font_source": "renderer glyph resolution (style.json)",
            "text_sizes_pt": sorted({(t["role"].split(".")[-1], t["size_pt"]) for t in rec["texts"]}),
            "line_widths_pt": {k: sorted(v) for k, v in widths.items()},
            "stroke_source": "Matplotlib artist properties at final size (style.json)",
            "titles": rec["titles"], "problems": problems}


def spine_raster(rgb, box, dpi):
    y = int((box["top"] + box["bottom"]) / 2)
    x0 = int(box["x0"])
    row = rgb[y, max(0, x0 - 60):x0 + 2].astype(int).sum(axis=1)
    return {"left_spine_dark_px": int((row < 384).sum()), "expected_px": round(ps.SPINE_PT / 72 * dpi, 2)}


def pl_check(area, npz):
    img = np.load(npz)["intensity"]
    ref = af.lut_colors(img, float(img.min()), float(img.max()))
    k = max(1, area.shape[0] // img.shape[0])
    ref = np.repeat(np.repeat(ref, k, axis=0), k, axis=1)
    if area.shape != ref.shape:
        return {"pass": False, "data_area_px": list(area.shape[:2]), "native": list(img.shape)}
    d = np.abs(area.astype(int) - ref.astype(int)).max(axis=2)
    return {"pass": int(d.max()) <= 2, "data_area_px": list(area.shape[:2]), "max_channel_diff": int(d.max()),
            "pixels_diff_gt1": int((d > 1).sum()), "device_px_per_native_px": k}


def figure_entry(out_dir, name, src_dir, overrides_expected=False):
    tif = out_dir / f"{name}.tiff"
    rec = json.loads((out_dir / "qa" / f"{name}.style.json").read_text())
    entry = {"tiff": tiff_facts(tif), "target_mm": rec["target_mm"],
             "evidence": font_and_strokes(rec, name, rec.get("axis_overrides")),
             "axis_overrides": rec.get("axis_overrides", {}),
             "clearance_mm": rec["layout"].get("clearance_mm")}
    rgb = np.asarray(Image.open(tif).convert("RGB"))
    entry["spine_raster"] = spine_raster(rgb, rec["main_axes"]["box_px"], entry["tiff"]["dpi"][0])
    raster_ok = True
    if not rec.get("axis_overrides"):
        if name in HEATMAPS:
            entry["heatmap_cells"] = af.audit_mesh(rgb, rec, src_dir)
            raster_ok = entry["heatmap_cells"]["every_cell_resolved"]
        if name == "05_PL_image":
            x0, top, x1, bottom = af.data_box(rec)
            entry["pl_pixels"] = pl_check(rgb[top:bottom, x0:x1], src_dir / "PL_image.npz")
            raster_ok = entry["pl_pixels"]["pass"]
    if overrides_expected and not rec.get("axis_overrides"):
        entry["evidence"]["problems"].append("expected saved axis overrides were not applied")
    entry["pass"] = entry["tiff"]["export_pass"] and entry["tiff"]["nature_width"] and \
        not entry["evidence"]["problems"] and raster_ok
    return entry


def composite_entry(tif, pl_npz):
    rec = json.loads(tif.with_suffix(".json").read_text())
    entry = {"tiff": tiff_facts(tif), "checks": rec["checks"], "grid": rec["grid"], "dpi": rec["dpi"],
             "label": rec["label"], "panels": []}
    ok = entry["tiff"]["export_pass"] and entry["tiff"]["nature_width"] and all(rec["checks"].values())
    rgb = None
    for p in rec["panels"]:
        item = {"label": p["label"], "spec": p["spec"], "kind": p["kind"],
                "box_px": p["box_px"], "placed_mm": [round(p["box_px"][2] / rec["dpi"] * 25.4, 2),
                                                     round(p["box_px"][3] / rec["dpi"] * 25.4, 2)]}
        if p["kind"] == "data":
            srec = json.loads(Path(p["render"]["style_json"]).read_text())
            ev = font_and_strokes(srec, p["name"], srec.get("axis_overrides"))
            item.update({"fonts_actual": ev["fonts_actual"], "line_widths_pt": ev["line_widths_pt"],
                         "text_sizes_pt": ev["text_sizes_pt"], "problems": ev["problems"],
                         "evidence": "panel render record (style.json)"})
            ok = ok and not ev["problems"]
            if p["name"] == "05_PL_image":
                if rgb is None:
                    rgb = np.asarray(Image.open(tif).convert("RGB"))
                x, y, w, h = (int(round(v)) for v in p["box_px"])
                item["pl_pixels"] = pl_check(rgb[y:y + h, x:x + w], pl_npz)
                ok = ok and item["pl_pixels"]["pass"]
        else:
            item.update({"fonts_actual": "unverified (imported artwork)",
                         "line_widths_pt": "unverified (imported artwork)",
                         "effective_dpi_at_placement": round(p.get("effective_dpi", 0), 1),
                         "resampled": p.get("resampled"), "rasterization": p.get("rasterization")})
            if p["kind"] == "pdf":
                import pymupdf
                with pymupdf.open(p["path"]) as doc:
                    item["pdf_embedded_fonts"] = sorted({f[3] for f in doc[p["page"] - 1].get_fonts()})
        entry["panels"].append(item)
    entry["panel_label_font"] = rec["label"]["font"] + f" (PIL truetype, {rec['label']['text_pt']:g} pt at composite dpi)"
    entry["pass"] = ok
    return entry


def overview(out, items, width_mm, sheet_dpi=600, margin_mm=4.0, gap_mm=5.0, cap_pt=7):
    """Shelf-pack every deliverable at its physical size on one 600 dpi sheet."""
    mm2px = sheet_dpi / 25.4
    font = ImageFont.truetype(str(ps.resolve_font("Arial").path), round(cap_pt / 72 * sheet_dpi))
    cap_h = round(cap_pt / 72 * sheet_dpi * 1.6)
    W = round(width_mm * mm2px)
    x = y = round(margin_mm * mm2px)
    row_h, placed = 0, []
    for label, path, mm in items:
        w, h = round(mm[0] * mm2px), round(mm[1] * mm2px)
        if x + w > W - margin_mm * mm2px and x > margin_mm * mm2px:
            x, y = round(margin_mm * mm2px), y + row_h + round(gap_mm * mm2px)
            row_h = 0
        placed.append((label, path, mm, x, y, w, h))
        x += w + round(gap_mm * mm2px)
        row_h = max(row_h, h + cap_h)
    H = y + row_h + round(margin_mm * mm2px)
    sheet = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(sheet)
    layout = []
    for label, path, mm, x, y, w, h in placed:
        draw.text((x, y), f"{label}  {mm[0]:.1f} x {mm[1]:.1f} mm", font=font, fill=(90, 90, 90))
        with Image.open(path) as im:
            im = im.convert("RGB")
            native = im.size == (w, h)
            if not native:
                im = im.resize((w, h), Image.LANCZOS)
            sheet.paste(im, (x, y + cap_h))
        draw.rectangle((x - 2, y + cap_h - 2, x + w + 1, y + cap_h + h + 1), outline=(200, 200, 200), width=2)
        layout.append({"item": label, "xy_px": [x, y + cap_h], "size_px": [w, h], "mm": mm,
                       "placed_1to1": native})
    path = out / "qa" / "overview_final_size.tiff"
    sheet.save(path, format="TIFF", compression="tiff_lzw", dpi=(sheet_dpi, sheet_dpi), icc_profile=ps.srgb_icc_bytes())
    facts = tiff_facts(path)
    facts.pop("nature_width", None)
    facts["note"] = ("review sheet: each TIFF at its physical size on a 600 dpi canvas; items rendered above "
                     "600 dpi are resampled for this sheet only (deliverables untouched)")
    facts["panels"] = layout
    return facts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sheet-width-mm", type=float, default=390.0)
    a = ap.parse_args()
    out = a.out.resolve()
    qa = out / "qa"
    res = {"figures": {}, "double_column": {}, "composites": {}, "menu_before": {}, "menu_after": {},
           "menu_renders": {}}
    for n in FIGURE_NAMES:
        if (out / f"{n}.tiff").exists():
            res["figures"][n] = figure_entry(out, n, out / "source_data")
        if (out / "double_column" / f"{n}.tiff").exists():
            res["double_column"][n] = figure_entry(out / "double_column", n, out / "double_column" / "source_data")
        for key, sub, expect in (("menu_before", "before", False), ("menu_after", "after", True),
                                 ("menu_renders", "menu_renders", True)):
            if (qa / sub / f"{n}.tiff").exists():
                res[key][n] = figure_entry(qa / sub, n, qa / sub / "source_data", overrides_expected=expect)
    pl_npz = qa / "before" / "source_data" / "PL_image.npz"
    for tif in sorted((out / "composite").glob("*.tiff")):
        res["composites"][tif.name] = composite_entry(tif, pl_npz)
    # menu: reloaded config reproduces the menu render pixel for pixel
    res["menu_reload_identical"] = {}
    for n in res["menu_after"]:
        if n in res["menu_renders"]:
            a1 = np.asarray(Image.open(qa / "after" / f"{n}.tiff"))
            a2 = np.asarray(Image.open(qa / "menu_renders" / f"{n}.tiff"))
            res["menu_reload_identical"][n] = a1.shape == a2.shape and bool((a1 == a2).all())

    items = [(n, out / f"{n}.tiff", e["tiff"]["mm"]) for n, e in res["figures"].items()]
    items += [(f"double_column/{n}", out / "double_column" / f"{n}.tiff", e["tiff"]["mm"])
              for n, e in res["double_column"].items()]
    items += [(f"composite/{k}", out / "composite" / k, e["tiff"]["mm"]) for k, e in res["composites"].items()]
    res["overview"] = overview(out, items, a.sheet_width_mm)

    groups = ("figures", "double_column", "composites", "menu_before", "menu_after", "menu_renders")
    res["summary"] = {g: {k: v["pass"] for k, v in res[g].items()} for g in groups}
    all_ok = all(all(v.values()) for v in res["summary"].values()) and all(res["menu_reload_identical"].values())
    res["all_pass"] = all_ok
    for g in groups:
        for k, v in res[g].items():
            t = v["tiff"]
            print(f"{'PASS' if v['pass'] else 'FAIL'} {g}/{k}: {t['px'][0]}x{t['px'][1]} px @ {t['dpi'][0]:g} dpi = "
                  f"{t['mm'][0]:.2f} x {t['mm'][1]:.2f} mm {t['compression']} ICC={t['icc_profile']}")
            for p in v.get("evidence", {}).get("problems", []):
                print("    -", p)
    print("menu reload identical:", res["menu_reload_identical"])
    print("OVERVIEW:", res["overview"]["path"], res["overview"]["px"], res["overview"]["mm"])
    (qa / "verify_core.json").write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    print("ALL PASS" if all_ok else "SOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
