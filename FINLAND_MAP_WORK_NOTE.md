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
all `rotY=270`. They form a 2×2 stitched grid (single continuous map):

| Tile | posX  | posZ   | Notes (grid position) |
|------|-------|--------|-----------------------|
| 1    | 31.53 |  16.51 | top-right |
| 2    |  1.52 |  16.51 | top-middle/left |
| 3    |  1.53 | -13.51 | bottom-middle/left |
| 4    | -28.48| -13.51 | bottom-left |

(Tiles span ~X=-43→39, Z=-28→31 at 15-unit half-extents. The four images are separate
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
1. Are the 4 tiles a single continuous map (2×2), or 3 logical regions stitched? (Counts say 4
   tiles; user said "three maps stitched". Confirm intended logical grouping.)
2. Where will city/reference markers come from? Need them placed in a TTS save to calibrate.
3. Desired KML faction grouping (FIN/SWE/RUS folders?).
4. One combined KML output, or keep multiple files?

---

## Repo / environment facts
- New repo remote: `https://github.com/Bigredgeek/UTNS2_TTS2KML` (origin, branch `main`).
- Old project (reference): `../SOTN_TTS2KML_Merged` (remote Bigredgeek/SOTN_TTS2KML_Merged,
  upstream gronank/AnalyzeTTS).
- Python deps used by scripts: `numpy`, `lupa` (lua54), `pykml`, `lxml`.
- Helper inspection scripts left in repo root: `_inspect_160.py`, `_inspect2.py`
  (ad-hoc analysis of the new save — safe to delete later).

## Next action when resuming
Answer the open questions, then start with (A) `towns.lua` Finnish cities + (B) map-tile
coordinate handling, since everything else depends on a working calibration.
