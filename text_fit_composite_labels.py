"""Panel-label fit and font evidence for composites at final placement size.

    python text_fit_composite_labels.py --out OUT [--expect-format '(a)'] [--expect-pt 14]
                                        [--json NAME] [--glob '*.tiff']

For every ``<out>/composite/*.tiff`` (with its ``.json`` layout record):

* Runs the full composite text-fit of ``text_fit.composite_fit`` (renderer
  boxes of every data-panel text and of imported artwork with an evidence sidecar,
  mapped into composite pixels; collisions, tick collisions, clipping, crop, edges).
* Label geometry: each rendered label box (PIL ``textbbox`` at the composite dpi)
  against every axes box, colour bar, imported artwork frame, every other text box
  (ticks, axis labels, legends, offsets, other labels), the canvas, and its own
  panel cell (crop boundary). Minimum clearance to the nearest frame/text in mm.
* Label pixels: the ink bbox measured on the saved TIFF inside the label's cell
  band must equal the PIL box (no clipping, nothing else drawn there), and the
  label is re-rendered from the resolved font file at the recorded size and
  compared pixel-by-pixel with the TIFF crop (proves font face and size).
* Font: family/style read back from the font file, size in pt =
  truetype px / dpi x 72, format and texts in reading order.

Writes <out>/qa/<json> (default text_fit_composite_labels.json); exit 0 when all pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figure_config as fc  # noqa: E402
import text_fit as tf  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def gap_px(a, b):
    """Clearance between two boxes (0 when they touch or overlap)."""
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return float(np.hypot(dx, dy)) if dx and dy else float(max(dx, dy))


def frames_and_texts(rec):
    """All axes/colour-bar/artwork frames and mapped renderer text boxes in composite px."""
    frames, texts = [], []
    for p in rec["panels"]:
        tag = f"{p['label']}:"
        if p["kind"] == "data":
            srec = json.loads(Path(p["render"]["style_json"]).read_text())
            ox, oy = p["render_origin_px"]
            texts += tf.text_items(srec, ox, oy, 1.0, tag)
            frames += [(f"{tag}{k}", b) for k, b in tf.axes_boxes(srec, ox, oy)]
        else:
            bx, by, bw, bh = p["box_px"]
            frames.append((f"{tag}artwork_frame", [bx, by, bx + bw, by + bh]))
            ev = p.get("evidence_json")
            if ev and Path(ev).exists():
                e = json.loads(Path(ev).read_text())
                s = bw / e["canvas_px"][0]
                texts += tf.text_items(e, bx, by, s, tag)
                frames += [(f"{tag}{k}", b) for k, b in tf.axes_boxes(e, bx, by, s)]
    leg = rec.get("legend")
    if leg:   # shared legend in an empty cell: its text boxes count like any other 10 pt text
        texts += [{"panel": "legend:", "role": t["role"], "text": t["text"], "size_pt": t["size_pt"],
                   "bbox": [float(v) for v in t["bbox_px"]]} for t in leg["texts"]]
    return frames, texts


def label_check(tif, expect_format, expect_pt):
    rec = json.loads(tif.with_suffix(".json").read_text())
    lab = rec["label"]
    dpi = rec["dpi"]
    W, H = rec["canvas_px"]
    with Image.open(tif) as im:
        rgb = np.asarray(im.convert("RGB"))
    gray = rgb.min(axis=2)
    font = ImageFont.truetype(lab["font"], lab["truetype_px"])
    fam, style = font.getname()
    frames, texts = frames_and_texts(rec)
    labels = [(p, [float(v) for v in p["label_px"]["bbox"]]) for p in rec["panels"]]
    per_label, ok = [], True
    for p, bb in labels:
        hits = [f"{n}" for n, fr in frames if tf.overlap(bb, fr, tol=0.0)]
        hits += [f"{t['panel']}{t['role']}:{t['text']}" for t in texts if tf.overlap(bb, t["bbox"], tol=0.0)]
        hits += [f"label {q.get('label_text', q['label'])}" for q, ob in labels if q is not p and tf.overlap(bb, ob, tol=0.0)]
        near_frame = min(((gap_px(bb, fr), n) for n, fr in frames), default=(None, None))
        near_text = min(((gap_px(bb, t["bbox"]), f"{t['panel']}{t['role']}:{t['text']}") for t in texts),
                        default=(None, None))
        cx0, cy0, cx1, cy1 = p["crop_px"] if p["kind"] == "data" else (
            p["cell_px"][0], p["cell_px"][1], p["cell_px"][0] + p["cell_px"][2], p["cell_px"][1] + p["cell_px"][3])
        in_cell = bb[0] >= cx0 and bb[1] >= cy0 and bb[2] <= cx1 and bb[3] <= cy1
        in_canvas = bb[0] >= 0 and bb[1] >= 0 and bb[2] <= W and bb[3] <= H
        # Pixel evidence: re-render the label from the font file and compare with the TIFF.
        x0, y0 = (int(v) for v in bb[:2])
        x1, y1 = (int(np.ceil(v)) for v in bb[2:])
        pad = 4
        X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
        crop = gray[Y0:Y1, X0:X1]
        ref = Image.new("L", (W, H), 255)  # full canvas so sub-pixel placement matches
        # Redraw from the font file at the recorded baseline and size, as make_composite did.
        ImageDraw.Draw(ref).text(tuple(p["label_px"]["baseline_xy"]), p["label_text"], font=font, fill=0, anchor="ls")
        refc = np.asarray(ref)[Y0:Y1, X0:X1]
        diff = np.abs(crop.astype(int) - refc.astype(int))
        ink = np.argwhere(crop < 250)
        ink_bbox = ([int(ink[:, 1].min() + X0), int(ink[:, 0].min() + Y0), int(ink[:, 1].max() + X0 + 1),
                     int(ink[:, 0].max() + Y0 + 1)] if len(ink) else None)
        ink_inside = bool(ink_bbox) and ink_bbox[0] >= x0 and ink_bbox[1] >= y0 and ink_bbox[2] <= x1 and ink_bbox[3] <= y1
        pix_match = int(diff.max()) <= 1
        entry = {"panel": p["label"], "text": p["label_text"], "spec": p["spec"], "bbox_px": bb,
                 "size_mm": [round((bb[2] - bb[0]) / dpi * 25.4, 3), round((bb[3] - bb[1]) / dpi * 25.4, 3)],
                 "overlaps": hits,
                 "min_clearance_to_frame_mm": None if near_frame[0] is None else round(near_frame[0] / dpi * 25.4, 3),
                 "nearest_frame": near_frame[1],
                 "min_clearance_to_text_mm": None if near_text[0] is None else round(near_text[0] / dpi * 25.4, 3),
                 "nearest_text": near_text[1],
                 "inside_cell_crop": in_cell, "inside_canvas": in_canvas,
                 "tiff_ink_bbox_px": ink_bbox, "tiff_ink_inside_label_box": ink_inside,
                 "rerender_max_abs_diff": int(diff.max()), "rerender_pixel_match": pix_match,
                 "offset_from_box_corner_mm": p["label_px"]["offset_from_box_corner_mm"]}
        entry["pass"] = not hits and in_cell and in_canvas and ink_inside and pix_match
        ok = ok and entry["pass"]
        per_label.append(entry)
    actual_pt = lab["truetype_px"] / dpi * 72
    texts_expected = [fc.format_panel_label(expect_format, i) for i in range(len(rec["panels"]))]
    font_ev = {"font_file": lab["font"], "family": fam, "style": style, "truetype_px": lab["truetype_px"],
               "dpi": dpi, "actual_pt": round(actual_pt, 4), "requested_pt": lab["text_pt"],
               "format": lab.get("format"), "texts": lab.get("texts"), "expected_texts": texts_expected,
               "settings_source": lab.get("settings_source"),
               "is_arial_bold": fam == "Arial" and style == "Bold",
               "size_ok": abs(actual_pt - expect_pt) <= 0.01,
               "format_ok": lab.get("format") == expect_format and lab.get("texts") == texts_expected}
    font_ok = font_ev["is_arial_bold"] and font_ev["size_ok"] and font_ev["format_ok"]
    full = tf.composite_fit(tif)
    other_sizes = sorted({t["size_pt"] for t in texts})
    res = {"tiff": str(tif), "width_mm": rec["width_mm"], "height_mm": round(rec["height_mm"], 3),
           "grid": rec["grid"], "dpi": dpi, "canvas_px": [W, H],
           "label_font": font_ev, "labels": per_label,
           "other_text_sizes_pt": other_sizes,
           "other_text_not_shrunk": all(s >= 10.0 - 0.01 for s in other_sizes),
           "full_text_fit": {k: full[k] for k in ("n_text", "text_collisions", "tick_collisions", "text_in_data_box",
                                                   "clipped_canvas", "clipped_crop", "label_vs_artwork",
                                                   "edge_clearance_mm", "edge_clearance_in_1_2_mm",
                                                   "evidence_coverage", "composite_checks", "legend", "pass")},
           "spans": rec.get("spans"), "positions": rec.get("positions"), "empty_cells": rec.get("empty_cells"),
           "auto_layout": None if not rec.get("auto_layout") else {
               k: rec["auto_layout"].get(k) for k in ("selected_grid", "selection_reason", "forced",
                                                      "failed_criteria")},
           "baked_in_text_without_evidence": full["evidence_coverage"]["artwork_without_evidence"]}
    res["pass"] = ok and font_ok and full["pass"] and res["other_text_not_shrunk"]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expect-format", default=fc.LABEL_FORMAT_DEFAULT)
    ap.add_argument("--expect-pt", type=float, default=fc.LABEL_PT_DEFAULT)
    ap.add_argument("--json", default="text_fit_composite_labels.json")
    ap.add_argument("--dir", default="composite", help="sub-directory of --out holding the composites")
    ap.add_argument("--glob", default="*.tiff")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    res = {"tool": "text_fit_composite_labels.py", "expected": {"format": a.expect_format, "pt": a.expect_pt,
                                                                "font": "Arial Bold"},
           "tolerance_px": tf.TOL, "composites": {}}
    for tif in sorted((out / a.dir).glob(a.glob)):
        if tif.with_suffix(".json").exists():
            res["composites"][tif.name] = r = label_check(tif, a.expect_format, a.expect_pt)
            f = r["label_font"]
            print(f"{'PASS' if r['pass'] else 'FAIL'} {tif.name}: {r['width_mm']:g} x {r['height_mm']:.2f} mm, "
                  f"labels {f['texts']} {f['family']} {f['style']} {f['actual_pt']} pt; "
                  f"label overlaps={sum(len(x['overlaps']) for x in r['labels'])} "
                  f"pixel_match={all(x['rerender_pixel_match'] for x in r['labels'])} "
                  f"min_clear_frame_mm={min(x['min_clearance_to_frame_mm'] for x in r['labels'])} "
                  f"min_clear_text_mm={min((x['min_clearance_to_text_mm'] for x in r['labels'] if x['min_clearance_to_text_mm'] is not None), default=None)} "
                  f"full_fit={r['full_text_fit']['pass']} edges={r['full_text_fit']['edge_clearance_mm']}")
            for x in r["labels"]:
                if not x["pass"]:
                    print(f"    {x['text']}: {x}")
    res["all_pass"] = bool(res["composites"]) and all(v["pass"] for v in res["composites"].values())
    (out / "qa").mkdir(parents=True, exist_ok=True)
    (out / "qa" / a.json).write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    print("ALL PASS" if res["all_pass"] else "SOME CHECKS FAILED")
    return 0 if res["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
