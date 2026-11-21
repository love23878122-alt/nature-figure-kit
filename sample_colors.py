"""Same sample name, same colour: run-wide name -> colour/linestyle resolution.

Pure logic, no plotting. Used by plot_figures.series_style (single figures and
make_figures.py batches), make_composite.py (all data panels of a composite)
and figmenu.py (key ``n`` at the main menu).

    import sample_colors as sc
    doc = sc.load_map(path)            # {"pins": {...}, "order": [...]} (validated)
    table, warns = sc.resolve(["MeO-2PACz", "2PACz"], "nature-6c-2",
                              pins=doc["pins"], order=doc["order"])
    table["MeO-2PACz"]  # {"color": "#3B549D", "linestyle": None, "source": "palette", ...}

Names
    A series name is its legend label after config overrides (for 03/04 the
    ``legend.labels`` text). Matching is exact after stripping surrounding
    whitespace; there is no case folding ("2PACz" and "2pacz" are different
    names). Series without a legend label (01, 02, 07, 10) have no name and keep
    the position-based colouring.

When it is active
    Name-based colouring applies when a palette is named (figure "palette" key
    or --palette) or the pins give a colour for a name. With no palette and no
    pins nothing changes: the spec colours and linestyles are used by position.
    With pins and no palette, pinned names take their pin; unpinned names keep
    their spec colour by position (``source: "spec"``, colour filled in by the
    figure).

Assignment rule (deterministic)
    1. Pinned names take their pinned colour.
    2. Then names listed in the shared map's ``order`` list (if any), then every
       other name in first-appearance order, each get the next palette colour
       that is not already taken by a pin (pinned colours are not reused for
       other names while unused palette colours remain). Names in ``order``
       keep their slot even when the current figure does not show them, so a
       saved order reproduces the same colours in every later run.
    3. First appearance: for a composite, panels in panel order, and inside a
       panel the series/legend order; for a make_figures.py batch, figures in
       FIGURE_NAMES order, then series order. All names are collected before
       any colour is assigned, so one name has one colour across the run.

Linestyles and overflow
    While the distinct unpinned names (run names plus ``order`` names) fit into
    the available palette colours (palette length minus the palette colours
    taken by pins), ``linestyle`` is None: the figure keeps its own spec
    linestyle by position (03/04 solid/dashed). Beyond that the colours cycle
    over the available colours and the linestyle advances once per cycle,
    per name (solid -> dashed -> dotted -> dashdot); pinned names are solid.
    One WARNING is returned. Two pins with the same colour also give a WARNING.
    Nothing raises for overflow.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import palettes

FILENAME = "sample_colors.json"
MAP_KEYS = ("pins", "order")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
LINESTYLES = palettes.OVERFLOW_LINESTYLES


class SampleColorError(ValueError):
    pass


def clean_name(name):
    """Exact-match key: surrounding whitespace stripped, nothing else changed."""
    if not isinstance(name, str):
        raise SampleColorError(f"sample name must be text, got {name!r}")
    key = name.strip()
    if not key:
        raise SampleColorError("sample name must not be empty")
    return key


def normalize_hex(value, what="colour"):
    if not isinstance(value, str) or not HEX_RE.match(value.strip()):
        raise SampleColorError(f"{what} {value!r} is not a #RRGGBB hex colour")
    return value.strip().upper()


def validate_map(doc):
    """Validated copy {"pins": {name: "#RRGGBB"}, "order": [name, ...]}; unknown keys are rejected."""
    if doc is None:
        return {"pins": {}, "order": []}
    if not isinstance(doc, dict):
        raise SampleColorError('sample colour map must be a JSON object {"pins": {...}, "order": [...]}')
    extra = set(doc) - set(MAP_KEYS)
    if extra:
        raise SampleColorError(f"unknown sample colour key(s) {', '.join(sorted(extra))} "
                               f"(allowed: {', '.join(MAP_KEYS)})")
    pins_in = doc.get("pins") or {}
    order_in = doc.get("order") or []
    if not isinstance(pins_in, dict):
        raise SampleColorError('"pins" must be an object {"name": "#RRGGBB"}')
    if not isinstance(order_in, list):
        raise SampleColorError('"order" must be a list of names')
    pins = {}
    for k, v in pins_in.items():
        key = clean_name(k)
        if key in pins:
            raise SampleColorError(f"name {key!r} is pinned twice")
        pins[key] = normalize_hex(v, f"pin for {key!r}")
    order = []
    for n in order_in:
        key = clean_name(n)
        if key not in order:
            order.append(key)
    return {"pins": pins, "order": order}


def map_path(config_dir):
    return Path(config_dir) / FILENAME


def load_map(path):
    """Validated map from ``path``; a missing file is an empty map."""
    p = Path(path)
    if not p.exists():
        return {"pins": {}, "order": []}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SampleColorError(f"{p}: not valid JSON ({exc})") from exc
    try:
        return validate_map(doc)
    except SampleColorError as exc:
        raise SampleColorError(f"{p}: {exc}") from exc


def save_map(path, doc):
    """Write the validated map (hex uppercase) and return the path."""
    clean = validate_map(doc)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def merged_order(existing_order, resolved_order):
    """Saved ``order``: the existing list, then the run's names that are not in it yet."""
    out = [clean_name(n) for n in existing_order or []]
    for n in resolved_order:
        if n not in out:
            out.append(n)
    return out


def first_appearance(groups):
    """Distinct cleaned names from an iterable of name lists, in first-appearance order."""
    seen = []
    for group in groups:
        for n in group or []:
            key = clean_name(n)
            if key not in seen:
                seen.append(key)
    return seen


def is_active(palette, pins):
    return bool(palette) or bool(pins)


def resolve(names_in_order, palette, pins=None, order=None):
    """Resolve the name table for one run.

    ``names_in_order``: all names of the run in first-appearance order
    (duplicates are ignored). ``palette``: palette id or None. Returns
    ``(table, warnings)``; ``table`` maps each run name to
    ``{"color", "linestyle", "source", "slot"}`` where ``source`` is "pin",
    "palette" or "spec" (no palette: the figure fills the spec colour by
    position, ``color`` None). ``linestyle`` is None while the palette fits
    (the figure's own linestyle applies), else a name from LINESTYLES.
    """
    pins = validate_map({"pins": pins or {}})["pins"]
    order = validate_map({"order": order or []})["order"]
    names = first_appearance([names_in_order])
    warns = []
    by_colour = {}
    for n, c in pins.items():
        by_colour.setdefault(c, []).append(n)
    for c, ns in by_colour.items():
        if len(ns) > 1:
            warns.append(f"WARNING: sample colours: pins {', '.join(ns)} share the colour {c}")
    table = {}
    for n in names:
        if n in pins:
            table[n] = {"color": pins[n], "linestyle": None, "source": "pin", "slot": None}
    if not palette:
        for n in names:
            if n not in pins:
                table[n] = {"color": None, "linestyle": None, "source": "spec", "slot": None}
        return table, warns
    hexes = palettes.get_palette(palette)
    taken = set(pins.values())
    avail = [c for c in hexes if c not in taken]
    cycle_offset = 0
    if not avail:      # every palette colour is pinned: cycle the full palette, starting dashed
        avail, cycle_offset = list(hexes), 1
    # Assignment sequence: order-list names (slots kept even if absent), then the rest.
    sequence = [n for n in order if n not in pins]
    sequence += [n for n in names if n not in pins and n not in sequence]
    k = len(avail)
    overflow = len(sequence) > k or cycle_offset > 0
    if overflow:
        cycles = -(-len(sequence) // k) + cycle_offset
        used = [LINESTYLES[i % len(LINESTYLES)] for i in range(cycle_offset, cycles)]
        warns.append(f"WARNING: sample colours: {len(sequence)} distinct unpinned names but palette {palette} "
                     f"has {k} available colour(s) ({len(hexes)} minus {len(hexes) - k if not cycle_offset else len(hexes)} "
                     f"taken by pins); colours cycle and the linestyle advances per cycle per name "
                     f"({' -> '.join(used)})")
    for i, n in enumerate(sequence):
        if n not in names:
            continue
        style = LINESTYLES[(i // k + cycle_offset) % len(LINESTYLES)] if overflow else None
        table[n] = {"color": avail[i % k], "linestyle": style, "source": "palette", "slot": i}
    if overflow:
        for n in names:
            if table[n]["source"] == "pin":
                table[n]["linestyle"] = "solid"
    # Report in first-appearance order.
    return {n: table[n] for n in names}, warns


def resolution_record(palette, names, table, warns, pins, order, map_file=None):
    """JSON-ready record of one resolution (written to the style/evidence JSON)."""
    return {"active": is_active(palette, pins), "palette": palette, "names_in_order": list(names),
            "pins": dict(pins or {}), "order": list(order or []), "map_file": str(map_file) if map_file else None,
            "table": {n: dict(v) for n, v in table.items()}, "warnings": list(warns),
            "match_rule": "exact after stripping surrounding whitespace; no case folding"}


def describe_table(table):
    lines = []
    for n, e in table.items():
        c = e["color"] or "spec colour by position"
        ls = e["linestyle"] or "figure linestyle"
        lines.append(f"{n} = {c} ({ls}; {e['source']})")
    return lines


def cli_map(explicit=None, config_dir=None, no_config=False):
    """Map for a CLI run: ``(doc, read_path_or_None, save_path)``.

    ``--sample-colors FILE`` wins (read when it exists, always the save target);
    else ``<config-dir>/sample_colors.json`` is read automatically when it exists,
    unless ``--no-config``. ``config_dir`` must already be resolved
    (figure_config.config_dir).
    """
    if explicit:
        p = Path(explicit)
        return load_map(p), (p if p.exists() else None), p
    p = map_path(config_dir)
    if not no_config and p.exists():
        return load_map(p), p, p
    return validate_map(None), None, p


def save_order(path, resolved_names):
    """Append the run's names to the saved ``order`` (pins untouched); returns (path, order)."""
    doc = load_map(path)
    doc["order"] = merged_order(doc["order"], resolved_names)
    return save_map(path, doc), doc["order"]
