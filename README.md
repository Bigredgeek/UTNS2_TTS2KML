# UTNS2_TTS2KML

A utility to convert a Tabletop Simulator (TTS) save file from the **UTNS: Uprising**
campaign (Red Strike wargame, Finland / Russian-border theatre) into a single KML map
file for Google Earth / web maps. The board is one continuous map stitched from four
tile images, and all units are exported into a single KML grouped by faction.

## Credits

This project is built upon the original TTS2KML scripts created by Gronank. The
coordinate-transformation system and KML generation logic were originally developed by
Gronank. This fork adapts that work to the UTNS: Uprising map: it collapses the old
three-layer (Tac/Strat/Op) pipeline into a single stitched four-tile map, georeferences
the board from town control points read off the tile imagery, and re-groups units into
Finland / Sweden / Russia / NATO folders.

Original repository by Gronank:
- [AnalyzeTTS](https://github.com/gronank/AnalyzeTTS)

## Overview

The pipeline works in two phases:

1. **Calibration (one-time, or when the map changes)** — `TTS2KML/calibrate.py` reads
   town Ground Control Points (`town_gcps.json`) plus real-world coordinates
   (`towns.lua`) and fits a 2D-quadratic transform, writing `TTS2KML/tts2lola.json`.
2. **Conversion (every turn)** — `TTS2KML/tts2kml.py` reads the TTS save and
   `tts2lola.json`, converts each on-board unit's game coordinates to real-world
   longitude/latitude, and writes a single KML grouped by faction. `process_maps.bat`
   orchestrates this and archives the output.

## How It Works

### The map: one stitched board from four tiles
The map is a single continuous board assembled from four `Custom_Tile` objects
(nicknamed `1`–`4`), each 15×15 scale and rotated `rotY=270`. They abut on a 30-unit
grid in a diagonal-staircase layout:

```
[ 1 ][   ]     1 = top-left
[ 2 ][ 3 ]     2 = left-center, 3 = right-center
[   ][ 4 ]     4 = bottom-right
```

Because units already carry world coordinates, the converter needs **no map-object
lookup** — it transforms unit positions directly through the board frame stored in
`tts2lola.json`.

### Coordinate transformation
`tts2lola.json` contains:
- `frame` — the board origin + scale used to turn world `posX/posZ` into board-relative
  `(x, y)` (with the `z,x` axis swap that undoes the tiles' rotation).
- `easting` / `northing` — 2D-quadratic coefficients (`a..f`) mapping board `(x, y)` to
  longitude / latitude. A quadratic is used because the board spans a large area
  (≈ 1 inch TTS = 5 km) where a single linear fit would leave edge error.
- `tiles` + `margin` — per-tile extents used to drop units that aren't on any board.

### Calibration from town control points
The tile images carry no coordinate grid, so the board is georeferenced using towns as
control points:
- `pixel → TTS world coordinate` is computed analytically from each tile's known
  position, scale, and orientation.
- `town → real lon/lat` comes from `towns.lua`.
- `town → pixel` is recorded once in `town_gcps.json` (each town's dot location in its
  tile image).

To re-calibrate, edit `town_gcps.json` and re-run `calibrate.py` — no code changes.

### Unit processing & faction grouping
Units are sorted into one folder each, by priority:
`Russia` (`RUS`) → `Finland` (`FIN`) → `Sweden` (`SWE`) → `NATO` (`NATO`, not FIN/SWE)
→ `Neutral` (untagged / `Marker`). Units off all four boards are dropped.

## Requirements

- Python 3.x (must be added to system PATH)
- Folder structure:
  ```
  UTNS2_TTS2KML/
  ├── process_maps.bat
  └── TTS2KML/
      ├── tts2kml.py        (converter)
      ├── calibrate.py      (calibration)
      ├── towns.lua         (real-world city coordinates)
      ├── town_gcps.json    (image-derived control points)
      └── tts2lola.json     (generated transform)
  ```

## Dependency Installation

1. Install Python:
   - Download from https://www.python.org/downloads/
   - **Important**: Check "Add Python to PATH" during installation
   - Verify by opening Command Prompt and typing: `python --version`

2. Install Python packages:
   - From the repo root, run: `pip install -r requirements.txt`
   - Runtime needs `pykml` + `lxml`; calibration also needs `numpy` + `lupa`.

3. Verify Python PATH (if Python isn't recognized):
   - Open System Properties → Advanced → Environment Variables
   - Under "System Variables", select "Path" and add (typically):
     ```
     C:\Users\[Username]\AppData\Local\Programs\Python\Python3x\
     C:\Users\[Username]\AppData\Local\Programs\Python\Python3x\Scripts\
     ```

## Usage

1. Place your TTS save file (e.g., `TS_Save_160.json`) in the repo root.
2. Run `process_maps.bat`.
3. When prompted, enter an archive folder name (examples: `GT3`, `2025-10-21-Turn3`).
4. A single KML named `UTNS_<SaveName>.kml` is generated (the `<SaveName>` is read from
   the save file and sanitized for use as a filename).
5. The output is also archived under `Archived KML's/<your-folder-name>/` alongside the
   original save JSON for traceability.

### Where the files go
- The latest KML is copied to the repository root (for quick access).
- A persistent copy is placed in `Archived KML's/<your-folder-name>/`, containing the
  generated `UTNS_<SaveName>.kml` and the original save JSON.

## Recalibrating the map

If the board tiles change (new images, repositioned tiles), regenerate the transform:

1. Update `TTS2KML/town_gcps.json` with the new tile centers and town control points
   (each town's pixel position in its tile image). Use ≥ 6 well-spread towns across all
   four tiles for an accurate quadratic fit.
2. Run:
   ```
   cd TTS2KML
   python calibrate.py
   ```
3. `calibrate.py` prints per-town residuals (in degrees and approximate km) and the
   maximum residual, then writes `tts2lola.json`. If a town's residual is large, fix its
   pixel coordinates (or add refinement points) and re-run.

## Script Details

### process_maps.bat
- Finds the JSON save file in the repo root.
- Prompts for an archive folder name.
- Runs `TTS2KML/tts2kml.py` and copies the generated KML to the repo root and the
  archive folder (with the source JSON).

### TTS2KML/calibrate.py
- Loads `town_gcps.json` (tile geometry, orientation, town pixel control points) and
  `towns.lua` (real-world coordinates).
- Converts each control point's pixel position to a TTS world coordinate, then to the
  board frame, and fits a 2D-quadratic transform for longitude and latitude.
- Writes `tts2lola.json` and prints calibration residuals.

### TTS2KML/tts2kml.py
- Loads `tts2lola.json` and the TTS save.
- For each tagged unit on one of the four boards, transforms its position to lon/lat.
- Groups units into Russia / Finland / Sweden / NATO / Neutral folders and writes a
  single KML, preserving unit names and counter imagery.

## Troubleshooting

1. **Python path issues**: verify `python --version`; check the PATH environment variable.
2. **Save file issues**: ensure the save is valid JSON and the four map tiles are present
   (nicknames `1`–`4`); verify units carry `Transform` and `Tags`.
3. **Units missing from the KML**: confirm they're tagged and sit on a board tile (off-board
   staging/reserve units are intentionally dropped). Widen `margin` in `town_gcps.json`
   (and re-calibrate) if a board edge is clipping valid units.
4. **Positions look skewed**: re-check the town control points in `town_gcps.json` and the
   `orientation` block, then re-run `calibrate.py` and inspect the residuals.
