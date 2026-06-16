"""UTNS2 calibration: image-derived GCPs -> tts2lola.json.

The four map tiles carry no coordinate graticule, so we georeference using towns
as Ground Control Points (GCPs):

  pixel (in a tile image)  --[analytic tile geometry]-->  TTS world coord
  town name                --[towns.lua lookup]-------->  real lon/lat

Both links are combined to fit a board-frame -> lon/lat transform, written to
``tts2lola.json`` for ``tts2kml.py`` to consume. The model is affine or
2D-quadratic (selected by ``model`` in town_gcps.json; ``auto`` uses affine until
there are enough GCPs to validate a quadratic). Both are emitted as the same six
coefficients (the affine model leaves the quadratic terms at zero), and the fit
is reported with per-GCP residuals plus a leave-one-out generalisation estimate.

Input: ``town_gcps.json`` (tile geometry, image orientation, and the list of
{town, tile, px, py} control points). Re-calibrating means editing that JSON and
re-running this script - no code changes required.
"""

import json
import os

import numpy as np
from lupa.lua54 import LuaRuntime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOWNS_FILE = os.path.join(SCRIPT_DIR, "towns.lua")
GCP_FILE = os.path.join(SCRIPT_DIR, "town_gcps.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "tts2lola.json")

# Coefficient count per axis for each model.
AFFINE_PARAMS = 3      # [x, y, 1]
QUADRATIC_PARAMS = 6   # [x^2, y^2, x*y, x, y, 1]
# Use a quadratic only when there are enough GCPs to leave real degrees of
# freedom for validation; otherwise a quadratic just overfits sparse points.
AUTO_QUADRATIC_MIN_GCPS = 10


def load_towns():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().loadfile(TOWNS_FILE)()
    return lua.globals()["towns"]


def town_lonlat(towns, name):
    town = towns[name]
    if town is None:
        return None
    return (town["longitude"], town["latitude"])


def pixel_to_world(px, py, tile, tile_size_px, orientation):
    """Map a pixel within a tile image to a TTS world (posX, posZ).

    orientation maps image axes (u = px right, v = py down) to world axes. The
    default (validated against the Gulf of Bothnia = west, Russia = east) is:
    +u -> -Z, +v -> -X (map drawn north-up, tiles placed at rotY=270).
    """
    u = px / tile_size_px
    v = py / tile_size_px
    if orientation.get("swap_uv"):
        u, v = v, u
    du = u - 0.5
    dv = v - 0.5
    full = 2.0 * tile["half"]

    offsets = {"X": 0.0, "Z": 0.0}
    offsets[orientation["u_axis"]] = orientation["u_sign"] * du * full
    offsets[orientation["v_axis"]] = orientation["v_sign"] * dv * full
    return (tile["cx"] + offsets["X"], tile["cz"] + offsets["Z"])


def board_offset(pos_x, pos_z, origin_x, origin_z, scale):
    """World -> board-frame (x, y) with the z,x swap that undoes rotY=270."""
    return ((pos_z - origin_z) / scale, (pos_x - origin_x) / scale)


def design_row(x, y, model):
    """Design-matrix row. Both models emit 6 columns ordered
    [x^2, y^2, x*y, x, y, 1] so the output coefficients always map onto the
    (a, b, c, d, e, f) consumed by tts2kml.py; the affine model simply leaves
    the three quadratic columns at zero."""
    if model == "affine":
        return [0.0, 0.0, 0.0, x, y, 1.0]
    return [x ** 2, y ** 2, x * y, x, y, 1.0]


def active_columns(model):
    """Indices of design columns actually fitted for the given model."""
    if model == "affine":
        return [3, 4, 5]
    return [0, 1, 2, 3, 4, 5]


def fit(rows, targets, model):
    """Least-squares fit over only the active columns; returns 6 coefficients
    (inactive columns set to 0)."""
    cols = active_columns(model)
    matrix = np.array(rows, dtype=float)[:, cols]
    vector = np.array(targets, dtype=float)
    solution, *_ = np.linalg.lstsq(matrix, vector, rcond=None)
    coeffs = np.zeros(6, dtype=float)
    for idx, value in zip(cols, solution):
        coeffs[idx] = value
    return coeffs


def predict(coeffs, row):
    return float(np.dot(coeffs, row))


def km_error(pred_lon, pred_lat, lon, lat):
    dlon = pred_lon - lon
    dlat = pred_lat - lat
    return float(np.hypot(dlat * 111.0, dlon * 111.0 * np.cos(np.radians(lat))))


def leave_one_out_rms(rows, lons, lats, model):
    """Refit with each GCP removed and measure that point's predicted error;
    a robust generalisation estimate for sparse control points."""
    n = len(rows)
    min_needed = len(active_columns(model)) + 1
    if n < min_needed + 1:
        return None
    errors = []
    for i in range(n):
        keep = [j for j in range(n) if j != i]
        sub_rows = [rows[j] for j in keep]
        east = fit(sub_rows, [lons[j] for j in keep], model)
        north = fit(sub_rows, [lats[j] for j in keep], model)
        errors.append(
            km_error(predict(east, rows[i]), predict(north, rows[i]), lons[i], lats[i])
        )
    return float(np.sqrt(np.mean(np.square(errors))))


def coeffs_to_dict(coeffs):
    keys = ("a", "b", "c", "d", "e", "f")
    return {k: float(v) for k, v in zip(keys, coeffs)}


def choose_model(requested, n_gcps):
    requested = (requested or "auto").lower()
    if requested == "affine":
        return "affine"
    if requested == "quadratic":
        return "quadratic"
    # auto
    return "quadratic" if n_gcps >= AUTO_QUADRATIC_MIN_GCPS else "affine"


def main():
    with open(GCP_FILE, encoding="utf-8") as handle:
        gcp_data = json.load(handle)

    tile_size_px = gcp_data["tile_size_px"]
    tiles = gcp_data["tiles"]  # {"1": {"cx":..,"cz":..,"half":..}, ...}
    orientation = gcp_data["orientation"]
    gcps = gcp_data.get("gcps", [])
    requested_model = gcp_data.get("model", "auto")

    towns = load_towns()

    # Board frame: origin at mean tile center, scale = tile half-extent.
    origin_x = sum(t["cx"] for t in tiles.values()) / len(tiles)
    origin_z = sum(t["cz"] for t in tiles.values()) / len(tiles)
    scale = next(iter(tiles.values()))["half"]

    rows, lons, lats, labels = [], [], [], []
    skipped = []
    for gcp in gcps:
        name = gcp["town"]
        lonlat = town_lonlat(towns, name)
        if lonlat is None:
            skipped.append(name)
            continue
        tile = tiles[str(gcp["tile"])]
        pos_x, pos_z = pixel_to_world(
            gcp["px"], gcp["py"], tile, tile_size_px, orientation
        )
        x, y = board_offset(pos_x, pos_z, origin_x, origin_z, scale)
        rows.append(design_row(x, y, "quadratic"))  # full 6-col row; fit() slices
        lons.append(lonlat[0])
        lats.append(lonlat[1])
        labels.append(name)

    if skipped:
        print(f"WARNING: {len(skipped)} GCP town(s) not in towns.lua: {skipped}")

    n = len(rows)
    model = choose_model(requested_model, n)
    min_gcps = len(active_columns(model))
    if n < min_gcps:
        raise SystemExit(
            f"Only {n} usable GCPs after towns.lua lookup; the {model} model needs "
            f"at least {min_gcps}. Add more towns to {GCP_FILE}."
        )

    easting = fit(rows, lons, model)
    northing = fit(rows, lats, model)

    # Residual report (degrees + rough km; 1 deg lat ~ 111 km).
    print(f"Model: {model} (requested '{requested_model}', {n} GCPs)")
    print("Per-GCP fit residuals:")
    max_km = 0.0
    sq = []
    for row, lon, lat, label in zip(rows, lons, lats, labels):
        pred_lon = predict(easting, row)
        pred_lat = predict(northing, row)
        km = km_error(pred_lon, pred_lat, lon, lat)
        sq.append(km * km)
        max_km = max(max_km, km)
        print(
            f"  {label:<16} dlon={pred_lon - lon:+.4f} dlat={pred_lat - lat:+.4f}"
            f"  (~{km:.1f} km)"
        )
    rms_km = float(np.sqrt(np.mean(sq)))
    print(f"Fit RMS: ~{rms_km:.1f} km   Max: ~{max_km:.1f} km")
    loo = leave_one_out_rms(rows, lons, lats, model)
    if loo is not None:
        print(f"Leave-one-out RMS (generalisation): ~{loo:.1f} km")

    output = {
        "model": model,
        "frame": {
            "originX": origin_x,
            "originZ": origin_z,
            "scale": scale,
        },
        "easting": coeffs_to_dict(easting),
        "northing": coeffs_to_dict(northing),
        "tiles": [
            {"cx": t["cx"], "cz": t["cz"], "half": t["half"]}
            for t in tiles.values()
        ],
        "margin": gcp_data.get("margin", 0.0),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(output, out, indent=4)
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
