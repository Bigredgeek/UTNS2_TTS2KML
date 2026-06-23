"""UTNS2 TTS -> KML converter (single stitched Finland map).

Reads a Tabletop Simulator save (one continuous 4-tile board) plus the calibration
file ``tts2lola.json`` produced by ``calibrate.py``, and emits a single KML with
units grouped into Russia / Finland / Sweden / NATO / Neutral folders.

Design notes:
- Units already carry world ``posX/posZ`` so NO map-object lookup is needed.
- The board frame + 2D-quadratic transform live entirely in ``tts2lola.json``.
- A unit is kept only if it sits on one of the four map tiles (per-tile bounds),
  which drops off-board staging/reserve pieces.
"""

import argparse
import json
import os
import re

from lxml import etree
from pykml.factory import KML_ElementMaker as KML

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSFORM_FILE = os.path.join(SCRIPT_DIR, "tts2lola.json")

DEFAULT_ICON_SCALE = 3
NEUTRAL_ICON_SCALE = 2

# Faction folders in render order. Each entry: (folder name, routing tag).
# Routing is priority-ordered: the first tag a unit has wins, so a unit tagged
# both FIN and NATO lands in Finland, and a NATO-only unit lands in NATO.
FACTION_ORDER = [
    ("Russia", "RUS"),
    ("Finland", "FIN"),
    ("Sweden", "SWE"),
    ("NATO", "NATO"),
]

MAP_TILE_NICKNAMES = {"1", "2", "3", "4"}


class GeoReferencedMap:
    """Applies the board-frame + 2D-quadratic transform from tts2lola.json."""

    def __init__(self, transform_file=TRANSFORM_FILE):
        with open(transform_file) as handle:
            self.data = json.load(handle)
        self.frame = self.data["frame"]
        self.easting = self.data["easting"]
        self.northing = self.data["northing"]
        self.tiles = self.data["tiles"]
        self.margin = self.data.get("margin", 0.0)

    def on_board(self, transform):
        """True if the world position lies on any of the four map tiles."""
        pos_x = transform.get("posX")
        pos_z = transform.get("posZ")
        if pos_x is None or pos_z is None:
            return False
        for tile in self.tiles:
            half = tile["half"] + self.margin
            if abs(pos_x - tile["cx"]) <= half and abs(pos_z - tile["cz"]) <= half:
                return True
        return False

    def board_offset(self, transform):
        """World (posX, posZ) -> board-frame (x, y), keeping the z,x swap that
        undoes the tiles' rotY=270 orientation."""
        scale = self.frame["scale"]
        x = (transform["posZ"] - self.frame["originZ"]) / scale
        y = (transform["posX"] - self.frame["originX"]) / scale
        return (x, y)

    def to_lola(self, transform):
        """World transform -> (lon, lat), or None if the unit is off-board."""
        if not self.on_board(transform):
            return None
        x, y = self.board_offset(transform)
        lon = (
            self.easting["a"] * x ** 2 + self.easting["b"] * y ** 2
            + self.easting["c"] * x * y + self.easting["d"] * x
            + self.easting["e"] * y + self.easting["f"]
        )
        lat = (
            self.northing["a"] * x ** 2 + self.northing["b"] * y ** 2
            + self.northing["c"] * x * y + self.northing["d"] * x
            + self.northing["e"] * y + self.northing["f"]
        )
        return (lon, lat)


def to_kml_coord(point):
    return f"{point[0]},{point[1]}"


def to_kml_point(waypoint):
    return KML.Point(KML.coordinates(to_kml_coord(waypoint)))


def faction_for(tags):
    """Return the folder name for a unit's tags, or None to skip it."""
    if not tags:
        return None
    tag_set = {t for t in tags if isinstance(t, str)}
    for folder_name, tag in FACTION_ORDER:
        if tag in tag_set:
            return folder_name
    return "Neutral"


def has_hidden_tag(tags):
    """True if any tag is the 'HIDDEN' marker (case-insensitive)."""
    return any(isinstance(t, str) and t.strip().upper() == "HIDDEN" for t in (tags or []))


def icon_scale_for(tags):
    tag_set = {t for t in (tags or []) if isinstance(t, str)}
    if tag_set & {"NATO", "FIN", "SWE", "RUS"}:
        return DEFAULT_ICON_SCALE
    return NEUTRAL_ICON_SCALE


def create_kml_doc(mission_name, units):
    styles_by_id = {}
    placemarks = {name: [] for name, _ in FACTION_ORDER}
    placemarks["Neutral"] = []

    for obj, position in units:
        tags = obj.get("Tags")
        folder_name = faction_for(tags)
        if folder_name is None:
            continue

        custom_image = obj.get("CustomImage") or {}
        image_path = custom_image.get("ImageURL") or custom_image.get("ImageSecondaryURL") or ""
        raw_name = obj.get("Nickname") or ""
        name = raw_name.replace(" ", "")
        icon_scale = icon_scale_for(tags)

        existing = styles_by_id.get(name)
        if existing:
            if icon_scale < existing["scale"]:
                existing["scale"] = icon_scale
            if not existing["href"] and image_path:
                existing["href"] = image_path
        else:
            styles_by_id[name] = {"href": image_path, "scale": icon_scale}

        placemark = KML.Placemark(
            KML.name(name), KML.styleUrl(f"#{name}"), to_kml_point(position)
        )
        placemarks[folder_name].append(placemark)

    styles = [
        KML.Style(
            KML.IconStyle(
                KML.scale(data["scale"]),
                KML.Icon(KML.href(data["href"])),
            ),
            id=style_id,
        )
        for style_id, data in styles_by_id.items()
    ]

    folders = []
    for folder_name in [name for name, _ in FACTION_ORDER] + ["Neutral"]:
        marks = placemarks.get(folder_name) or []
        if marks:
            folders.append(KML.Folder(KML.name(folder_name), *marks))

    return KML.kml(KML.Document(KML.Name(mission_name), *styles, *folders))


def sanitize_save_name(save_name, fallback):
    """Build the output base name 'UTNS_<SaveName>' (sanitized for filenames)."""
    name = (save_name or "").strip()
    if not name:
        name = fallback
    # Drop characters invalid in Windows filenames, collapse whitespace to '_'.
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    if not name:
        name = fallback
    if not name.upper().startswith("UTNS"):
        name = f"UTNS_{name}"
    return name


def collect_units(data, crs, hide_russia=False, hide_hidden=False):
    units = []
    for obj in data.get("ObjectStates", []):
        if obj.get("Name") not in ("Custom_Tile", "Custom_Token"):
            continue
        if obj.get("Nickname") in MAP_TILE_NICKNAMES:
            continue  # the four map tiles themselves
        tags = obj.get("Tags")
        if not tags:
            continue
        if hide_hidden and has_hidden_tag(tags):
            continue
        if hide_russia and faction_for(tags) == "Russia":
            continue
        pos = crs.to_lola(obj.get("Transform", {}))
        if not pos:
            continue
        units.append((obj, pos))
    return units


def main():
    parser = argparse.ArgumentParser(
        description="Convert a TTS save into a stitched Finland KML map."
    )
    parser.add_argument(
        "path", nargs="?", default="SampleScenario.json",
        help="TTS save file to convert (default: SampleScenario.json).",
    )
    parser.add_argument(
        "--hide-russia", action="store_true",
        help="Exclude units routed to the Russia folder.",
    )
    parser.add_argument(
        "--hide-hidden", action="store_true",
        help="Exclude units tagged 'HIDDEN'.",
    )
    args = parser.parse_args()
    path = args.path

    crs = GeoReferencedMap()
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    units = collect_units(
        data, crs, hide_russia=args.hide_russia, hide_hidden=args.hide_hidden
    )

    fallback = os.path.splitext(os.path.basename(path))[0]
    base_name = sanitize_save_name(data.get("SaveName"), fallback)
    suffix = "_BLUEVIEW" if (args.hide_russia or args.hide_hidden) else "_ALL"
    base_name = f"{base_name}{suffix}"
    output_file = f"{base_name}.kml"

    doc = create_kml_doc(base_name, units)
    xml_bytes = etree.tostring(doc, pretty_print=True, encoding="utf-8")
    with open(output_file, "wb") as out:
        out.write(xml_bytes.rstrip(b"\r\n\t "))

    print(f"Wrote {output_file} ({len(units)} on-board units)")


if __name__ == "__main__":
    main()
