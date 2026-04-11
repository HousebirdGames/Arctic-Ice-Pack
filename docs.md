# Arctic Ice Pack — Technical Reference

Adds a walkable pack-ice sheet to the arctic region of Stormworks: Build and Rescue.
Players and vehicles can traverse on top; submarines can dive beneath.
The ice is composed of overlapping irregular polygon slabs (square, pentagon variants, trapezoid)
with a low-poly aesthetic.

---

## Directory Structure

```
arctic_ice_pack/
├── src/
│   ├── generate_tiles.py   # all source logic: FBX generation + tile XML patching
│   └── config.json         # all tuneable parameters
├── meshes/                 # [built] compiled .mesh and .phys files (8 files)
├── tiles/
│   ├── mod/                # [built] primary patched tile XMLs
│   ├── mod_extra/          # [built] optional extra patched tile XMLs
│   └── original/           # [built] backup of original game tiles (restored by disable.bat)
├── build.bat               # full rebuild: FBX → compile → copy → patch XMLs
├── enable.bat              # deploy mod to game ROM
└── disable.bat             # restore original game files
```

`tiles/` and `meshes/` are in `.gitignore` — only source and config are versioned.

---

## Build Pipeline

### build.bat (4 stages)

**Stage 1** — `python src/generate_tiles.py --fbx-only`
Generates 4 FBX ASCII files into `<Stormworks>/sdk/meshes/`:
- `arctic_ice_flat.fbx` — square slab
- `arctic_ice_penta.fbx` — regular pentagon
- `arctic_ice_penta2.fbx` — wide pentagon variant (asymmetric bearings)
- `arctic_ice_trap.fbx` — trapezoid (wide end × 1.0, narrow end × 0.6)

**Stage 2** — `mesh_compiler.com` (Stormworks SDK tool, run from `<Stormworks>/sdk/`)
Each FBX is compiled twice:
- Default mode → `.mesh` (visual rendering)
- `-m physics_mesh` → `.phys` (collision geometry)

**Stage 3** — Copy 8 compiled files to `arctic_ice_pack/meshes/`

**Stage 4** — `python src/generate_tiles.py`
Patches game tile XMLs, outputs to `tiles/mod/` and `tiles/mod_extra/`.

### enable.bat

1. Calls `disable.bat silent` — atomically restores originals first, preventing stale stamps from a previous build
2. Copies 8 `.mesh`/`.phys` files to `<Stormworks>/rom/meshes/`
3. Copies all `tiles/mod/*.xml` to `<Stormworks>/rom/data/tiles/`
4. Asks user whether to also copy `tiles/mod_extra/*.xml` (see tile categories below)

### disable.bat

1. Deletes the 8 mesh files from `rom/meshes/` (silent on missing)
2. Copies `tiles/original/*.xml` back to `rom/data/tiles/`

`disable.bat` accepts a `silent` argument — suppresses the `pause` at the end, used internally by `enable.bat`.

---

## Configuration — src/config.json

```json
{
  "ice_height": 8,
  "shape_mix": {
    "random_seed": 420,
    "mesh_size_m": 2800,
    "slab_depth_m": 28.0,
    "bevel_inset_m": 0.8
  },
  "tile_exclusions": [
    "arctic_tile_12_oilrig",
    "arctic_island_playerbase",
    "arctic_tile_11", "arctic_tile_13",
    "arctic_tile_21", "arctic_tile_22", "arctic_tile_23",
    "arctic_tile_31", "arctic_tile_32", "arctic_tile_33"
  ]
}
```

| Key | Effect |
|-----|--------|
| `ice_height` | Y position (metres) of ice surface above water |
| `mesh_size_m` | Footprint of each ice slab in metres. Default 2800 m — intentionally larger than the 1 km tile grid to prevent gaps at tile boundaries, especially after random rotation |
| `slab_depth_m` | Ice thickness in metres (affects bevel profile depth) |
| `bevel_inset_m` | Horizontal inset of bevel rim — creates sloped edge appearance |
| `random_seed` | Global seed for deterministic per-tile variation |
| `tile_exclusions` | Tile filenames (without `.xml`) to skip patching entirely |

Changing any value and re-running `build.bat` fully regenerates meshes and tiles.

---

## Tile Patching Algorithm

Source: `patch_world_tiles()` in `generate_tiles.py`

### Tile Categories

Tiles in `<Stormworks>/rom/data/tiles/` are classified by filename prefix:

**PRIMARY** (`tiles/mod/`) — arctic-only tiles; safe to add ice visuals globally:
- `ice_shelf_0*` — arctic ice shelf tiles
- `arctic_tile_*` — generic arctic tiles
- `arctic_island_*` — arctic island tiles
- `island_41_*` — underwater mining island
- `island_42_*` — volcano island

**EXTRA** (`tiles/mod_extra/`) — tiles that also appear in non-arctic regions; only physics is added to avoid ice visuals showing up elsewhere:
- `track_*` — train track tiles

`enable.bat` asks the user whether to deploy extra tiles.

### Per-Tile Processing

For each matching tile (not in exclusion list):

1. **Deterministic RNG** seeded from `MD5(f"{RANDOM_SEED}:{filename}")` — ensures identical output across rebuilds, different shape/rotation per tile.

2. **Shape selection** (single roll):
   - 40% → `arctic_ice_penta`
   - 30% → `arctic_ice_penta2`
   - 15% → `arctic_ice_trap`
   - 15% → `arctic_ice_flat`

3. **Rotation** — one of `[0, 45, 90, 135, 180, 225, 270, 315]` degrees (Y-axis)

4. **Y micro-jitter** — `ice_height + uniform(-0.01, 0.01)` — prevents z-fighting when overlapping slabs from adjacent tiles render at the same Y.

5. **Stamp injection** — string replacement into XML:
   - Before `</physics_meshes>`: inject a `<physics_mesh>` element
   - Before `</meshes>`: inject a `<mesh>` element (primary tiles only; extra tiles get physics only)
   - Handles both `<tag/>` (self-closing empty) and `<tag>...</tag>` forms

6. **Backup** — on every run, the ROM tile is read, stripped of any existing ice stamps, and written to `tiles/original/`. This keeps the backup clean regardless of ROM state.

---

## XML Tile Format

Stormworks tile XMLs define one 1 km² world grid square:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definition>
  <meshes>
    <!-- visual meshes -->
    <mesh id="..." file_name="meshes/filename.mesh">
      <transform 00="cos" 02="sin" 20="-sin" 22="cos" 30="x" 31="y" 32="z"/>
    </mesh>
  </meshes>
  <physics_meshes>
    <!-- collision meshes -->
    <physics_mesh id="..." file_name="meshes/filename.phys">
      <transform .../>
    </physics_mesh>
  </physics_meshes>
  <!-- other sections: lights, tracks, interactables, etc. -->
</definition>
```

### Transform Attribute Format

Encodes a 4×4 matrix in sparse form. Unspecified values default to identity (0 for translation, 1 for diagonal scale).

| Attr | Matrix position | Meaning |
|------|----------------|---------|
| `00` | M[0][0] | X-axis X component (cos θ for Y-rotation) |
| `02` | M[0][2] | X-axis Z component (sin θ for Y-rotation) |
| `20` | M[2][0] | Z-axis X component (-sin θ for Y-rotation) |
| `22` | M[2][2] | Z-axis Z component (cos θ for Y-rotation) |
| `30` | M[3][0] | X translation |
| `31` | M[3][1] | Y translation |
| `32` | M[3][2] | Z translation |

Example — 45° Y-rotation at height 8 m:
```xml
<transform 00="0.707107" 02="0.707107" 20="-0.707107" 22="0.707107" 30="0" 31="8.005" 32="0"/>
```

The injected ice stamps always use `x=0, z=0` (tile centre), `y=ice_height ± jitter`.

### Injected Stamp IDs

- Visual mesh: `id="flat_ice_vis"` (fixed string regardless of shape)
- Physics mesh: `id="flat_ice_phys"` (fixed string regardless of shape)

---

## FBX Mesh Generation

All meshes are FBX 7.3.0 ASCII format (text-based, human-readable).

**Unit convention**: 1 FBX unit = 1 cm. Dimensions in metres are multiplied by 100.

**Coordinate system** (set in FBX GlobalSettings):
- Y-up (`UpAxis=1`)
- Z-front (`FrontAxis=2`)
- `UnitScaleFactor=2.54` (matches Stormworks SDK expectation)

### Shared Geometry Pattern

Every mesh type follows this structure:
- Top face at Y=0
- Bevel rim vertices at Y=`-slab_depth_cm`, inset horizontally by `bevel_inset_cm`
- Face normals computed per triangle (flat shading — all smoothing groups = 0)
- UVs: planar XZ mapping, normalized to [0,1] over the bounding box
- Single material (`Material::white`) — Stormworks applies its own texture/shader

### arctic_ice_flat (square)

- 8 vertices: 4 top corners at `±HALF`, 4 bevel bottom corners at `±(HALF - bevel_inset)`
- 12 triangles: top×2, bottom×2, 4 beveled sides×2 each
- Normals: top=(0,1,0), bottom=(0,-1,0), each side uses bevel angle computed from depth/inset ratio

### arctic_ice_penta (regular pentagon)

- Bearings: `[0°, 72°, 144°, 216°, 288°]`
- 10 vertices: 5 top rim + 5 bevel bottom rim (radially placed)
- 20 triangles: top fan (5 tris from centre) + bottom fan (5) + 5 beveled sides (2 each)
- Normals computed via cross product of edge vectors

### arctic_ice_penta2 (wide pentagon variant)

- Same structure as penta, different bearings: `[0°, 80°, 155°, 230°, 300°]`
- Produces asymmetric shape for visual variety

### arctic_ice_trap (trapezoid)

- Wide end (Z+): full `±HALF` width
- Narrow end (Z-): `±HALF × 0.6` width
- 8 vertices: 4 top + 4 bevel bottom
- 12 triangles: top×2, bottom×2, 4 sides×2 each
- Face normals computed dynamically via cross product

---

## Key Implementation Details

**Oversized slabs** — `mesh_size_m=2800` in 1 km tiles means each slab extends ~900 m beyond the tile boundary in each direction. This ensures full coverage despite random rotations.

**Idempotency** — `patch_world_tiles()` always reads directly from ROM, strips any existing ice stamps via `strip_ice_stamps()`, then applies exactly one stamp. Repeated calls to `generate()` always produce identical single-stamp output regardless of ROM state.

**Physics vs visual separation** — Extra tiles (tracks) only receive a `<physics_mesh>` stamp. No `<mesh>` is added, so there is no visual ice outside the arctic, but players/vehicles still get collision response.

**enable.bat atomicity** — Calls `disable.bat silent` before copying anything, ensuring no mix of old and new stamps if switching between builds.

**SDK dependency** — `mesh_compiler.com` must exist at `<Stormworks>/sdk/mesh_compiler.com`. The SDK is distributed separately by the game developer and is not included in this repo.

---

## Workflow: Making Changes

### Change ice height
Edit `ice_height` in `config.json`, run `build.bat`, then `enable.bat`.

### Change ice coverage (add/remove tiles)
- To exclude a tile: add its filename (without `.xml`) to `tile_exclusions` in `config.json`
- To add a new tile group as primary: add its filename prefix to `PRIMARY_PREFIXES` in `generate_tiles.py`
- To add a new tile group as extra (physics-only): add prefix to `EXTRA_PREFIXES`

### Change slab shape/size
Edit `mesh_size_m`, `slab_depth_m`, or `bevel_inset_m` in `config.json`.
Run full `build.bat` (FBX must be regenerated + recompiled).

### Change shape distribution
Edit the probability thresholds in `patch_world_tiles()`:
```python
if roll < 0.40:       # penta (40%)
elif roll < 0.70:     # penta2 (30%)
elif roll < 0.85:     # trap (15%)
else:                 # flat (15%)
```

### Change random variation
Edit `random_seed` in `config.json`. Run `build.bat`. Different seed → different per-tile shape/rotation assignments.

---

## Path Constants (generate_tiles.py)

Resolved relative to the script's location at runtime:

```
SCRIPT_DIR    = arctic_ice_pack/src/
MOD_DIR       = arctic_ice_pack/
STORMWORKS    = <Steam>/steamapps/common/Stormworks/
SDK_DIR       = <Stormworks>/sdk/
ROM_TILES_DIR = <Stormworks>/rom/data/tiles/
ORIGINAL_DIR  = arctic_ice_pack/tiles/original/
OUTPUT_DIR    = arctic_ice_pack/tiles/mod/
EXTRA_OUTPUT_DIR  = arctic_ice_pack/tiles/mod_extra/
```
