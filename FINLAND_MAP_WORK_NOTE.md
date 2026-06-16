# UTNS_2 Finland Map — Work Reference Note

> Status: **Analysis paused.** No code changes made yet. This note captures everything needed
> to resume the conversion of the new Finland/Russia-border map (TTS save `TS_Save_160.json`).

## Goal
Adapt this project (a fork/copy of `SOTN_TTS2KML_Merged`) to a **new map: Finland near the
Russian border**, from a **new TTS save (`TS_Save_160.json`, "UTNS: Uprising v2")**.

Key change from the old SOTN project:
- **No more multiple scale levels** (old project had 3 separate layers: TacMap / StratMap / OpMap,
  each its own folder + transform).
- **New layout = THREE (actually four) map images stitched together** into one continuous board.

---

## What the OLD project does (baseline)
Three independent map folders, each with the same pipeline:
- `AnalyzeTTS-TacMap/`, `AnalyzeTTS-StratMap/`, `AnalyzeTTS-OpMap/`
- Each folder has:
  - `AnalyzeTTS/AnalyzeTTS.py` — calibrates transform from city markers → writes `tts2lola.json`
  - `AnalyzeTTS/towns.lua` — real-world lat/long of reference cities (German cities currently)
  - `AnalyzeTTS/TTS.json`, `Bounds.json` — calibration inputs
  - `TTS2KML/TTS2KML.py` — reads save + `tts2lola.json`, emits KML
  - `TTS2KML/tts2lola.json` — the "Lola offset file" (easting/northing transform + bounds)
- `process_maps.bat` — runs all three, copies KMLs to root + `Archived KML's/<name>/`
- Transform model:
  - TacMap = **linear** (easting/northing = scale + offset)
  - StratMap/OpMap = **2D quadratic** (a,b,c,d,e,f coefficients) + small latitude shear
- Map object located by `Nickname == 'TacMap'/'StratMap'/'OpMap'`.
- `relativeOffset()` computes `(posX-mapX)/scaleX`, `(posZ-mapZ)/scaleZ`, then swaps axes (z,x)
  to undo TTS rotation/mirror.
- City markers matched by `Nickname` against keys in `towns.lua`.

## "Lola offset file" = `tts2lola.json`
Per-map JSON with `easting`, `northing` (transform coeffs) and `bounds` (NE/SW in relative units).
A new one must be generated for the Finland map.

---

## NEW SAVE ANALYSIS — `TS_Save_160.json` (SaveName: "UTNS: Uprising v2")
154 top-level objects. **Critical structural differences:**

### 1. No TacMap/StratMap/OpMap objects exist
The map is now **four big `Custom_Tile` objects** nicknamed `1`,`2`,`3`,`4`, each scale 15×15,
all `rotY=270`. They form a **continuous stitched board arranged as a diagonal staircase**
(NOT a filled 2×2 grid).

**CONFIRMED VISUAL LAYOUT (user, 2026-06-16 + attached screenshot):**
- Tile **1 = top-left**
- Tile **2 = left-center**
- Tile **3 = right-center**
- Tile **4 = bottom-right**

The board is therefore a 3-row × 2-column staircase with the top-right and bottom-left
cells EMPTY:
```
[ 1 ][   ]      row top
[ 2 ][ 3 ]      row middle   <- tiles 2 and 3 share the middle rows; 2 left, 3 right
[   ][ 4 ]      row bottom
```
(More precisely, by posX level: 1 is alone on the top row, 2+3 share the middle row,
4 is alone on the bottom row; by posZ level: 1+2 are the left column, 3+4 the right column.)

| Tile | posX  | posZ   | Visual position | Row (posX) | Col (posZ) |
|------|-------|--------|-----------------|-----------|-----------|
| 1    | 31.53 |  16.51 | top-left        | top (31.5)| left (16.5) |
| 2    |  1.52 |  16.51 | left-center     | mid (1.5) | left (16.5) |
| 3    |  1.53 | -13.51 | right-center    | mid (1.5) | right (-13.5) |
| 4    | -28.48| -13.51 | bottom-right    | bottom (-28.5) | right (-13.5) |

**Axis mapping (critical — explains why the old note's "top-right/bottom-left" labels were wrong):**
- Screen **vertical** (north/up) tracks **+posX** (higher posX = higher on screen). Tile 1 (X=31.5) is top, tile 4 (X=-28.5) is bottom.
- Screen **horizontal** (east/right) tracks **−posZ** (higher posZ = further LEFT). Tiles 1+2 (Z=16.5) are the left column, tiles 3+4 (Z=−13.5) the right column.
- This is consistent with `TTS2KML.relativeOffset()` returning `(z, x)` (axis swap) to undo the `rotY=270` rotation/mirror.

Tile centers are spaced exactly 30 units apart in both posX (31.5 / 1.5 / −28.5) and posZ
(16.5 / −13.5). Each tile is 15×15 scale = 30-unit full extent, so tiles **abut perfectly**
and unit world coordinates are already continuous across the whole board.

(Tiles span ~X=−43→47, Z=−28→31 at 15-unit half-extents. The four images are separate
Steam-hosted PNGs — different ImageURLs per tile.)

### 2. Units are now `Custom_Token` (not `Custom_Tile`/contained in bags)
- 123 top-level `Custom_Token` units, tagged. Tag distribution (recursive):
  - `NATO`: 110, `Units`: 110, `FIN`: 74, `SWE`: 36, `RUS`: 13
- New faction tags: **FIN, SWE, RUS** (Finland, Sweden, Russia) replace the old NATO/WP scheme.
  Note: many units carry BOTH a national tag AND `NATO`. There is no `WP` tag — Russians use `RUS`.
- Other objects: 11 `Chess_Queen`, 9 `Custom_Assetbundle`, 6 `HandTrigger`, 1 `Custom_Model`.
- Unit coordinate span: X: -33.05..4.45, Z: -0.10..58.92 (note units extend well beyond the
  tile area in Z — likely an off-board staging/reserve area).

### 3. No city/town reference markers present yet
The distinct nicknames are all military units (e.g. `1/2MechInf`, `2ndResBdeHQ`, `RussBatt`,
`SOF Kettu`, `LaplandJaegerHQ`, `NorrbottenRegHQ`) plus tile numbers and table furniture.
**There are currently no Finnish/Swedish city markers** to calibrate against — `towns.lua` only
has German + a few NATO-flank cities (Murmansk, Leningrad, Andoya, etc.).

---

## REQUIRED CHANGES (the plan)

### A. Geographic reference data — `towns.lua`
- Add Finnish / Swedish / NW-Russian cities near the border with real lat/long, e.g.:
  Rovaniemi, Kemi, Tornio, Oulu, Kajaani, Kuusamo, Sodankylä, Ivalo, Kemijärvi (FIN);
  Luleå, Boden, Kiruna, Haparanda (SWE); Murmansk, Kandalaksha, Alakurtti (RUS).
- Murmansk + Leningrad already exist and can stay.
- These markers must then be **placed in the TTS save** (or a calibration save) so the solver
  can match them — currently none exist in `TS_Save_160.json`.

### B. Map identification — replace `'TacMap'/'StratMap'/'OpMap'` lookup
- In both `AnalyzeTTS.py` and `TTS2KML.py`: the `Nickname == 'StratMap'` (etc.) logic must
  change to handle the **stitched 4-tile grid**. Options:
  1. Treat the whole board as one coordinate frame anchored to ONE reference tile, OR
  2. Compute a combined origin/scale spanning all four tiles.
- Decide a single canonical origin (likely tile center grid) + per-tile offsets, since each
  tile is a separate object at a known posX/posZ but the underlying world coords are continuous.

### C. Single transform instead of 3 layers
- Collapse to ONE pipeline / one `tts2lola.json` (no Tac/Strat/Op split).
- Likely keep the **2D-quadratic** solver (best for the larger Finland extent / projection).
- Regenerate the **Lola offset file** once calibration markers exist.

### D. Faction sorting — `TTS2KML.py createKmlDoc()`
- Old code sorts into NATO (`'NATO'`), Pact (`'WP'`), Marker. 
- New tags are FIN / SWE / RUS (+ NATO). Need new folder scheme, e.g.:
  - NATO/Finland (FIN), NATO/Sweden (SWE), Russia (RUS), Neutral/Marker.
- There is no `WP` tag anymore → Russian units (`RUS`) are the OPFOR.

### E. Bounds
- `Bounds.json` / bounds in `tts2lola.json` must cover the full stitched extent
  (tiles span roughly X −43..39, Z −28..31 in world units before relative scaling).

### F. Project structure / batch / scripts
- `process_maps.bat` currently loops 3 map folders → simplify to a single map run.
- `generate_release_links.py` hardcodes `REPO_SLUG = "Bigredgeek/SOTN_TTS2KML_Merged"` and
  asset names OpMap/StratMap/TacMap.kml → update repo slug to `Bigredgeek/UTNS2_TTS2KML`
  and the single/renamed KML output(s).
- `README.md` still says "SOTN_TTS2KML_Merged" and describes 3 layers → rewrite for the new
  single stitched Finland map.

---

## OPEN QUESTIONS FOR USER (resolve before coding)

> **ALL QUESTIONS RESOLVED (user, 2026-06-16). Decisions recorded below.**

**Q1 (layout) — ANSWERED:** 4 tiles, diagonal staircase, 1=TL / 2=LC / 3=RC / 4=BR,
single continuous coordinate frame. See "CONFIRMED VISUAL LAYOUT" above.

**Q2 — Calibration source — DECIDED: image-derived GCPs (no manual marker placement).**
The tile images carry **no coordinate graticule** (user confirmed), so pixels can't be read
as coordinates directly. Instead we use **towns as Ground Control Points (GCPs)** derived
straight from the imagery:
  - **Link 1 — pixel → TTS world coord = ANALYTIC/EXACT.** Each tile is a `Custom_Tile` at a
    known `posX/posZ`, scale 15 (±15 extent), `rotY=270`; the four abut on a 30-unit grid.
    So any stitched-image pixel maps to a known TTS world coordinate.
  - **Link 2 — town → real lat/long = LOOKUP** (`towns.lua`).
  - **Link 3 — pixel → town = visual extraction** (locate each town's DOT, not its text label).
  - Net effect: identical GCP math to placing markers, but **no manual marker placement**.
  - User MAY still export a `lola.json` calibration save with optional outer-boundary markers;
    treat those as supplemental/validation, not the primary source.
  - **Orientation lock:** pin the 1-of-8 flip/rotation using a known landmark (Gulf of Bothnia
    coast = west, Russia = east); verify by residuals.
  - **Fallback:** if any town's residual is large, user drops a few refinement markers only.

**Q3 — Transform model — DECIDED: keep 2D-quadratic.** Scale ≈ 1" TTS = 5 km; board spans
~hundreds of km, so projection curvature is non-trivial → quadratic (`[x²,y²,xy,x,y,1]`) with
GCPs spread across all four tiles (esp. corners) is the right model. (A single affine would
leave edge error; quadratic absorbs the projection bend.)

**Q4 — Faction grouping — DECIDED:** folders `Finland` (FIN), `Sweden` (SWE), `Russia` (RUS),
`NATO` (NATO-tagged but not FIN/SWE), `Neutral` (untagged/Marker). Priority routing so each
unit lands in exactly one folder: RUS → Finland? No — RUS→Russia; else FIN→Finland;
else SWE→Sweden; else NATO→NATO; else Neutral.

**Q5 — Output — DECIDED:** single KML named **`UTNS_<SaveName>.kml`** (derive from the save's
`SaveName`, sanitized). Batch script **still prompts for the archive folder name**. Keep the
`Archived KML's/<name>/` archive + root-copy workflow.

**Q6 — Project structure — DECIDED:** collapse the three `AnalyzeTTS-*` folders into ONE
pipeline; strip/simplify to this project's scope.

**Q7 — towns.lua — DECIDED:** KEEP existing entries; ADD FIN/SWE/RUS towns extracted by
analyzing the four tile images (prominent featured towns).

**Q8 — Off-board units — DECIDED:** DROP anything not on the four boards (bounds filter).

**Q9 — Special-icon logic — DECIDED:** REMOVE. HQ-supply / quarter-scale special cases no
longer exist in this iteration → delete that code path.

**Q10 — Release tooling — DECIDED:** slug → `Bigredgeek/UTNS2_TTS2KML`, asset → single new KML.

---

## ARCHITECTURE DECISION RECORD (2026-06-16)

### Board frame (replaces per-map `Nickname` lookup)
At RUNTIME, units already carry world `posX/posZ`, so **no tile/map-object lookup is needed**.
Define ONE synthetic "board frame" stored in `tts2lola.json`:
  - `origin` = chosen reference (board center, e.g. (1.5, 1.5)) and `scale` (e.g. 15).
  - `boardOffset(pos) = ((posZ-originZ)/scale, (posX-originX)/scale)`  ← keep the (z,x) swap
    that undoes `rotY=270` (matches old `TTS2KML.relativeOffset`).
  - The quadratic fit absorbs whatever linear scale we pick, so the exact constants are free.
This removes the fragile `Nickname=='StratMap'` search from BOTH scripts.

### Tile geometry (for calibration only)
- Tile centers: 1=(31.53,16.51) 2=(1.52,16.51) 3=(1.53,-13.51) 4=(-28.48,-13.51); half-extent 15.
- Tile world extent N = [posX±15] × [posZ±15]. Image is 3000×3000, `rotY=270` (axis swap+flip).
- pixel(px,py) in tile N → world: normalize u=px/3000, v=py/3000 → apply tile extent with the
  orientation locked by landmark. Then world → board frame → GCP for the quadratic fit.

### Calibration data file (NEW): `town_gcps.json`
Decouples the laborious image reading from the solver. Shape:
```jsonc
{ "tile_size_px": 3000,
  "tiles": { "1": {"posX":31.53,"posZ":16.51}, ... },
  "orientation": "<locked mapping u,v -> +/-X,+/-Z>",
  "gcps": [ {"town":"Rovaniemi","tile":"2","px":1234,"py":890}, ... ] }
```
AnalyzeTTS reads this + `towns.lua`, computes world coords, fits the quadratic, writes
`tts2lola.json`. Re-running calibration = edit this JSON, no code changes.

---

## CONTEXT REFERENCES (read these before implementing)

> All three `AnalyzeTTS-*` folders are near-identical copies. **StratMap is the canonical
> reference** for the new single pipeline because it already uses the 2D-quadratic solver
> (TacMap is linear). Paths below are the StratMap copies; the Op/Tac copies mirror them.

### Calibration solver
- [AnalyzeTTS-StratMap/AnalyzeTTS/AnalyzeTTS.py](AnalyzeTTS-StratMap/AnalyzeTTS/AnalyzeTTS.py)
  - `find_map_transform(objects, preferred_names=['StratMap'])` — locates map object by
    `Nickname`. **MUST change** for the 4-tile board (no `StratMap` object exists).
  - `relativeOffset(objectTransform, mapTransform)` — `((posX-mapX)/scaleX, (posZ-mapZ)/scaleZ)`,
    returns `(x, z)` (NOTE: solver returns x,z; the KML reader swaps to z,x — see below).
  - `constructMatrix()` — builds the `[x², y², xy, x, y, 1]` design matrix (2D quadratic).
  - `solve_ransac()` / `solve()` — RANSAC quadratic fit, **needs ≥6 city markers**.
  - City matching loop reads `Nickname` and looks it up in `towns` (exact, then `_`→space).
  - Writes `tts2lola.json` with `easting{a..f}`, `northing{a..f}`, `bounds{NorthEast,SouthWest}`.
  - Bounds come from `Bounds.json` `Chess_Pawn` markers named `NorthEast`/`SouthWest`.

### KML generator
- [AnalyzeTTS-StratMap/TTS2KML/TTS2KML.py](AnalyzeTTS-StratMap/TTS2KML/TTS2KML.py)
  - `class GeoReferencedMap` — loads `tts2lola.json`; finds map via
    `ttsObjects['Nickname'] == 'StratMap'`. **MUST change** for 4 tiles.
  - `GeoReferencedMap.relativeOffset()` — returns **`(z, x)`** (axis swap to undo `rotY=270`).
    This is the swap that makes the tile layout map to screen as described above.
  - `GeoReferencedMap.toLoLa()` — applies quadratic, then `lat += 0.02 * x` shear, and
    **bounds-filters** (returns `None` if outside `bounds`). Off-board units get dropped here.
  - `createKmlDoc()` — **faction sorting lives here**: currently `'NATO'`→nato, `'WP'`→pact,
    `'Marker'`→neutral folders named `NATO_StratMap` / `Pact_StratMap` / `Undefined_Stratmap`.
    **MUST change** to FIN/SWE/RUS scheme (Q4).
  - `icon_scale_for()` + `is_hq_supply_marker()` / `is_quarter_scale_marker()` — special-icon
    sizing keyed off two hard-coded Steam `ImageURL`s (`HQ_SUPPLY_IMAGE_URL`,
    `QUARTER_SCALE_IMAGE_URL`). See Q9.
  - Main loop handles top-level `Custom_Tile`/`Custom_Token` and `ContainedObjects` in bags.
    New units are top-level `Custom_Token` (good — already handled).

### Reference geo data
- [AnalyzeTTS-StratMap/AnalyzeTTS/towns.lua](AnalyzeTTS-StratMap/AnalyzeTTS/towns.lua)
  - `towns = { ["Name"] = { latitude=, longitude=, display_name= }, ... }`. Mostly German;
    already has `Murmansk`, `Leningrad`, `Andoya`, `Keflavik`, etc. Add FIN/SWE/RUS cities here.
  - Loaded in AnalyzeTTS.py via `lupa.lua54` (`loadfile('towns.lua')()`).

### Calibration inputs (per folder, used by AnalyzeTTS.py)
- `AnalyzeTTS-StratMap/AnalyzeTTS/TTS.json` — save snapshot used for calibration (city markers).
- `AnalyzeTTS-StratMap/AnalyzeTTS/Bounds.json` — `Chess_Pawn` corner markers for bounds.
- `AnalyzeTTS-StratMap/TTS2KML/tts2lola.json` — the generated transform consumed by TTS2KML.py.

### Orchestration / tooling
- [process_maps.bat](process_maps.bat) — copies save into all 3 `*/TTS2KML/`, runs each
  `TTS2KML.py`, trims + copies `TacMap/StratMap/OpMap.kml` to root and `Archived KML's/<name>/`.
  **MUST collapse** to a single map (Q6).
- [generate_release_links.py](generate_release_links.py) — `REPO_SLUG = "Bigredgeek/SOTN_TTS2KML_Merged"`
  (line ~13), `ASSET_NAMES = ("OpMap.kml","StratMap.kml","TacMap.kml")` (line ~14). Update both (Q10).
- [README.md](README.md) — still documents the old 3-layer SOTN project; rewrite for single map.

### New-save inspection helpers (REMOVED — recoverable from git history)
- `_inspect_160.py` / `_inspect2.py` — dumped the 4 tiles (pos/rot/scale/url), nicknames, tag
  distribution, unit extent. `_grid_detect.py` / `_tile_overview.py` — tile download/crop +
  graticule check. All four were one-time scaffolding; removed after calibration. Restore with
  `git show <commit>:_inspect_160.py` from the "with analysis scaffolding" commit if needed.
- Source save: [TS_Save_160.json](TS_Save_160.json) (SaveName "UTNS: Uprising v2", 154 objects).

### Transform shape reference (`tts2lola.json`)
```jsonc
{ "easting":  { "a":.., "b":.., "c":.., "d":.., "e":.., "f":.. },   // lon = a x² + b y² + c xy + d x + e y + f
  "northing": { "a":.., "b":.., "c":.., "d":.., "e":.., "f":.. },   // lat = (same form) + 0.02*x shear
  "bounds":   { "NorthEast":[x,y], "SouthWest":[x,y] } }            // in swapped (z,x) relative units
```

---

## Repo / environment facts
- New repo remote: `https://github.com/Bigredgeek/UTNS2_TTS2KML` (origin, branch `main`).
- Cloned locally at `C:\Users\Pathos\Documents\Coding\UTNS2_TTS2KML`.
- Old project (reference): `../SOTN_TTS2KML_Merged` (remote Bigredgeek/SOTN_TTS2KML_Merged,
  upstream gronank/AnalyzeTTS).
- Python deps used by scripts: `numpy`, `lupa` (lua54), `pykml`, `lxml`.
  - **All installed locally** (`pykml`, `lxml`, `numpy`, `lupa`). `requirements.txt` lists all four.
- Helper inspection scripts (`_inspect_160.py`, `_inspect2.py`, `_grid_detect.py`,
  `_tile_overview.py`) were one-time scaffolding — REMOVED after calibration (in git history).
- Tile images were downloaded to `_tile_images/` (gitignored, ~50 MB) and removed; re-fetchable
  from the save ImageURLs via the helper script in history (or `Invoke-WebRequest`).

---

## IMPLEMENTATION STATUS (2026-06-16)

### DONE — new single pipeline (`TTS2KML/`)
- `TTS2KML/tts2kml.py` — converter. Board-frame + 2D-quadratic transform; NO map-object
  lookup; per-tile on-board filter (drops off-board units); faction folders
  Russia/Finland/Sweden/NATO/Neutral (priority routing); output `UTNS_<SaveName>.kml`.
  Removed the HQ-supply / quarter-scale special-icon logic (Q9).
- `TTS2KML/calibrate.py` — reads `town_gcps.json` + `towns.lua`, pixel->world->board, lstsq fit
  (affine OR quadratic, `model` field; `auto` = affine until >=10 GCPs), prints per-GCP residuals
  + leave-one-out RMS (km), writes `tts2lola.json`. Affine/quadratic both emit the same 6 coeffs
  (affine zeros the quadratic terms) so tts2kml.py is model-agnostic.
- `TTS2KML/town_gcps.json` — tile geometry + orientation + `model:auto` + **8 real GCPs**
  (Kittila, Sodankyla, Rovaniemi, Kemijarvi, Salla, Posio, Taivalkoski, Pudasjarvi).
- `TTS2KML/towns.lua` — original entries KEPT + ~32 FIN/SWE/RUS regional towns (ASCII keys),
  incl. the 8 GCP towns. 165 total.
- `TTS2KML/tts2lola.json` — **REAL calibration** (affine), generated by calibrate.py.
- `process_maps.bat` — simplified to single run (finds save, runs converter, copies to root +
  `Archived KML's/<name>/`, still prompts for archive folder name).
- `generate_release_links.py` — slug `Bigredgeek/UTNS2_TTS2KML`, matches `UTNS*.kml` by prefix.
- `requirements.txt` — pykml, lxml, numpy, lupa.  `README.md` — rewritten for single map.
- `.gitignore` — ignores `_tile_images/`, staged `TTS2KML/TS_Save_*.json` + `TTS2KML/*.kml`.

### CALIBRATION RESULT (2026-06-16)
- Map is **interior Finnish Lapland** (Kittila–Sodankyla–Salla north → Pudasjarvi–Posio south),
  north-up, Russia east. NOT the coast — Gulf of Bothnia / Swedish / Russian-coast towns are
  off-map, so most of those `towns.lua` additions are unused (harmless).
- 8 GCPs across all 4 tiles. **Affine fit: 1.8 km RMS, 3.1 km max, 3.2 km leave-one-out.**
  (Data is near-perfectly linear → affine chosen over quadratic, which would overfit 8 points.)
- Unit output spans lon 25.1–27.1E, lat 66.2–66.67N (Rovaniemi front-line cluster) — sane.

### VALIDATED
- `tts2kml.py` on `TS_Save_160.json`: valid KML, 68 on-board units (of 123),
  Russia=13 / Finland=37 / Sweden=18, 52 styles. Faction routing + off-board drop +
  `UTNS_<SaveName>` filename derivation all confirmed.

### DONE — cleanup
- Old `AnalyzeTTS-TacMap/StratMap/OpMap` folders DELETED (git-recoverable). New pipeline is
  the self-contained `TTS2KML/` folder.
- Root `_*.py` helpers (`_inspect_160`, `_inspect2`, `_grid_detect`, `_tile_overview`) and the
  `_tile_images/` download cache REMOVED (recoverable from the "with analysis scaffolding" commit).

## To improve accuracy later (optional)
1. Add more GCPs to `town_gcps.json` (towns near board corners help most); read pixel dots off
   `_tile_images/tile{1..4}.png`. With >=10 GCPs set `model:"quadratic"` (or leave `auto`).
2. `cd TTS2KML && python calibrate.py`; watch the leave-one-out RMS (should stay low).
3. Re-run the converter / `process_maps.bat`; spot-check in Google Earth.
