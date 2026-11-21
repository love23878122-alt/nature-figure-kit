"""Verify every Batch 3 TIFF, build the final-size overview and the PNG previews.

    python verify_figures.py --out OUT [--sheet-width-mm 390] [--preview-dpi 150]

Reads each saved TIFF (px, dpi tags -> mm, compression, ICC description, mode)
and pairs it with renderer evidence (``qa/<name>.style.json``: glyph-level font
files, point sizes, stroke widths, ticks, collisions). Heatmap cells and the PL
image are checked against the stored native arrays.

Composites: data panels use their per-panel render records. Imported artwork
uses its ``<file>.evidence.json`` source renderer record when present (point
sizes and stroke widths scaled by the measured physical placement scale);
otherwise fonts and strokes are flagged "unverified (imported artwork, no
renderer evidence)". Panel letters: font file and actual point size from the
PIL truetype size used at the composite density.

Writes <out>/qa/verify_figures.json, <out>/qa/overview_final_size.tiff and
<out>/qa/preview/<name>.png (downscaled previews; review only).
Exit 0 when every check passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paper_style as ps  # noqa: E402
from plot_figures import FIGURE_NAMES  # noqa: E402
from verify_core import (figure_entry, font_and_strokes, overview, pl_check,  # noqa: E402
                           tiff_facts)

Image.MAX_IMAGE_PIXELS = None


def imported_evidence(p, rec_dpi):
    ev_path = p.get("evidence_json")
    scale = (p.get("placement") or {}).get("physical_scale")
    if not (ev_path and Path(ev_path).exists() and scale):
        return {"fonts_actual": "unverified (imported artwork, no renderer evidence)",
                "line_widths_pt": "unverified (imported artwork, no renderer evidence)",
                "text_sizes_pt": "unverified (imported artwork, no renderer evidence)",
                "evidence": None, "problems": [], "flag": "baked-in text/strokes need visual review"}
    ev = json.loads(Path(ev_path).read_text())
    name = ev.get("figure", "")
    # Artwork derived from a pipeline figure (e.g. 07_mean_spectrum_vector) follows that figure's stroke rule.
    name = next((n for n in FIGURE_NAMES if n[:3] == name[:3]), name)
    fs = font_and_strokes(ev, name)
    # Sizes at placement = source size x physical scale (scale 1.0 for native placement).
    sizes = sorted({(r, round(s * scale, 3)) for r, s in fs["text_sizes_pt"]})
    widths = {k: sorted({round(w * scale, 4) for w in v}) for k, v in fs["line_widths_pt"].items()}
    problems = list(fs["problems"])
    if abs(scale - 1.0) > 0.005:
        problems.append(f"artwork placed at scale {scale:.4f}: baked-in type is no longer 12/10 pt")
    return {"fonts_actual": fs["fonts_actual"], "text_sizes_pt": sizes, "line_widths_pt": widths,
            "physical_scale": scale,
            "evidence": f"source renderer record {Path(ev_path).name} (glyph fonts, artist sizes and widths), "
                        f"scaled by the measured placement scale",
            "problems": problems}


def composite_entry(tif, pl_npz):
    rec = json.loads(tif.with_suffix(".json").read_text())
    dpi = rec["dpi"]
    entry = {"tiff": tiff_facts(tif), "checks": rec["checks"], "grid": rec["grid"], "dpi": dpi,
             "canvas_ink_clearance_mm": rec.get("canvas_ink_clearance_mm"), "panels": []}
    ok = entry["tiff"]["export_pass"] and entry["tiff"]["nature_width"] and all(rec["checks"].values())
    rgb = None
    for p in rec["panels"]:
        item = {"label": p["label"], "spec": p["spec"], "kind": p["kind"], "box_px": p["box_px"],
                "placed_mm": [round(p["box_px"][2] / dpi * 25.4, 2), round(p["box_px"][3] / dpi * 25.4, 2)]}
        if p["kind"] == "data":
            srec = json.loads(Path(p["render"]["style_json"]).read_text())
            ev = font_and_strokes(srec, p["name"], srec.get("axis_overrides"))
            item.update({"fonts_actual": ev["fonts_actual"], "line_widths_pt": ev["line_widths_pt"],
                         "text_sizes_pt": ev["text_sizes_pt"], "problems": ev["problems"],
                         "axis_overrides": srec.get("axis_overrides", {}),
                         "evidence": "panel render record at composite density (style.json)"})
            # Overrides are expected only when the composite was rendered from an explicit
            # --config-dir (Batch 6 demo: saved labels/legend/interval); a default
            # composite must not pick up saved menu settings.
            explicit_cfg = "--config-dir" in (rec.get("command") or [])
            item["overrides_expected"] = explicit_cfg
            if srec.get("axis_overrides") and not explicit_cfg:
                item["problems"].append("default composite uses saved menu overrides")
            if p["name"] == "05_PL_image":
                if rgb is None:
                    rgb = np.asarray(Image.open(tif).convert("RGB"))
                x, y, w, h = (int(round(v)) for v in p["box_px"])
                item["pl_pixels"] = pl_check(rgb[y:y + h, x:x + w], pl_npz)
                if not item["pl_pixels"]["pass"]:
                    item["problems"].append("PL pixels differ from viridis(native)")
        else:
            item.update(imported_evidence(p, dpi))
            item.update({"effective_dpi_at_placement": round(p.get("effective_dpi", 0), 1),
                         "resampled": p.get("resampled"), "rasterization": p.get("rasterization"),
                         "placement": p.get("placement")})
            if p["kind"] == "pdf":
                import pymupdf
                with pymupdf.open(p["path"]) as doc:
                    item["pdf_embedded_fonts"] = sorted({f[3] for f in doc[p["page"] - 1].get_fonts()})
        ok = ok and not item["problems"]
        entry["panels"].append(item)
    lab = rec["label"]
    px = lab.get("truetype_px", round(lab["text_pt"] / 72 * dpi))
    # Re-open the exact font file at the recorded size and read back its names.
    from PIL import ImageFont
    f = ImageFont.truetype(lab["font"], px)
    fam, style = f.getname()
    entry["panel_letters"] = {"font": lab["font"], "font_family_resolved": fam, "font_style_resolved": style,
                              "format": lab.get("format"), "texts": lab.get("texts"),
                              "requested_pt": lab["text_pt"], "truetype_px": px,
                              "actual_pt": round(px / dpi * 72, 3), "settings_source": lab.get("settings_source"),
                              "evidence": "PIL truetype size at the composite density (font file re-opened)"}
    entry["panel_letters"]["pass"] = (fam == "Arial" and style == "Bold"
                                      and abs(entry["panel_letters"]["actual_pt"] - lab["text_pt"]) <= 0.05)
    if not entry["panel_letters"]["pass"]:
        ok = False
    entry["pass"] = ok
    return entry


def previews(out, items, preview_dpi):
    pdir = out / "qa" / "preview"
    pdir.mkdir(parents=True, exist_ok=True)
    made = []
    for label, path, _mm in items:
        with Image.open(path) as im:
            s = preview_dpi / float(im.info["dpi"][0])
            small = im.convert("RGB").resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                                             Image.LANCZOS)
        dst = pdir / (label.replace("/", "__").removesuffix(".tiff") + ".png")
        small.save(dst, dpi=(preview_dpi, preview_dpi))
        made.append(str(dst))
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--default-config-dir", type=Path, default=None,
                    help="config dir the top-level (default) renders were made with, e.g. demo/demo_config; "
                         "their overrides must equal it exactly (else: no overrides allowed)")
    ap.add_argument("--sheet-width-mm", type=float, default=390.0)
    ap.add_argument("--preview-dpi", type=float, default=150.0)
    ap.add_argument("--json-name", default="verify_figures.json")
    a = ap.parse_args()
    out = a.out.resolve()
    qa = out / "qa"
    res = {"tool": "verify_figures.py", "spec_pt": {"axis_label": ps.AXIS_LABEL_PT, "tick_legend_annotation": ps.TICK_PT},
           "figures": {}, "composites": {}}
    for n in FIGURE_NAMES:
        if (out / f"{n}.tiff").exists():
            res["figures"][n] = figure_entry(out, n, out / "source_data")
            expected = {}
            if a.default_config_dir is not None:
                import figure_config as fc
                cfg = fc.load(n, a.default_config_dir)
                if cfg:
                    expected = dict(cfg["axes"])
                    expected.update({k: cfg[k] for k in ("labels", "legend", "heatmap", "palette") if cfg.get(k)})
                    expected = json.loads(json.dumps(expected))
            if res["figures"][n]["axis_overrides"] != expected:
                res["figures"][n]["evidence"]["problems"].append(
                    "default render picked up saved overrides" if not expected
                    else "default render overrides differ from --default-config-dir")
                res["figures"][n]["pass"] = False
    # Optional groups (kit demo / menu acceptance layouts).
    for key, sub, expect in (("double_column", "double_column", False), ("menu_before", "qa/before", False),
                             ("menu_after", "qa/after", True), ("menu_renders", "qa/menu_renders", True)):
        d = out / sub
        for n in FIGURE_NAMES:
            if (d / f"{n}.tiff").exists():
                res.setdefault(key, {})[n] = figure_entry(d, n, d / "source_data", overrides_expected=expect)
    if res.get("menu_after") and res.get("menu_renders"):
        res["menu_reload_identical"] = {}
        for n in res["menu_after"]:
            if n in res["menu_renders"]:
                a1 = np.asarray(Image.open(qa / "after" / f"{n}.tiff"))
                a2 = np.asarray(Image.open(qa / "menu_renders" / f"{n}.tiff"))
                res["menu_reload_identical"][n] = a1.shape == a2.shape and bool((a1 == a2).all())
    pl_npz = out / "source_data" / "PL_image.npz"
    if not pl_npz.exists():
        pl_npz = qa / "before" / "source_data" / "PL_image.npz"
    for tif in sorted((out / "composite").glob("*.tiff")):
        res["composites"][tif.name] = composite_entry(tif, pl_npz)

    items = [(n, out / f"{n}.tiff", e["tiff"]["mm"]) for n, e in res["figures"].items()]
    items += [(f"double_column/{n}", out / "double_column" / f"{n}.tiff", e["tiff"]["mm"])
              for n, e in res.get("double_column", {}).items()]
    items += [(f"composite/{k}", out / "composite" / k, e["tiff"]["mm"]) for k, e in res["composites"].items()]
    res["overview"] = overview(out, items, a.sheet_width_mm)
    res["previews"] = previews(out, items, a.preview_dpi)

    groups = [g for g in ("figures", "double_column", "composites", "menu_before", "menu_after", "menu_renders")
              if g in res]
    res["summary"] = {g: {k: v["pass"] for k, v in res[g].items()} for g in groups}
    all_ok = all(all(v.values()) for v in res["summary"].values()) and \
        all(res.get("menu_reload_identical", {}).values())
    res["all_pass"] = all_ok
    for g in groups:
        for k, v in res[g].items():
            t = v["tiff"]
            print(f"{'PASS' if v['pass'] else 'FAIL'} {g}/{k}: {t['px'][0]}x{t['px'][1]} px @ {t['dpi'][0]:g} dpi = "
                  f"{t['mm'][0]:.2f} x {t['mm'][1]:.2f} mm {t['compression']} ICC={t['icc_profile']}")
            probs = v.get("evidence", {}).get("problems", []) + [f"{p['label']}: {q}" for p in v.get("panels", [])
                                                                  for q in p.get("problems", [])]
            for q in probs:
                print("    -", q)
    print("OVERVIEW:", res["overview"]["path"], res["overview"]["px"], res["overview"]["mm"])
    print("PREVIEWS:", len(res["previews"]), "in", qa / "preview")
    if "menu_reload_identical" in res:
        print("menu reload identical:", res["menu_reload_identical"])
    (qa / a.json_name).write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    print("ALL PASS" if all_ok else "SOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
