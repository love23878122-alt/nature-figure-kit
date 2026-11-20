"""Text-fit QA at final size for figures and composites.

    python text_fit.py --out OUT [--figures-only]

Evidence: renderer bounding boxes (``qa/<name>.style.json``, Matplotlib Agg at the
final export density) for every visible text element. For composites, each data
panel's boxes are mapped from its padded panel render into composite pixels
(``render_origin_px``); imported artwork with an ``<file>.evidence.json`` sidecar
is mapped by its placement offset and uniform scale. The rendered panel-letter
boxes (PIL ``textbbox``) are included. Imported artwork without a sidecar is
listed as "baked-in text without renderer evidence (visual review)".

Checks per output:
  * text_collisions   - any two visible text boxes intersect (> 0.5 px)
  * tick_collisions   - subset where both boxes are tick labels
  * text_in_data_box  - axis/tick labels intruding into an axes box
  * clipped_canvas    - text box beyond the canvas edge
  * clipped_crop      - composite: panel text beyond its cell/frame crop boundary
  * label_vs_artwork  - composite: a panel letter intersects any panel frame/axes box or text
  * edge_clearance_mm - exported ink-to-edge clearance measured on the TIFF (target 1-2 mm)
  * colorbar_label_clearance - composite: horizontal clearance (mm) from each colour-bar
    label to the axis label (and nearest text) of the panel to its right; a collision fails
  * ylabel_alignment  - composite: y-label left edges per column in final composite px

Writes <out>/qa/text_fit.json; exit 0 when every output passes.
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

Image.MAX_IMAGE_PIXELS = None
TOL = 0.5          # px; boxes must overlap by more than this to count
EDGE_MIN_MM, EDGE_MAX_MM = 0.95, 2.05   # 1-2 mm target, with half-pixel rounding slack


def overlap(a, b, tol=TOL):
    return min(a[2], b[2]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[1], b[1]) > tol


def is_tick(role):
    return "tick." in role


def text_items(rec, dx=0.0, dy=0.0, s=1.0, panel=None):
    out = []
    for t in rec["texts"]:
        x0, y0, x1, y1 = t["bbox_px"]
        out.append({"panel": panel, "role": t["role"], "text": t["text"], "size_pt": t["size_pt"],
                    "bbox": [dx + s * x0, dy + s * y0, dx + s * x1, dy + s * y1]})
    return out


def axes_boxes(rec, dx=0.0, dy=0.0, s=1.0):
    boxes = []
    for key, b in (("main", rec["main_axes"]["box_px"]), ("colorbar", (rec.get("colorbar") or {}).get("box_px"))):
        if b:
            boxes.append((key, [dx + s * b["x0"], dy + s * b["top"], dx + s * b["x1"], dy + s * b["bottom"]]))
    return boxes


def pairwise(items):
    text, tick = [], []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if overlap(a["bbox"], b["bbox"]):
                pair = [f"{a['panel'] or ''}{a['role']}:{a['text']}", f"{b['panel'] or ''}{b['role']}:{b['text']}"]
                text.append(pair)
                if is_tick(a["role"]) and is_tick(b["role"]):
                    tick.append(pair)
    return text, tick


def intrusions(items, boxes):
    """Axis labels and tick labels must sit outside every axes box (legends/annotations may be inside)."""
    hits = []
    for t in items:
        if not (is_tick(t["role"]) or t["role"].endswith(("xlabel", "ylabel"))):
            continue
        for key, b in boxes:
            if t.get("panel_boxes") is not None and (key, b) not in t["panel_boxes"]:
                continue
            if overlap(t["bbox"], b, tol=1.0):
                hits.append(f"{t['panel'] or ''}{t['role']}:{t['text']} in {key} box")
    return hits


def outside(items, rect):
    x0, y0, x1, y1 = rect
    return [f"{t['panel'] or ''}{t['role']}:{t['text']}" for t in items
            if t["bbox"][0] < x0 - TOL or t["bbox"][1] < y0 - TOL or t["bbox"][2] > x1 + TOL or t["bbox"][3] > y1 + TOL]


def edge_clearance(tif):
    with Image.open(tif) as im:
        dpi = float(im.info["dpi"][0])
        arr = np.asarray(im.convert("RGB"))
    c = ps.edge_clearance_px(arr)
    mm = {k: round(v / dpi * 25.4, 3) for k, v in c.items()}
    return mm, all(EDGE_MIN_MM <= v <= EDGE_MAX_MM for v in mm.values())


def figure_fit(out, name):
    tif = out / f"{name}.tiff"
    rec = json.loads((out / "qa" / f"{name}.style.json").read_text())
    W, H = rec["canvas_px"]
    items = text_items(rec)
    text, tick = pairwise(items)
    clear, clear_ok = edge_clearance(tif)
    res = {"tiff": str(tif), "canvas_px": [W, H], "dpi": rec["dpi"], "target_mm": rec["target_mm"],
           "n_text": len(items), "text_sizes_pt": sorted({t["size_pt"] for t in items}),
           "evidence_coverage": {"texts_with_renderer_boxes": len(items), "texts_without_evidence": 0,
                                 "source": "Matplotlib renderer get_window_extent at final size"},
           "text_collisions": text, "tick_collisions": tick,
           "text_in_data_box": intrusions(items, axes_boxes(rec)),
           "clipped_canvas": outside(items, (0, 0, W, H)),
           "edge_clearance_mm": clear, "edge_clearance_in_1_2_mm": clear_ok,
           "legend_data_overlap": rec["legend_data_overlap"],
           "layout": {k: rec["layout"].get(k) for k in ("tick_thinning", "legend", "height_grown_mm")
                      if rec["layout"].get(k) is not None}}
    res["pass"] = not (text or tick or res["text_in_data_box"] or res["clipped_canvas"]
                       or res["legend_data_overlap"]) and clear_ok
    return res


def colorbar_clearance(rec, items, dpi):
    """Colour-bar label -> neighbouring panel (to the right) axis label, in final composite px."""
    out = []
    panels = {p["label"]: p for p in rec["panels"]}
    for p in rec["panels"]:
        cbl = [t for t in items if t["panel"] == f"{p['label']}:" and t["role"] == "colorbar.ylabel"]
        if not cbl:
            continue
        cb = cbl[0]
        rows = set(range(p["row"], p["row"] + p["row_span"]))
        for q in panels.values():
            if q["col"] != p["col"] + p["col_span"] or not rows & set(range(q["row"], q["row"] + q["row_span"])):
                continue
            qt = [t for t in items if t["panel"] == f"{q['label']}:"]
            ylab = [t for t in qt if t["role"] == "axes.ylabel"]
            near = min(qt, key=lambda t: t["bbox"][0], default=None)
            entry = {"colorbar_label": f"{p['label']}:{cb['text']}", "neighbour": q["label"],
                     "colorbar_label_x1_px": round(cb["bbox"][2], 2),
                     "colorbar_gap_pt": rec.get("colorbar_gap_pt"), "colorbar_labelpad_pt": rec.get("colorbar_labelpad_pt")}
            for key, t in (("axis_label", ylab[0] if ylab else None), ("nearest_text", near)):
                if t is None:
                    entry[key] = None
                    continue
                gap = t["bbox"][0] - cb["bbox"][2]
                entry[key] = {"text": f"{t['role']}:{t['text']}", "x0_px": round(t["bbox"][0], 2),
                              "clearance_mm": round(gap / dpi * 25.4, 3),
                              "collision": bool(overlap(cb["bbox"], t["bbox"], tol=0.0) or gap <= 0
                                                and min(cb["bbox"][3], t["bbox"][3]) > max(cb["bbox"][1], t["bbox"][1]))}
            entry["collision"] = any((entry[k] or {}).get("collision") for k in ("axis_label", "nearest_text"))
            out.append(entry)
    return out


def composite_fit(tif):
    rec = json.loads(tif.with_suffix(".json").read_text())
    W, H = rec["canvas_px"]
    dpi = rec["dpi"]
    items, boxes, frames, panels_out, gaps = [], [], [], [], []
    for p in rec["panels"]:
        tag = f"{p['label']}:"
        entry = {"label": p["label"], "spec": p["spec"], "kind": p["kind"], "crop_px": p.get("crop_px")}
        if p["kind"] == "data":
            srec = json.loads(Path(p["render"]["style_json"]).read_text())
            ox, oy = p["render_origin_px"]
            its = text_items(srec, ox, oy, 1.0, tag)
            bxs = axes_boxes(srec, ox, oy)
            entry.update({"evidence": "panel renderer boxes mapped by render_origin_px",
                          "texts_with_renderer_boxes": len(its), "texts_without_evidence": 0,
                          "text_sizes_pt": sorted({t["size_pt"] for t in its}),
                          "panel_render_text_outside_canvas": srec["text_outside_canvas"],
                          "legend_data_overlap": srec["legend_data_overlap"]})
            frames.append((f"{tag}axes", [b for k, b in bxs if k == "main"][0]))
            frames += [(f"{tag}{k}", b) for k, b in bxs if k != "main"]
        else:
            bx, by, bw, bh = p["box_px"]
            frame = [bx, by, bx + bw, by + bh]
            frames.append((f"{tag}artwork_frame", frame))
            bxs, its = [], []
            ev_path = p.get("evidence_json")
            if ev_path and Path(ev_path).exists():
                ev = json.loads(Path(ev_path).read_text())
                s = bw / ev["canvas_px"][0]
                its = text_items(ev, bx, by, s, tag)
                for t in its:
                    t["size_pt"] = round(t["size_pt"] * (p.get("placement") or {}).get("physical_scale", 1.0), 3)
                bxs = axes_boxes(ev, bx, by, s)
                entry.update({"evidence": f"source renderer boxes from {Path(ev_path).name}, uniform scale "
                                          f"{s:.5f} px/px, offset {[bx, by]}",
                              "physical_scale": (p.get("placement") or {}).get("physical_scale"),
                              "texts_with_renderer_boxes": len(its), "texts_without_evidence": 0,
                              "text_sizes_pt_at_placement": sorted({t["size_pt"] for t in its})})
            else:
                gaps.append(p["spec"])
                entry.update({"evidence": "none: baked-in text without renderer evidence (visual review)",
                              "texts_with_renderer_boxes": 0, "texts_without_evidence": "unknown"})
        for t in its:
            t["panel_boxes"] = bxs
        crop = p.get("crop_px")
        entry["clipped_crop"] = outside(its, crop) if crop else []
        entry["text_in_data_box"] = intrusions(its, bxs)
        items += its
        boxes += bxs
        panels_out.append(entry)
    # Shared legend in an empty cell (make_composite --empty-cells legend): its 10 pt
    # text boxes join the collision checks and must stay inside the legend cell.
    legend_out, leg = None, rec.get("legend")
    if leg:
        its = [{"panel": "legend:", "role": t["role"], "text": t["text"], "size_pt": t["size_pt"],
                "bbox": [float(v) for v in t["bbox_px"]], "panel_boxes": []} for t in leg["texts"]]
        legend_out = {"cell_rc_1based": leg.get("cell_rc_1based"), "cell_px": leg["cell_px"],
                      "evidence": "legend renderer boxes (Matplotlib Agg at the composite dpi) mapped by the cell origin",
                      "texts_with_renderer_boxes": len(its), "text_sizes_pt": sorted({t["size_pt"] for t in its}),
                      "all_glyphs_arial_bold": all(t.get("all_glyphs_in_resolved_face") for t in leg["texts"]),
                      "clipped_cell": outside(its, leg["cell_px"])}
        legend_out["pass"] = (not legend_out["clipped_cell"] and legend_out["text_sizes_pt"] == [10.0]
                              and legend_out["all_glyphs_arial_bold"])
        items += its
    # Panel letters (rendered PIL boxes).
    letters = []
    for p in rec["panels"]:
        lb = p["label_px"]["bbox"]
        letters.append({"panel": None, "role": "panel_label", "text": p.get("label_text", p["label"]),
                        "size_pt": rec["label"]["text_pt"],
                        "bbox": [float(v) for v in lb]})
    letter_hits = []
    for L in letters:
        for name, fr in frames:
            if overlap(L["bbox"], fr, tol=0.0):
                letter_hits.append(f"label {L['text']} vs {name}")
        for t in items:
            if overlap(L["bbox"], t["bbox"], tol=0.0):
                letter_hits.append(f"label {L['text']} vs {t['panel']}{t['role']}:{t['text']}")
    for t in items:
        t.pop("panel_boxes", None)
    all_items = items + letters
    cbc = colorbar_clearance(rec, items, dpi)
    text, tick = pairwise(all_items)
    clear, clear_ok = edge_clearance(tif)
    label_pt_actual = round(rec["label"].get("truetype_px", round(rec["label"]["text_pt"] / 72 * dpi)) / dpi * 72, 3)
    res = {"tiff": str(tif), "canvas_px": [W, H], "dpi": dpi, "grid": rec["grid"],
           "n_text": len(all_items), "panel_letters": letters, "panel_letter_pt_actual": label_pt_actual,
           "panels": panels_out,
           "evidence_coverage": {"texts_with_renderer_boxes": len(items), "panel_letters": len(letters),
                                 "artwork_without_evidence": gaps},
           "text_collisions": text, "tick_collisions": tick,
           "text_in_data_box": [h for e in panels_out for h in e["text_in_data_box"]],
           "clipped_canvas": outside(all_items, (0, 0, W, H)),
           "clipped_crop": [h for e in panels_out for h in e["clipped_crop"]],
           "label_vs_artwork": letter_hits,
           "edge_clearance_mm": clear, "edge_clearance_in_1_2_mm": clear_ok,
           "composite_checks": rec["checks"], "legend": legend_out,
           "spans": rec.get("spans"), "empty_cells": rec.get("empty_cells"),
           "colorbar_label_clearance": cbc,
           "colorbar_label_min_clearance_mm": min((e["axis_label"]["clearance_mm"] for e in cbc if e["axis_label"]),
                                                  default=None),
           "ylabel_alignment": (rec.get("alignment") or {}).get("ylabel_alignment_per_column"),
           "height_mm": rec.get("height_mm")}
    if legend_out:
        res["evidence_coverage"]["legend_texts"] = legend_out["texts_with_renderer_boxes"]
        res["clipped_crop"] += [f"legend {h}" for h in legend_out["clipped_cell"]]
    res["pass"] = not (text or tick or res["text_in_data_box"] or res["clipped_canvas"] or res["clipped_crop"]
                       or (legend_out is not None and not legend_out["pass"])
                       or any(e["collision"] for e in cbc)
                       or letter_hits or any(e.get("legend_data_overlap") for e in panels_out)
                       or any(e.get("panel_render_text_outside_canvas") for e in panels_out)) \
        and clear_ok and all(rec["checks"].values())
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--figures-only", action="store_true")
    a = ap.parse_args()
    out = a.out.resolve()
    res = {"tool": "text_fit.py", "tolerance_px": TOL, "edge_target_mm": [1.0, 2.0],
           "figures": {}, "composites": {}}
    for n in FIGURE_NAMES:
        if (out / f"{n}.tiff").exists():
            res["figures"][n] = figure_fit(out, n)
    if not a.figures_only:
        for tif in sorted((out / "composite").glob("*.tiff")):
            res["composites"][tif.name] = composite_fit(tif)
    ok = True
    for g in ("figures", "composites"):
        for k, v in res[g].items():
            ok = ok and v["pass"]
            print(f"{'PASS' if v['pass'] else 'FAIL'} {g}/{k}: texts={v['n_text']} collisions={len(v['text_collisions'])} "
                  f"tick={len(v['tick_collisions'])} in_box={len(v['text_in_data_box'])} "
                  f"clip={len(v['clipped_canvas'])}{' crop=%d letters=%d' % (len(v['clipped_crop']), len(v['label_vs_artwork'])) if g == 'composites' else ''} "
                  f"edge_mm={v['edge_clearance_mm']}")
            for key in ("text_collisions", "text_in_data_box", "clipped_canvas", "clipped_crop", "label_vs_artwork"):
                for h in v.get(key, [])[:6]:
                    print(f"    {key}: {h}")
    res["all_pass"] = ok
    (out / "qa").mkdir(parents=True, exist_ok=True)
    (out / "qa" / "text_fit.json").write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
