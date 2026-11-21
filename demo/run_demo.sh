#!/usr/bin/env bash
# Final check: reproduce example figures, a scripted menu session and composites
# from the bundled demo data only, then verify every TIFF.
#   bash demo/run_demo.sh [OUT_DIR]        (default: demo_out/ in the kit root)
# Uses $PYTHON if set, else python3. Exit 0 = everything passed.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1   # keep the kit free of __pycache__
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
OUT="${1:-$KIT/demo_out}"
DATA="$KIT/demo/data"
MAN="$KIT/demo/data_manifest.json"
mkdir -p "$OUT"
step() { echo; echo "=== $* ==="; }

step "1. example figures, 89 mm (spec defaults; demo-only XRD config: y tick numbers hidden, 'Intensity (a.u.)')"
# demo/demo_config/ holds only 02_XRD.json, so every other figure renders its spec defaults.
"$PY" "$KIT/make_figures.py" --data "$DATA" --manifest "$MAN" --out "$OUT" --config-dir "$KIT/demo/demo_config"

step "2. double column, 183 mm"
"$PY" "$KIT/make_figures.py" --data "$DATA" --manifest "$MAN" --out "$OUT/double_column" --double-column \
      --no-config --only 04_TPC_overlay_logtime,06_in_situ_PL_heatmap

step "3. scripted menu session (all ten figures) and automatic config reload"
"$PY" "$KIT/make_figures.py" --data "$DATA" --manifest "$MAN" --out "$OUT/qa/before" --no-config
"$PY" "$KIT/figmenu.py" --data "$DATA" --manifest "$MAN" --config-dir "$OUT/qa/configs" \
      --out "$OUT/qa/menu_renders" --script "$KIT/demo/menu_demo.keys" --transcript "$OUT/qa/menu_session.txt" \
      > "$OUT/qa/menu_stdout.log"
tail -n 3 "$OUT/qa/menu_session.txt"
"$PY" "$KIT/make_figures.py" --data "$DATA" --manifest "$MAN" --out "$OUT/qa/after" --config-dir "$OUT/qa/configs"

step "4. composites from data panels and from TIFF + PNG + PDF files, 89 and 183 mm"
"$PY" "$KIT/run_composites.py" --data "$DATA" --manifest "$MAN" --out "$OUT/composite"

step "5. text fit at final size (collisions, tick collisions, clipping, crop, edge clearance)"
"$PY" "$KIT/text_fit.py" --out "$OUT"

step "6. verify every TIFF"
"$PY" "$KIT/verify_figures.py" --out "$OUT" --default-config-dir "$KIT/demo/demo_config"

step "7. composite panel labels: default (a) 14 pt Arial Bold, fit and pixel evidence"
"$PY" "$KIT/text_fit_composite_labels.py" --out "$OUT"

step "8. saved label settings from the menu session (composite.json) re-render with (A) 12 pt"
"$PY" "$KIT/make_composite.py" --data "$DATA" --manifest "$MAN" --config-dir "$OUT/qa/configs" \
      --out "$OUT/qa/label_menu/composite/saved_labels.tiff" --panels 01_IR 03_TPC_overlay | tail -n 1
"$PY" "$KIT/text_fit_composite_labels.py" --out "$OUT/qa/label_menu" --expect-format "(A)" --expect-pt 12

step "9. Batch 5 composite layout: auto 4/6/7/8 panels at 89 and 183 mm, --force, spans, legends, invalid input"
"$PY" "$KIT/run_composites.py" --data "$DATA" --manifest "$MAN" --out "$OUT/b5/composite" \
      --qa-dir "$OUT/b5/qa" --preview-dir "$OUT/b5/preview" --layout-acceptance | grep -E "^(PASS|FAIL) case|^LAYOUT ACCEPTANCE"
grep -q "All cases as expected: \*\*True\*\*" "$OUT/b5/qa/layout_acceptance.md"
"$PY" "$KIT/text_fit_composite_labels.py" --out "$OUT/b5" --json text_fit_composite_labels_b5.json

step "10. scripted composite layout menu: auto/manual, spans, legend cell, save/reload/reset, preview renders"
mkdir -p "$OUT/b5/menu"
"$PY" "$KIT/figmenu.py" --data "$DATA" --manifest "$MAN" --config-dir "$OUT/b5/menu/configs" \
      --out "$OUT/b5/menu/composite" --double-column \
      --composite-panels 06_in_situ_PL_heatmap 03_TPC_overlay 04_TPC_overlay_logtime 07_in_situ_PL_mean_spectrum \
      --script "$KIT/demo/menu_layout.keys" --transcript "$OUT/b5/menu/menu_layout_session.txt" > "$OUT/b5/menu/stdout.log"
tail -n 1 "$OUT/b5/menu/menu_layout_session.txt"
grep -E "rendered .*composite_preview|render failed" "$OUT/b5/menu/menu_layout_session.txt" | cut -c1-160
"$PY" - "$OUT/b5/menu" <<'PYEOF'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
t = (d / "menu_layout_session.txt").read_text()
recs = {p.stem: json.loads(p.read_text()) for p in sorted((d / "composite").glob("composite_preview_*.json"))
        if not p.name.endswith(".nofit.json")}
saved = json.loads((d / "configs" / "composite.json").read_text())["composite"]
R = list(recs.values())
autos = [r for r in R if r.get("auto_layout")]
manual = [r for r in R if not r.get("auto_layout")]
checks = {
    "auto preview 2x3 with a=row and legend at 3,2": any(r["grid"] == [2, 3] and r["legend"]
        and r["legend"]["cell_rc_1based"] == [3, 2] and r["positions"][0]["col_span"] == 2 for r in autos),
    "unsaved reset renders displayed defaults (manual 2x2, no spans) despite saved auto config":
        any(r["grid"] == [2, 2] and r["spans"] == {} and r["empty_cells"]["use"] == "blank" for r in manual),
    "manual preview with a=row + legend": any(r["positions"][0]["col_span"] == 2 and r["legend"] for r in manual),
    "invalid span / legend inputs rejected in the menu": t.count("! rejected:") >= 3,
    "occupied legend cell reported, menu continued": t.count("! render failed") == 2,
    "saved config reloaded": saved == {"layout": "auto", "spans": {"a": "row"}, "empty_cells": "legend",
        "legend_cell": "3,2", "legend_entries": ["Sample 1=#2166AC:solid", "Sample 2=#B35806:dashed"]},
    "session ended": t.rstrip().endswith("bye"),
}
for k, v in checks.items():
    print(f"{'PASS' if v else 'FAIL'} menu layout: {k}")
sys.exit(0 if all(checks.values()) else 1)
PYEOF
"$PY" "$KIT/text_fit_composite_labels.py" --out "$OUT/b5/menu" --json text_fit_composite_labels_menu.json
step "11. Batch 6: label editors, legend text, heatmap interval, hidden tick numbers, shared composite legend"
B6="$OUT/b6"
mkdir -p "$B6/menu"
"$PY" "$KIT/figmenu.py" --data "$DATA" --manifest "$MAN" --config-dir "$B6/configs" --out "$B6/menu" --double-column \
      --composite-panels 06_in_situ_PL_heatmap 03_TPC_overlay 04_TPC_overlay_logtime 07_in_situ_PL_mean_spectrum \
      --script "$KIT/demo/menu_b6.keys" --transcript "$B6/menu/menu_b6_session.txt" > "$B6/menu/stdout.log"
tail -n 1 "$B6/menu/menu_b6_session.txt"
grep -E "WARNING" "$B6/menu/menu_b6_session.txt" | cut -c1-160
# Saved configs reload automatically: figures (89 mm) and the shared-legend composite (183 mm,
# d spans the last row, legend in cell 2,2, so no grid cell is left blank).
"$PY" "$KIT/make_figures.py" --data "$DATA" --manifest "$MAN" --out "$B6/qa/after" --config-dir "$B6/configs" \
      --only 01_IR,02_XRD,03_TPC_overlay,04_TPC_overlay_logtime,06_in_situ_PL_heatmap | grep -E "^RENDER"
"$PY" "$KIT/make_composite.py" --data "$DATA" --manifest "$MAN" --config-dir "$B6/configs" --double-column \
      --out "$B6/composite/shared_legend_span_183mm.tiff" \
      --panels 06_in_situ_PL_heatmap 03_TPC_overlay 04_TPC_overlay_logtime 07_in_situ_PL_mean_spectrum | tail -n 1 | cut -c1-160
"$PY" "$KIT/text_fit.py" --out "$B6/qa/after" --figures-only | tail -n 1
"$PY" "$KIT/text_fit.py" --out "$B6" | tail -n 1
"$PY" "$KIT/text_fit_composite_labels.py" --out "$B6" --json text_fit_composite_labels_b6.json | tail -n 1
"$PY" "$KIT/verify_figures.py" --out "$B6" | grep -E "^(PASS|FAIL)"
"$PY" - "$B6" <<'PYEOF'
import json, sys
from pathlib import Path
b6 = Path(sys.argv[1])
st = lambda n: json.loads((b6 / "qa" / "after" / "qa" / f"{n}.style.json").read_text())  # noqa: E731
txt = lambda r, role: [t["text"] for t in r["texts"] if t["role"] == role]  # noqa: E731
ir, xrd, t3, t4, h6 = (st(n) for n in ("01_IR", "02_XRD", "03_TPC_overlay", "04_TPC_overlay_logtime",
                                       "06_in_situ_PL_heatmap"))
rec = json.loads((b6 / "composite" / "shared_legend_span_183mm.json").read_text())
tf = json.loads((b6 / "qa" / "text_fit.json").read_text())["composites"]["shared_legend_span_183mm.tiff"]
sess = (b6 / "menu" / "menu_b6_session.txt").read_text()
cfgs = {p.stem: json.loads(p.read_text()) for p in (b6 / "configs").glob("*.json")}
hb = next(p for p in rec["panels"] if p["spec"] == "06_in_situ_PL_heatmap")["box_px"]
hid = xrd["layout"].get("tick_numbers_hidden", {}).get("y", {})
panel_legend_texts = [t for p in rec["panels"] if p["kind"] == "data"
                      for t in json.loads(Path(p["render"]["style_json"]).read_text())["texts"]
                      if t["role"] == "axes.legend"]
checks = {
    "XRD y label 'Intensity (a.u.)' from saved labels": txt(xrd, "axes.ylabel") == ["Intensity (a.u.)"]
        and cfgs["02_XRD"]["labels"]["ylabel"] == {"name": "Intensity", "unit": "a.u."},
    "XRD y tick numbers hidden, tick marks and label kept, offset hidden":
        not [t for t in xrd["texts"] if t["role"].startswith("axes.ytick")] and hid.get("tick_marks_visible", 0) > 0
        and hid.get("label_visible") is True and hid.get("offset_visible") is False and not txt(xrd, "axes.yoffset"),
    "TPC legends Control / Target (03 and 04)": txt(t3, "axes.legend") == ["Control", "Target"]
        and txt(t4, "axes.legend") == ["Control", "Target"],
    "04 log-time x upper limit 10^2 us": abs(max(t4["main_axes"]["xlim"]) - 100.0) < 1e-9,
    "01 x unit typed as Unicode cm-1 renders as mathtext with halfwidth hyphen":
        txt(ir, "axes.xlabel") == [r"Wavenumber (cm$^{\text{-1}}$)"],
    "06 heatmap x = Time (s) from the 1 s interval, first tick 0": txt(h6, "axes.xlabel") == ["Time (s)"]
        and txt(h6, "axes.xtick.major.label1")[0] == "0",
    "06 native-cell requirement uses the plotted time step": h6["native_requirement_px"]["smallest_step"]["x"] == 1.0,
    "composite: shared legend Control / Target from the panel handles": rec["legend"]["shared_legend"]
        and [t["text"] for t in rec["legend"]["texts"]] == ["Control", "Target"]
        and rec["legend"]["entries_source"] == "panel line handles",
    "composite: per-panel legends suppressed": not panel_legend_texts,
    "composite: no fully blank cell": rec["empty_cells"]["blank_cells_rc"] == [],
    "composite: heatmap box aspect 0.5-1.0": 0.5 <= hb[3] / hb[2] <= 1.0,
    "composite: y labels aligned per column": rec["checks"]["ylabels_aligned_per_column"],
    "composite: colour-bar label clearance > 0 mm, no collision": bool(tf["colorbar_label_clearance"])
        and all(not e["collision"] and e["axis_label"]["clearance_mm"] > 0 for e in tf["colorbar_label_clearance"]),
    "composite: text fit pass": tf["pass"],
    "menu: label-too-long WARNING": "WARNING: label too long: 07_in_situ_PL_mean_spectrum x label" in sess,
    "menu: shared-legend count and style WARNINGs": "WARNING: shared legend: 3 entries supplied" in sess
        and "linestyle dotted differs" in sess,
    "menu: saved composite.json reloaded": json.loads((b6 / "configs" / "composite.json").read_text())["composite"]
        == {"shared_legend": True, "spans": {"d": "row"}, "legend_cell": "2,2"} and "reloaded saved config" in sess,
    "menu: session ended": sess.rstrip().endswith("bye"),
}
for k, v in checks.items():
    print(f"{'PASS' if v else 'FAIL'} b6: {k}")
sys.exit(0 if all(checks.values()) else 1)
PYEOF
step "12. selectable palettes: synthetic nature-6c-2 test render, overflow, unknown id; --palette on the demo figures"
# Runs after every check above and writes only to its own subdirectories, so the
# bundled figures (no palette named) are unaffected.
"$PY" "$KIT/demo/test_palettes.py" --out "$OUT/palette_test" | grep -E "^(PASS|FAIL)|^PALETTE TEST"
"$PY" "$KIT/make_figures.py" --data "$DATA" --manifest "$MAN" --out "$OUT/palette_test/figures" --no-config \
      --palette nature-6c-2 --only 01_IR,04_TPC_overlay_logtime | grep -E "^(PALETTE|RENDER)"
"$PY" - "$OUT" <<'PYEOF'
import json, sys
from pathlib import Path
o = Path(sys.argv[1])
st = lambda d, n: json.loads((d / "qa" / f"{n}.style.json").read_text())  # noqa: E731
p4, p1 = st(o / "palette_test" / "figures", "04_TPC_overlay_logtime"), st(o / "palette_test" / "figures", "01_IR")
d4 = st(o, "04_TPC_overlay_logtime")
checks = {
    "--palette nature-6c-2: 04 records palette and its first two hex": p4.get("palette") == "nature-6c-2"
        and p4.get("palette_hex_used") == ["#3B549D", "#D3272B"],
    "--palette nature-6c-2: 01 single series takes the first colour": p1.get("palette_hex_used") == ["#3B549D"],
    "no palette named: demo 04 keeps #2166AC / #B35806 solid/dashed": "palette" not in d4
        and d4["evidence"]["colors"] == ["#2166AC", "#B35806"] and d4["evidence"]["line_styles"] == ["solid", "dashed"],
}
for k, v in checks.items():
    print(f"{'PASS' if v else 'FAIL'} palette: {k}")
sys.exit(0 if all(checks.values()) else 1)
PYEOF
echo "DEMO OK: outputs in $OUT"
