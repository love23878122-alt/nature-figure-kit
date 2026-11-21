"""Selectable discrete series palettes (36 Nature palettes + okabe-ito).

    import palettes
    palettes.list_palettes()                 # ['okabe-ito', 'nature-3c-1', ...]
    palettes.get_palette("nature-6c-2")      # ['#3B549D', '#D3272B', ...]
    palettes.assign_series(8, "nature-6c-2") # colours + linestyles for 8 series

The catalog is ``palettes/nature_palettes.json`` next to this module. Palettes
are for discrete series (lines); heatmaps and colour bars keep their colormaps.

Overflow: when more series are requested than the palette holds, the colours
cycle and the linestyle advances once per full cycle (solid -> dashed -> dotted
-> dashdot, then repeat). A ``PaletteOverflowWarning`` is emitted (Python
warning, printed to stderr) and the result carries a ``warning`` string so the
caller can record it in the evidence / style JSON. Nothing crashes.

``python palettes.py`` lists every id with n and hex values.
"""
from __future__ import annotations

import json
import sys
import warnings
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "palettes" / "nature_palettes.json"
OVERFLOW_LINESTYLES = ("solid", "dashed", "dotted", "dashdot")
MPL_LINESTYLE = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
# Used only internally when code needs a named-palette assignment and none was
# named; the bundled figures keep their spec colours when no palette is named.
_FALLBACK = "okabe-ito"


class PaletteError(ValueError):
    pass


class PaletteOverflowWarning(UserWarning):
    pass


@lru_cache(maxsize=1)
def _catalog():
    doc = json.loads(CATALOG.read_text(encoding="utf-8"))
    return doc["source"], {p["id"]: p for p in doc["palettes"]}


def source_note():
    return dict(_catalog()[0])


def list_palettes():
    """All palette ids in catalog order."""
    return list(_catalog()[1])


def palette_info(name):
    """{'id', 'n', 'hex', ...} for ``name`` (validated)."""
    return dict(_catalog()[1][validate_name(name)])


def validate_name(name):
    """Return ``name`` if it is a known id, else raise PaletteError with the valid ids."""
    table = _catalog()[1]
    if isinstance(name, str) and name.strip() in table:
        return name.strip()
    ids = list(table)
    raise PaletteError(f"unknown palette {name!r}; valid ids: {ids[0]}, {', '.join(ids[1:5])}, ... "
                       f"{ids[-1]} ({len(ids)} in total; run 'python palettes.py' for the full list)")


def get_palette(name):
    """Hex colours (uppercase #RRGGBB, catalog order) of palette ``name``."""
    return list(_catalog()[1][validate_name(name)]["hex"])


def assign_series(n, name, linestyles=None, warn=True):
    """Colours and linestyles for ``n`` series from palette ``name``.

    ``linestyles`` (optional, one per series, names from OVERFLOW_LINESTYLES)
    is the caller's own linestyle choice while the palette fits; otherwise
    every series is solid. When ``n`` exceeds the palette length the colours
    cycle and series ``i`` takes OVERFLOW_LINESTYLES[(i // len) % 4], and a
    PaletteOverflowWarning is emitted. Returns a dict with ``palette``,
    ``colors``, ``linestyles`` (names), ``mpl_linestyles``, ``overflow`` and
    ``warning`` (None when it fits).
    """
    if name is None:
        raise PaletteError("assign_series needs a palette name (see list_palettes())")
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise PaletteError(f"series count must be a non-negative integer, got {n!r}")
    hexes = get_palette(name)
    k = len(hexes)
    colors = [hexes[i % k] for i in range(n)]
    overflow = n > k
    message = None
    if overflow:
        styles = [OVERFLOW_LINESTYLES[(i // k) % len(OVERFLOW_LINESTYLES)] for i in range(n)]
        message = (f"WARNING: palette {name} has {k} colours but {n} series were requested; "
                   f"colours cycle and the linestyle advances per cycle "
                   f"({' -> '.join(OVERFLOW_LINESTYLES[:min(len(OVERFLOW_LINESTYLES), -(-n // k))])})")
        if warn:
            warnings.warn(message, PaletteOverflowWarning, stacklevel=2)
            print(message, file=sys.stderr, flush=True)
    elif linestyles is not None:
        styles = [MPL_TO_NAME.get(s, s) for s in linestyles]
        if len(styles) != n or any(s not in OVERFLOW_LINESTYLES for s in styles):
            raise PaletteError(f"linestyles must be {n} of {', '.join(OVERFLOW_LINESTYLES)}")
    else:
        styles = ["solid"] * n
    return {"palette": validate_name(name), "palette_hex": hexes, "n_series": n, "colors": colors,
            "linestyles": styles, "mpl_linestyles": [MPL_LINESTYLE[s] for s in styles],
            "overflow": overflow, "warning": message}


MPL_TO_NAME = {v: k for k, v in MPL_LINESTYLE.items()}


def fallback_assignment(n, name=None, linestyles=None):
    """assign_series with the internal fallback when ``name`` is None (no crash on unnamed paths)."""
    return assign_series(n, name or _FALLBACK, linestyles=linestyles)


def describe(name):
    p = palette_info(name)
    return f"{p['id']} (n={p['n']}): {' '.join(p['hex'])}"


def main(argv=None):
    src = source_note()
    print(f"Source: {src['title']} - {src['url']} ({src['note']})")
    for pid in list_palettes():
        print(describe(pid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
