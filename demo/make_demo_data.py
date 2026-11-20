"""Generate the SYNTHETIC demo dataset for the kit (no measured data).

    python demo/make_demo_data.py [--out demo/data] [--seed 20261120]

Every value is computed here with NumPy from a fixed seed. This script reads
no input files. It never opens a project data directory and never copies,
samples or downsamples measurements. The six files use the same formats that
plot_figures.py loads:

* IR.csv            two header rows, then wavenumber (cm-1, descending), %T.
                    Sloped baseline with Lorentzian absorption bands plus noise.
* XRD.xls           BIFF2 worksheet (read with xlrd), no header, two numeric
                    columns: 2theta (deg), intensity. Pseudo-Voigt peaks on a
                    decaying background with Poisson noise.
* TPC 1.txt, TPC 2.txt
                    '#' comment lines, then whitespace-delimited time (us,
                    strictly positive, log spaced) and normalized current.
                    Bi-exponential decays plus a weak tail and noise.
* PL_Image_Data.CSV 221 x 221 comma-separated map: smooth grain-like blobs,
                    a gentle gradient and pixel noise.
* in situ PL.xlsx   sheet 1: five header rows (integration time, averages,
                    column titles, numeric timestamps in row index 3, date/time
                    in row index 4), then 386 ascending wavelengths in column 0
                    and 100 scans of counts. A Gaussian PL peak that drifts to
                    longer wavelength and grows over the scans, a weaker
                    decaying side peak, a baseline and noise. Sheet 2 is empty.

Writes demo/data_manifest.json with the SHA-256 of every file, "synthetic": true,
the generator path and the seed.
"""
import argparse
import hashlib
import json
import struct
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20261120
GENERATOR = "demo/make_demo_data.py"
PL_SIDE = 221
N_WAVELENGTHS, N_SCANS = 386, 100


# ------------------------------------------------------------------ helpers

def lorentz(x, x0, w):
    return 1.0 / (1.0 + ((x - x0) / (w / 2.0)) ** 2)


def gauss(x, x0, fwhm):
    return np.exp(-4.0 * np.log(2.0) * ((x - x0) / fwhm) ** 2)


def write_biff2(path, rows):
    """Minimal BIFF2 worksheet with NUMBER cells only (xlrd reads it natively)."""
    rows = np.asarray(rows, dtype=float)
    nrow, ncol = rows.shape
    out = bytearray()

    def rec(code, payload):
        out.extend(struct.pack("<HH", code, len(payload)) + payload)

    rec(0x0009, struct.pack("<HH", 0x0002, 0x0010))               # BOF, worksheet
    rec(0x0000, struct.pack("<HHHH", 0, nrow, 0, ncol))           # DIMENSIONS
    for r in range(nrow):
        for c in range(ncol):
            rec(0x0003, struct.pack("<HH3sd", r, c, b"\x00\x00\x00", float(rows[r, c])))  # NUMBER
    rec(0x000A, b"")                                              # EOF
    Path(path).write_bytes(bytes(out))


# --------------------------------------------------------------- generators

def make_ir(rng, path):
    wn = np.linspace(3996.4, 401.8, 1865)                          # ~1.93 cm-1 spacing
    base = 96.0 - 2.5 * (4000.0 - wn) / 3600.0
    bands = [(3380, 260, 16), (2955, 30, 5), (2922, 28, 9), (2852, 24, 6), (1728, 34, 31),
             (1635, 40, 9), (1458, 26, 11), (1377, 20, 6), (1240, 38, 18), (1102, 52, 38),
             (1028, 30, 14), (842, 22, 8), (722, 14, 6), (610, 40, 10)]
    absorb = sum(depth * lorentz(wn, x0, w) for x0, w, depth in bands)
    t = base - absorb + rng.normal(0.0, 0.12, wn.size)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"Synthetic demo IR spectrum - no measured data - {GENERATOR} seed {SEED}\n")
        f.write("cm-1,%T\n")
        for x, y in zip(wn, t):
            f.write(f"{x:.2f},{y:.2f}\n")


def make_xrd(rng, path):
    tt = np.round(np.arange(10.0, 70.0 + 1e-9, 0.02), 4)          # 3001 points
    peaks = [(14.12, 0.14, 15200), (20.03, 0.15, 3100), (24.51, 0.16, 5200), (28.44, 0.16, 11800),
             (31.88, 0.17, 6900), (35.03, 0.18, 2400), (40.62, 0.19, 4100), (43.21, 0.20, 3300),
             (50.07, 0.22, 1800), (58.36, 0.24, 1200)]
    eta = 0.45                                                     # pseudo-Voigt mixing
    signal = sum(h * (eta * lorentz(tt, x0, w) + (1 - eta) * gauss(tt, x0, w)) for x0, w, h in peaks)
    background = 420.0 * np.exp(-(tt - 10.0) / 18.0) + 160.0
    counts = rng.poisson(signal + background).astype(float)
    write_biff2(path, np.column_stack([tt, counts]))


def make_tpc(rng, path, taus, weights, scale, noise, label):
    t = np.logspace(-1.0, np.log10(15000.0), 900)                  # us, strictly positive
    y = sum(w * np.exp(-t / tau) for w, tau in zip(weights, taus))
    y = y + 0.012 * (1.0 + t / 3.0) ** -0.8                        # weak long tail
    y = scale * y / y[0] + rng.normal(0.0, noise, t.size)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# ----------------------------------------------------------\n")
        f.write(f"# Synthetic transient photocurrent ({label}) - no measured data\n")
        f.write(f"# Generated by {GENERATOR}, seed {SEED}\n")
        f.write("# Columns: Time (us)   Normalized Current (1)\n")
        f.write("# ----------------------------------------------------------\n")
        for a, b in zip(t, y):
            f.write(f"{a:.6E}\t{b:.6E}\n")


def make_pl_image(rng, path):
    n = PL_SIDE
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = 9.0 + 2.0 * (xx + yy) / (2 * n)                          # gentle gradient
    for _ in range(140):                                           # grain-like blobs
        cx, cy = rng.uniform(0, n, 2)
        r = rng.uniform(4.0, 14.0)
        img += rng.uniform(1.0, 6.0) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
    img += rng.normal(0.0, 0.35, img.shape)
    np.savetxt(path, img, delimiter=",", fmt="%.5g")


def make_in_situ(rng, path):
    from openpyxl import Workbook

    wl = np.linspace(300.0, 1150.0, N_WAVELENGTHS)                 # ascending, nm
    s = np.arange(N_SCANS) / (N_SCANS - 1)
    center = 752.0 + 34.0 * (1.0 - np.exp(-s / 0.35))              # red shift over time
    amp = 25.0 + 115.0 * (1.0 - np.exp(-s / 0.25)) - 18.0 * s
    side = 22.0 * np.exp(-s / 0.3)
    baseline = 32.0 + 0.008 * (wl - 300.0)
    counts = (baseline[:, None]
              + amp[None, :] * gauss(wl[:, None], center[None, :], 48.0 + 10.0 * s[None, :])
              + side[None, :] * gauss(wl[:, None], 528.0, 36.0)
              + rng.normal(0.0, 2.5, (N_WAVELENGTHS, N_SCANS)))
    timestamps = np.cumsum(np.r_[0, rng.integers(980, 1021, N_SCANS - 1)])   # ms
    t0 = datetime(2026, 1, 1, 9, 0, 0)
    stamps = [(t0 + timedelta(milliseconds=int(v))).strftime("%Y-%m-%d %H:%M:%S") for v in timestamps]

    wb = Workbook()
    ws = wb.active
    ws.title = "Synthetic"
    ws.append(["Integration Time [msec]"] + [100] * N_SCANS)
    ws.append(["Number of Averages"] + [1] * N_SCANS)
    ws.append(["Wavelength [nm]"] + ["Counts"] * N_SCANS)
    ws.append(["Timestamp"] + [int(v) for v in timestamps])
    ws.append(["Date/Time"] + stamps)
    for w, row in zip(wl, counts):
        ws.append([round(float(w), 4)] + [round(float(v), 4) for v in row])
    wb.create_sheet("Sheet2")                                      # empty second sheet
    fixed = datetime(2026, 1, 1)
    wb.properties.creator = "make_demo_data.py (synthetic)"
    wb.properties.created = wb.properties.modified = fixed
    wb.save(path)
    _normalize_zip(path)


def _normalize_zip(path):
    """Rewrite the xlsx zip with fixed entry times and core dates (byte-reproducible)."""
    import re
    import zipfile

    with zipfile.ZipFile(path) as z:
        entries = [(i.filename, z.read(i.filename)) for i in z.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            if name == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(created|modified)[^>]*>)[^<]*", rb"\g<1>2026-01-01T00:00:00Z", data)
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "data", help="output directory (default demo/data)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--manifest", type=Path, default=None,
                    help="manifest path (default: data_manifest.json next to --out)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    make_ir(rng, a.out / "IR.csv")
    make_xrd(rng, a.out / "XRD.xls")
    make_tpc(rng, a.out / "TPC 1.txt", (0.42, 1.55), (0.78, 0.22), 1.0, 0.004, "sample A")
    make_tpc(rng, a.out / "TPC 2.txt", (0.61, 2.30), (0.70, 0.30), 0.97, 0.005, "sample B")
    make_pl_image(rng, a.out / "PL_Image_Data.CSV")
    make_in_situ(rng, a.out / "in situ PL.xlsx")
    names = ["IR.csv", "PL_Image_Data.CSV", "TPC 1.txt", "TPC 2.txt", "XRD.xls", "in situ PL.xlsx"]
    digests = {n: hashlib.sha256((a.out / n).read_bytes()).hexdigest() for n in names}
    manifest = {"source_sha256": digests, "synthetic": True, "generator": GENERATOR, "seed": a.seed,
                "note": "All demo data are synthetic, generated by demo/make_demo_data.py; no measured data."}
    path = a.manifest or (a.out.parent / "data_manifest.json")
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
