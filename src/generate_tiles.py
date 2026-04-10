"""
Arctic Ice Pack - Tile Generator
Generates modified tile XMLs with ice mesh stamps.

Usage:
    python generate_tiles.py

Output goes to ../tiles/mod/
"""

import hashlib
import json
import math
import os
import random
import shutil

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
MOD_DIR       = os.path.dirname(SCRIPT_DIR)
STORMWORKS    = os.path.dirname(os.path.dirname(MOD_DIR))
SDK_DIR       = os.path.join(STORMWORKS, "sdk")
ROM_TILES_DIR = os.path.join(STORMWORKS, "rom", "data", "tiles")
CONFIG_PATH   = os.path.join(SCRIPT_DIR, "config.json")
ORIGINAL_DIR      = os.path.join(MOD_DIR, "tiles", "original")
OUTPUT_DIR        = os.path.join(MOD_DIR, "tiles", "mod")        # primary (ice_shelf + arctic)
EXTRA_OUTPUT_DIR  = os.path.join(MOD_DIR, "tiles", "mod_extra")  # extra (track, island, etc.)

# ── config ────────────────────────────────────────────────────────────────────
with open(CONFIG_PATH) as f:
    cfg = json.load(f)

ICE_Y           = cfg["ice_height"]                             # metres above water
RANDOM_SEED     = cfg["shape_mix"]["random_seed"]
MESH_SIZE_M     = cfg["shape_mix"].get("mesh_size_m",   2000)   # mesh footprint (metres)
SLAB_DEPTH_M    = cfg["shape_mix"].get("slab_depth_m",   25)   # ice slab thickness (metres)
BEVEL_INSET_M   = cfg["shape_mix"].get("bevel_inset_m",  0.5)   # horizontal bevel inset (metres)

# Derived FBX constants (1 FBX unit = 1 cm)
BEVEL_DEPTH_CM  = -int(SLAB_DEPTH_M * 100)   # negative = below top face
BEVEL_INSET_CM  =  int(BEVEL_INSET_M * 100)  # positive = inset from edge

# Bevel side normal components (valid for all mesh types)
_bm  = math.sqrt(BEVEL_INSET_CM**2 + BEVEL_DEPTH_CM**2)
BEVEL_N_SIDE = abs(BEVEL_DEPTH_CM) / _bm   # magnitude of outward horizontal component
BEVEL_N_DOWN = BEVEL_INSET_CM       / _bm  # magnitude of downward component

TILE_EXCLUSIONS = set(cfg.get("tile_exclusions", []))  # filenames (without .xml) to skip

random.seed(RANDOM_SEED)

# ── patchable world tile prefixes ─────────────────────────────────────────────
# Tiles matching these prefixes have per-grid-square physics activation (no
# radius limit).  blank.xml is permanently inert — not listed here.
#
# PRIMARY: get ice visual + physics.  Only arctic-specific tiles — safe to add
#          ice graphics globally since they only appear in the arctic region.
PRIMARY_PREFIXES = (
    "ice_shelf_0",   # arctic ice shelf tiles
    "island_41_",   # underwater mining island
    "arctic_tile_",
    "arctic_island_",
    "island_42_" # Volcano
)
# EXTRA: physics only, no ice visual.  These tile types appear in multiple world
#        regions, so adding ice graphics would spread visuals outside the arctic.
#        Controlled by the extra_tile_physics config flag.
EXTRA_PREFIXES = (
    "track_",       # train track tiles
)


def _nfmt(v):
    """Format a normal component: strip trailing zeros, keep sign."""
    s = f"{v:.6f}".rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def _bevel_normals_flat():
    """
    Build the Normals: *108 inner content string for the flat slab.
    Normal order matches topology: top×2, south×2, east×2, north×2, west×2, bottom×2.
    Each face uses 2 triangles × 3 vertices = 6 vertex-normals, all identical.
    """
    ns, nd = BEVEL_N_SIDE, BEVEL_N_DOWN

    def row3(nx, ny, nz):  # same normal repeated 3 times (one triangle)
        n = f"{_nfmt(nx)},{_nfmt(ny)},{_nfmt(nz)}"
        return f"{n},{n},{n}"

    lines = [
        row3(0,   1,   0  ) + ",",   # top tri1
        row3(0,   1,   0  ) + ",",   # top tri2
        row3(0,  -nd, -ns ) + ",",   # south tri1
        row3(0,  -nd, -ns ) + ",",   # south tri2
        row3(ns, -nd,  0  ) + ",",   # east  tri1
        row3(ns, -nd,  0  ) + ",",   # east  tri2
        row3(0,  -nd,  ns ) + ",",   # north tri1
        row3(0,  -nd,  ns ) + ",",   # north tri2
        row3(-ns,-nd,  0  ) + ",",   # west  tri1
        row3(-ns,-nd,  0  ) + ",",   # west  tri2
        row3(0,  -1,   0  ) + ",",   # bottom tri1
        row3(0,  -1,   0  ),         # bottom tri2  (no trailing comma)
    ]
    return "\n\t\t\t\t".join(lines)


def generate_ice_flat_fbx():
    """
    Write arctic_ice_flat.fbx to sdk/meshes/ at MESH_SIZE_M × MESH_SIZE_M.

    The mesh is a centred square slab:
      top face  : ±HALF at Y=0
      bottom rim: ±(HALF − bevel_inset) at Y=−slab_depth  (bevelled sides)
    8 vertices, 12 triangles.
    """
    HALF = int(MESH_SIZE_M / 2 * 100)
    BI   = BEVEL_INSET_CM
    BY   = BEVEL_DEPTH_CM
    B    = HALF - BI

    vert_str = (f"-{HALF},0,-{HALF},\n\t\t\t"
                f"{HALF},0,-{HALF},\n\t\t\t"
                f"{HALF},0,{HALF},\n\t\t\t"
                f"-{HALF},0,{HALF},\n\t\t\t"
                f"-{B},{BY},-{B},\n\t\t\t"
                f"{B},{BY},-{B},\n\t\t\t"
                f"{B},{BY},{B},\n\t\t\t"
                f"-{B},{BY},{B}")

    normals_str = _bevel_normals_flat()
    fbx = """; FBX 7.3.0 project file
; Copyright (C) 1997-2010 Autodesk Inc. and/or its licensors.
; All rights reserved.
; ----------------------------------------------------

FBXHeaderExtension:  {
\tFBXHeaderVersion: 1003
\tFBXVersion: 7300
\tCreationTimeStamp:  {
\t\tVersion: 1000
\t\tYear: 2024
\t\tMonth: 1
\t\tDay: 1
\t\tHour: 0
\t\tMinute: 0
\t\tSecond: 0
\t\tMillisecond: 0
\t}
\tCreator: "FBX SDK/FBX Plugins version 2016.0"
\tSceneInfo: "SceneInfo::GlobalInfo", "UserData" {
\t\tType: "UserData"
\t\tVersion: 100
\t\tMetaData:  {
\t\t\tVersion: 100
\t\t\tTitle: ""
\t\t\tSubject: ""
\t\t\tAuthor: ""
\t\t\tKeywords: ""
\t\t\tRevision: ""
\t\t\tComment: ""
\t\t}
\t\tProperties70:  {
\t\t\tP: "DocumentUrl", "KString", "Url", "", "arctic_ice_flat.fbx"
\t\t\tP: "SrcDocumentUrl", "KString", "Url", "", "arctic_ice_flat.fbx"
\t\t\tP: "Original", "Compound", "", ""
\t\t\tP: "Original|ApplicationVendor", "KString", "", "", "Autodesk"
\t\t\tP: "Original|ApplicationName", "KString", "", "", "3ds Max"
\t\t\tP: "Original|ApplicationVersion", "KString", "", "", "2014"
\t\t\tP: "LastSaved", "Compound", "", ""
\t\t\tP: "LastSaved|ApplicationVendor", "KString", "", "", "Autodesk"
\t\t\tP: "LastSaved|ApplicationName", "KString", "", "", "3ds Max"
\t\t\tP: "LastSaved|ApplicationVersion", "KString", "", "", "2014"
\t\t}
\t}
}
GlobalSettings:  {
\tVersion: 1000
\tProperties70:  {
\t\tP: "UpAxis", "int", "Integer", "",1
\t\tP: "UpAxisSign", "int", "Integer", "",1
\t\tP: "FrontAxis", "int", "Integer", "",2
\t\tP: "FrontAxisSign", "int", "Integer", "",1
\t\tP: "CoordAxis", "int", "Integer", "",0
\t\tP: "CoordAxisSign", "int", "Integer", "",1
\t\tP: "OriginalUpAxis", "int", "Integer", "",2
\t\tP: "OriginalUpAxisSign", "int", "Integer", "",1
\t\tP: "UnitScaleFactor", "double", "Number", "",2.54
\t\tP: "OriginalUnitScaleFactor", "double", "Number", "",2.54
\t\tP: "AmbientColor", "ColorRGB", "Color", "",0,0,0
\t\tP: "DefaultCamera", "KString", "", "", "Producer Perspective"
\t\tP: "TimeMode", "enum", "", "",6
\t\tP: "TimeProtocol", "enum", "", "",2
\t\tP: "SnapOnFrameMode", "enum", "", "",0
\t\tP: "TimeSpanStart", "KTime", "Time", "",0
\t\tP: "TimeSpanStop", "KTime", "Time", "",153953860000
\t\tP: "CustomFrameRate", "double", "Number", "",-1
\t\tP: "TimeMarker", "Compound", "", ""
\t\tP: "CurrentTimeMarker", "int", "Integer", "",-1
\t}
}

Documents:  {
\tCount: 1
\tDocument: 1000000, "", "Scene" {
\t\tProperties70:  {
\t\t\tP: "SourceObject", "object", "", ""
\t\t\tP: "ActiveAnimStackName", "KString", "", "", ""
\t\t}
\t\tRootNode: 0
\t}
}

References:  {
}

Definitions:  {
\tVersion: 100
\tCount: 5
\tObjectType: "GlobalSettings" {
\t\tCount: 1
\t}
\tObjectType: "AnimationStack" {
\t\tCount: 1
\t\tPropertyTemplate: "FbxAnimStack" {
\t\t\tProperties70:  {
\t\t\t\tP: "Description", "KString", "", "", ""
\t\t\t\tP: "LocalStart", "KTime", "Time", "",0
\t\t\t\tP: "LocalStop", "KTime", "Time", "",0
\t\t\t\tP: "ReferenceStart", "KTime", "Time", "",0
\t\t\t\tP: "ReferenceStop", "KTime", "Time", "",0
\t\t\t}
\t\t}
\t}
\tObjectType: "AnimationLayer" {
\t\tCount: 1
\t\tPropertyTemplate: "FbxAnimLayer" {
\t\t\tProperties70:  {
\t\t\t\tP: "Weight", "Number", "", "A",100
\t\t\t\tP: "Mute", "bool", "", "",0
\t\t\t\tP: "Solo", "bool", "", "",0
\t\t\t\tP: "Lock", "bool", "", "",0
\t\t\t\tP: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8
\t\t\t\tP: "BlendMode", "enum", "", "",0
\t\t\t\tP: "RotationAccumulationMode", "enum", "", "",0
\t\t\t\tP: "ScaleAccumulationMode", "enum", "", "",0
\t\t\t\tP: "BlendModeBypass", "ULongLong", "", "",0
\t\t\t}
\t\t}
\t}
\tObjectType: "Model" {
\t\tCount: 1
\t}
\tObjectType: "Geometry" {
\t\tCount: 1
\t\tPropertyTemplate: "FbxMesh" {
\t\t\tProperties70:  {
\t\t\t\tP: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8
\t\t\t\tP: "BBoxMin", "Vector3D", "Vector", "",0,0,0
\t\t\t\tP: "BBoxMax", "Vector3D", "Vector", "",0,0,0
\t\t\t\tP: "Primary Visibility", "bool", "", "",1
\t\t\t\tP: "Casts Shadows", "bool", "", "",1
\t\t\t\tP: "Receive Shadows", "bool", "", "",1
\t\t\t}
\t\t}
\t}
\tObjectType: "Material" {
\t\tCount: 1
\t}
}

Objects:  {
\tAnimationStack: 5000, "AnimStack::Take 001", "" {
\t\tProperties70:  {
\t\t\tP: "LocalStop", "KTime", "Time", "",153953860000
\t\t\tP: "ReferenceStop", "KTime", "Time", "",153953860000
\t\t}
\t}
\tAnimationLayer: 6000, "AnimLayer::BaseLayer", "" {
\t}
\tGeometry: 2000, "Geometry::arctic_ice_flat", "Mesh" {
\t\tVertices: *24 {
\t\t\ta: """ + vert_str + """
\t\t}
\t\tPolygonVertexIndex: *36 {
\t\t\ta: 0,2,-2,
\t\t\t0,3,-3,
\t\t\t0,1,-6,
\t\t\t0,5,-5,
\t\t\t1,2,-7,
\t\t\t1,6,-6,
\t\t\t2,3,-8,
\t\t\t2,7,-7,
\t\t\t3,0,-5,
\t\t\t3,4,-8,
\t\t\t4,5,-7,
\t\t\t4,6,-8
\t\t}
\t\tGeometryVersion: 124
\t\tLayerElementNormal: 0 {
\t\t\tVersion: 101
\t\t\tName: ""
\t\t\tMappingInformationType: "ByPolygonVertex"
\t\t\tReferenceInformationType: "Direct"
\t\t\tNormals: *108 {
\t\t\t\ta: FLAT_NORMALS_PLACEHOLDER
\t\t\t}
\t\t}
\t\tLayerElementUV: 0 {
\t\t\tVersion: 101
\t\t\tName: "UVChannel_1"
\t\t\tMappingInformationType: "ByPolygonVertex"
\t\t\tReferenceInformationType: "IndexToDirect"
\t\t\tUV: *8 {
\t\t\t\ta: 0,0,
\t\t\t\t1,0,
\t\t\t\t1,1,
\t\t\t\t0,1
\t\t\t}
\t\t\tUVIndex: *36 {
\t\t\t\ta: 0,2,1,
\t\t\t\t0,3,2,
\t\t\t\t3,2,1,
\t\t\t\t3,1,0,
\t\t\t\t3,2,1,
\t\t\t\t3,1,0,
\t\t\t\t3,2,1,
\t\t\t\t3,1,0,
\t\t\t\t3,2,1,
\t\t\t\t3,1,0,
\t\t\t\t0,1,2,
\t\t\t\t0,2,3
\t\t\t}
\t\t}
\t\tLayerElementSmoothing: 0 {
\t\t\tVersion: 102
\t\t\tName: ""
\t\t\tMappingInformationType: "ByPolygon"
\t\t\tReferenceInformationType: "Direct"
\t\t\tSmoothing: *12 {
\t\t\t\ta: 0,0,0,0,0,0,0,0,0,0,0,0
\t\t\t}
\t\t}
\t\tLayerElementMaterial: 0 {
\t\t\tVersion: 101
\t\t\tName: ""
\t\t\tMappingInformationType: "AllSame"
\t\t\tReferenceInformationType: "IndexToDirect"
\t\t\tMaterials: *1 {
\t\t\t\ta: 0
\t\t\t}
\t\t}
\t\tLayer: 0 {
\t\t\tVersion: 100
\t\t\tLayerElement:  {
\t\t\t\tType: "LayerElementNormal"
\t\t\t\tTypedIndex: 0
\t\t\t}
\t\t\tLayerElement:  {
\t\t\t\tType: "LayerElementUV"
\t\t\t\tTypedIndex: 0
\t\t\t}
\t\t\tLayerElement:  {
\t\t\t\tType: "LayerElementMaterial"
\t\t\t\tTypedIndex: 0
\t\t\t}
\t\t\tLayerElement:  {
\t\t\t\tType: "LayerElementSmoothing"
\t\t\t\tTypedIndex: 0
\t\t\t}
\t\t}
\t}
\tModel: 3000, "Model::arctic_ice_flat", "Mesh" {
\t\tVersion: 232
\t\tProperties70:  {
\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0
\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",0,0,0
\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0
\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1
\t\t}
\t\tShading: T
\t\tCulling: "CullingOff"
\t}
\tMaterial: 4000, "Material::white", "" {
\t\tVersion: 102
\t\tShadingModel: "phong"
\t\tMultiLayer: 0
\t\tProperties70:  {
\t\t\tP: "AmbientColor", "Color", "", "A",0,0,0
\t\t\tP: "DiffuseColor", "Color", "", "A",0.941176533699036,0.941176533699036,0.941176533699036
\t\t\tP: "SpecularColor", "Color", "", "A",0.5,0.5,0.5
\t\t\tP: "ShininessExponent", "Number", "", "A",25
\t\t\tP: "ReflectionFactor", "Number", "", "A",0
\t\t}
\t}
}

Connections:  {
\tC: "OO",3000,0
\tC: "OO",2000,3000
\tC: "OO",4000,3000
\tC: "OO",6000,5000
}

Takes:  {
\tCurrent: ""
\tTake: "Take 001" {
\t\tFileName: "Take_001.tak"
\t\tLocalTime: 0,153953860000
\t\tReferenceTime: 0,153953860000
\t}
}
"""
    fbx = fbx.replace("FLAT_NORMALS_PLACEHOLDER", normals_str)
    path = os.path.join(SDK_DIR, "meshes", "arctic_ice_flat.fbx")
    with open(path, "w", encoding="utf-8") as f:
        f.write(fbx)
    print(f"  Generated arctic_ice_flat.fbx ({MESH_SIZE_M} m × {MESH_SIZE_M} m, "
          f"bevel {BEVEL_INSET_M:.1f}m / {SLAB_DEPTH_M:.1f}m)")



def generate_ice_penta_fbx(fbx_name="arctic_ice_penta", bearings=None):
    """
    Write {fbx_name}.fbx — a pentagon slab at MESH_SIZE_M.

    A regular pentagon has no 90° rotational symmetry, so each of the 8 rotation
    steps (0–315° in 45° increments) looks genuinely different.  This gives much
    more visual variety than a square.

    Geometry:
      V0–V4 : top face vertices at circumradius R, bearings 0/72/144/216/288° from +Z
      BV0–BV4: bevel bottom rim at R_inner = R − BI/cos(36°), Y = BEVEL_DEPTH_CM
    10 vertices, 16 triangles (3 top + 3 bottom + 10 side).
    """
    HALF  = int(MESH_SIZE_M / 2 * 100)
    R     = HALF
    BI    = BEVEL_INSET_CM
    BY    = BEVEL_DEPTH_CM
    cos36 = math.cos(math.radians(36))
    R_in  = max(1, int(R - BI / cos36))

    # Bearings from north (+Z), CW (standard geographic)
    n_verts = 5
    if bearings is None:
        bearings = [i * 72.0 for i in range(n_verts)]   # 0, 72, 144, 216, 288

    # FBX coords: X = sin(bearing)*R, Y = 0/BY, Z = cos(bearing)*R
    def vert(r, y, b):
        return (int(r * math.sin(math.radians(b))), y, int(r * math.cos(math.radians(b))))

    top = [vert(R,    0,  b) for b in bearings]
    bot = [vert(R_in, BY, b) for b in bearings]
    all_v = top + bot   # indices 0–4 top, 5–9 bottom

    # ── Polygon topology ──────────────────────────────────────────────────────
    # FBX encodes last vertex of polygon as -(v+1)
    def enc(tris):
        out = []
        for tri in tris:
            out += [tri[0], tri[1], -(tri[2] + 1)]
        return out

    tris = []
    # Top face: fan from V0, CW-geographic winding → up normal
    for i in range(1, n_verts - 1):
        tris.append((0, i, i + 1))
    # Bottom face: reversed fan from BV0 → down normal
    for i in range(n_verts - 2):
        tris.append((n_verts, n_verts + n_verts - 1 - i, n_verts + n_verts - 2 - i))
    # Side quads (2 triangles each) — outward winding: (j, i, BVi), (j, BVi, BVj)
    for i in range(n_verts):
        j = (i + 1) % n_verts
        tris.append((j,          i,          n_verts + i))
        tris.append((j, n_verts + i, n_verts + j))

    poly_vals = enc(tris)
    poly_str  = ",\n\t\t\t".join(str(x) for x in poly_vals)
    poly_count = len(poly_vals)

    # ── Normals (flat shading — per polygon-vertex) ───────────────────────────
    ns, nd = BEVEL_N_SIDE, BEVEL_N_DOWN

    def cross3(a, b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

    def norm3(v):
        m = math.sqrt(sum(x*x for x in v))
        return tuple(x / m for x in v) if m > 1e-9 else (0, 1, 0)

    def face_n(tri):
        A, B, C = all_v[tri[0]], all_v[tri[1]], all_v[tri[2]]
        e1 = (B[0]-A[0], B[1]-A[1], B[2]-A[2])
        e2 = (C[0]-A[0], C[1]-A[1], C[2]-A[2])
        return norm3(cross3(e1, e2))

    # Mid-bearing of each side (outward horizontal direction)
    mid_b = [(bearings[i] + bearings[(i + 1) % n_verts]) / 2 for i in range(n_verts)]

    normals = []
    # Top (3 tris)
    for tri in tris[:3]:
        fn = face_n(tri)
        normals += [fn] * 3
    # Bottom (3 tris)
    for tri in tris[3:6]:
        fn = face_n(tri)
        normals += [fn] * 3
    # Sides: 5 quads × 2 tris — both tris of a quad share the same outward bevel normal
    for qi in range(n_verts):
        nx_h = ns * math.sin(math.radians(mid_b[qi]))
        nz_h = ns * math.cos(math.radians(mid_b[qi]))
        side_n = (nx_h, -nd, nz_h)
        normals += [side_n] * 6   # 2 tris × 3 verts

    normal_count = len(normals) * 3
    normal_lines = []
    for i, fn in enumerate(normals):
        s = f"{_nfmt(fn[0])},{_nfmt(fn[1])},{_nfmt(fn[2])}"
        if i < len(normals) - 1:
            normal_lines.append(s + ",")
        else:
            normal_lines.append(s)
    normals_str = "\n\t\t\t\t".join(normal_lines)

    # ── UVs: simple per-polygon-vertex planar XZ mapping ─────────────────────
    uv_list = []
    for tri in tris:
        for vi in tri:
            vx, _, vz = all_v[vi]
            uv_list.append(((vx + R) / (2 * R), (vz + R) / (2 * R)))

    uv_count   = len(uv_list) * 2
    uvidx_count = len(uv_list)
    uv_str     = ",\n\t\t\t\t".join(f"{u:.4f},{v:.4f}" for u, v in uv_list)
    uvidx_str  = ",\n\t\t\t\t".join(str(i) for i in range(uvidx_count))

    smooth_count = len(tris)
    vert_count   = len(all_v) * 3
    vert_str     = ",\n\t\t\t".join(f"{x},{y},{z}" for x, y, z in all_v)

    # ── FBX file ──────────────────────────────────────────────────────────────
    fbx = f"""; FBX 7.3.0 project file
; Copyright (C) 1997-2010 Autodesk Inc. and/or its licensors.
; All rights reserved.
; ----------------------------------------------------

FBXHeaderExtension:  {{
\tFBXHeaderVersion: 1003
\tFBXVersion: 7300
\tCreationTimeStamp:  {{
\t\tVersion: 1000
\t\tYear: 2024
\t\tMonth: 1
\t\tDay: 1
\t\tHour: 0
\t\tMinute: 0
\t\tSecond: 0
\t\tMillisecond: 0
\t}}
\tCreator: "FBX SDK/FBX Plugins version 2016.0"
\tSceneInfo: "SceneInfo::GlobalInfo", "UserData" {{
\t\tType: "UserData"
\t\tVersion: 100
\t\tMetaData:  {{
\t\t\tVersion: 100
\t\t\tTitle: ""
\t\t\tSubject: ""
\t\t\tAuthor: ""
\t\t\tKeywords: ""
\t\t\tRevision: ""
\t\t\tComment: ""
\t\t}}
\t\tProperties70:  {{
\t\t\tP: "DocumentUrl", "KString", "Url", "", "{fbx_name}.fbx"
\t\t\tP: "SrcDocumentUrl", "KString", "Url", "", "{fbx_name}.fbx"
\t\t\tP: "Original", "Compound", "", ""
\t\t\tP: "Original|ApplicationVendor", "KString", "", "", "Autodesk"
\t\t\tP: "Original|ApplicationName", "KString", "", "", "3ds Max"
\t\t\tP: "Original|ApplicationVersion", "KString", "", "", "2014"
\t\t\tP: "LastSaved", "Compound", "", ""
\t\t\tP: "LastSaved|ApplicationVendor", "KString", "", "", "Autodesk"
\t\t\tP: "LastSaved|ApplicationName", "KString", "", "", "3ds Max"
\t\t\tP: "LastSaved|ApplicationVersion", "KString", "", "", "2014"
\t\t}}
\t}}
}}
GlobalSettings:  {{
\tVersion: 1000
\tProperties70:  {{
\t\tP: "UpAxis", "int", "Integer", "",1
\t\tP: "UpAxisSign", "int", "Integer", "",1
\t\tP: "FrontAxis", "int", "Integer", "",2
\t\tP: "FrontAxisSign", "int", "Integer", "",1
\t\tP: "CoordAxis", "int", "Integer", "",0
\t\tP: "CoordAxisSign", "int", "Integer", "",1
\t\tP: "OriginalUpAxis", "int", "Integer", "",2
\t\tP: "OriginalUpAxisSign", "int", "Integer", "",1
\t\tP: "UnitScaleFactor", "double", "Number", "",2.54
\t\tP: "OriginalUnitScaleFactor", "double", "Number", "",2.54
\t\tP: "AmbientColor", "ColorRGB", "Color", "",0,0,0
\t\tP: "DefaultCamera", "KString", "", "", "Producer Perspective"
\t\tP: "TimeMode", "enum", "", "",6
\t\tP: "TimeProtocol", "enum", "", "",2
\t\tP: "SnapOnFrameMode", "enum", "", "",0
\t\tP: "TimeSpanStart", "KTime", "Time", "",0
\t\tP: "TimeSpanStop", "KTime", "Time", "",153953860000
\t\tP: "CustomFrameRate", "double", "Number", "",-1
\t\tP: "TimeMarker", "Compound", "", ""
\t\tP: "CurrentTimeMarker", "int", "Integer", "",-1
\t}}
}}

Documents:  {{
\tCount: 1
\tDocument: 1000000, "", "Scene" {{
\t\tProperties70:  {{
\t\t\tP: "SourceObject", "object", "", ""
\t\t\tP: "ActiveAnimStackName", "KString", "", "", ""
\t\t}}
\t\tRootNode: 0
\t}}
}}

References:  {{
}}

Definitions:  {{
\tVersion: 100
\tCount: 5
\tObjectType: "GlobalSettings" {{
\t\tCount: 1
\t}}
\tObjectType: "AnimationStack" {{
\t\tCount: 1
\t\tPropertyTemplate: "FbxAnimStack" {{
\t\t\tProperties70:  {{
\t\t\t\tP: "Description", "KString", "", "", ""
\t\t\t\tP: "LocalStart", "KTime", "Time", "",0
\t\t\t\tP: "LocalStop", "KTime", "Time", "",0
\t\t\t\tP: "ReferenceStart", "KTime", "Time", "",0
\t\t\t\tP: "ReferenceStop", "KTime", "Time", "",0
\t\t\t}}
\t\t}}
\t}}
\tObjectType: "AnimationLayer" {{
\t\tCount: 1
\t\tPropertyTemplate: "FbxAnimLayer" {{
\t\t\tProperties70:  {{
\t\t\t\tP: "Weight", "Number", "", "A",100
\t\t\t\tP: "Mute", "bool", "", "",0
\t\t\t\tP: "Solo", "bool", "", "",0
\t\t\t\tP: "Lock", "bool", "", "",0
\t\t\t\tP: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8
\t\t\t\tP: "BlendMode", "enum", "", "",0
\t\t\t\tP: "RotationAccumulationMode", "enum", "", "",0
\t\t\t\tP: "ScaleAccumulationMode", "enum", "", "",0
\t\t\t\tP: "BlendModeBypass", "ULongLong", "", "",0
\t\t\t}}
\t\t}}
\t}}
\tObjectType: "Model" {{
\t\tCount: 1
\t}}
\tObjectType: "Geometry" {{
\t\tCount: 1
\t\tPropertyTemplate: "FbxMesh" {{
\t\t\tProperties70:  {{
\t\t\t\tP: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8
\t\t\t\tP: "BBoxMin", "Vector3D", "Vector", "",0,0,0
\t\t\t\tP: "BBoxMax", "Vector3D", "Vector", "",0,0,0
\t\t\t\tP: "Primary Visibility", "bool", "", "",1
\t\t\t\tP: "Casts Shadows", "bool", "", "",1
\t\t\t\tP: "Receive Shadows", "bool", "", "",1
\t\t\t}}
\t\t}}
\t}}
\tObjectType: "Material" {{
\t\tCount: 1
\t}}
}}

Objects:  {{
\tAnimationStack: 5000, "AnimStack::Take 001", "" {{
\t\tProperties70:  {{
\t\t\tP: "LocalStop", "KTime", "Time", "",153953860000
\t\t\tP: "ReferenceStop", "KTime", "Time", "",153953860000
\t\t}}
\t}}
\tAnimationLayer: 6000, "AnimLayer::BaseLayer", "" {{
\t}}
\tGeometry: 2000, "Geometry::{fbx_name}", "Mesh" {{
\t\tVertices: *{vert_count} {{
\t\t\ta: {vert_str}
\t\t}}
\t\tPolygonVertexIndex: *{poly_count} {{
\t\t\ta: {poly_str}
\t\t}}
\t\tGeometryVersion: 124
\t\tLayerElementNormal: 0 {{
\t\t\tVersion: 101
\t\t\tName: ""
\t\t\tMappingInformationType: "ByPolygonVertex"
\t\t\tReferenceInformationType: "Direct"
\t\t\tNormals: *{normal_count} {{
\t\t\t\ta: {normals_str}
\t\t\t}}
\t\t}}
\t\tLayerElementUV: 0 {{
\t\t\tVersion: 101
\t\t\tName: "UVChannel_1"
\t\t\tMappingInformationType: "ByPolygonVertex"
\t\t\tReferenceInformationType: "IndexToDirect"
\t\t\tUV: *{uv_count} {{
\t\t\t\ta: {uv_str}
\t\t\t}}
\t\t\tUVIndex: *{uvidx_count} {{
\t\t\t\ta: {uvidx_str}
\t\t\t}}
\t\t}}
\t\tLayerElementSmoothing: 0 {{
\t\t\tVersion: 102
\t\t\tName: ""
\t\t\tMappingInformationType: "ByPolygon"
\t\t\tReferenceInformationType: "Direct"
\t\t\tSmoothing: *{smooth_count} {{
\t\t\t\ta: {",".join("0" for _ in range(smooth_count))}
\t\t\t}}
\t\t}}
\t\tLayerElementMaterial: 0 {{
\t\t\tVersion: 101
\t\t\tName: ""
\t\t\tMappingInformationType: "AllSame"
\t\t\tReferenceInformationType: "IndexToDirect"
\t\t\tMaterials: *1 {{
\t\t\t\ta: 0
\t\t\t}}
\t\t}}
\t\tLayer: 0 {{
\t\t\tVersion: 100
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementNormal"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementUV"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementMaterial"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementSmoothing"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t}}
\t}}
\tModel: 3000, "Model::{fbx_name}", "Mesh" {{
\t\tVersion: 232
\t\tProperties70:  {{
\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0
\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",0,0,0
\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0
\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1
\t\t}}
\t\tShading: T
\t\tCulling: "CullingOff"
\t}}
\tMaterial: 4000, "Material::white", "" {{
\t\tVersion: 102
\t\tShadingModel: "phong"
\t\tMultiLayer: 0
\t\tProperties70:  {{
\t\t\tP: "AmbientColor", "Color", "", "A",0,0,0
\t\t\tP: "DiffuseColor", "Color", "", "A",0.941176533699036,0.941176533699036,0.941176533699036
\t\t\tP: "SpecularColor", "Color", "", "A",0.5,0.5,0.5
\t\t\tP: "ShininessExponent", "Number", "", "A",25
\t\t\tP: "ReflectionFactor", "Number", "", "A",0
\t\t}}
\t}}
}}

Connections:  {{
\tC: "OO",3000,0
\tC: "OO",2000,3000
\tC: "OO",4000,3000
\tC: "OO",6000,5000
}}

Takes:  {{
\tCurrent: ""
\tTake: "Take 001" {{
\t\tFileName: "Take_001.tak"
\t\tLocalTime: 0,153953860000
\t\tReferenceTime: 0,153953860000
\t}}
}}
"""
    path = os.path.join(SDK_DIR, "meshes", f"{fbx_name}.fbx")
    with open(path, "w", encoding="utf-8") as f:
        f.write(fbx)
    print(f"  Generated {fbx_name}.fbx ({MESH_SIZE_M} m pentagon)")


def generate_ice_trap_fbx():
    """
    Write arctic_ice_trap.fbx — a trapezoidal slab at MESH_SIZE_M.

    Geometry:
      Wide end  (Z+, north): full ±HALF width
      Narrow end (Z-, south): ±HALF*NARROW width  (NARROW = 0.6)
      8 vertices: 4 top + 4 bevel bottom.  12 triangles.
    """
    HALF   = int(MESH_SIZE_M / 2 * 100)
    BI     = BEVEL_INSET_CM
    BY     = BEVEL_DEPTH_CM
    NARROW = 0.6
    HN     = int(HALF * NARROW)   # narrow half-width
    HNB    = max(1, HN - BI)      # narrow half-width at bevel bottom
    HB     = HALF - BI            # wide half-width at bevel bottom

    # Top vertices (indices 0-3), bottom bevel vertices (indices 4-7)
    all_v = [
        (-HN,  0,   -HALF),   # 0 SW top (narrow end)
        ( HN,  0,   -HALF),   # 1 SE top
        ( HALF, 0,   HALF),   # 2 NE top (wide end)
        (-HALF, 0,   HALF),   # 3 NW top
        (-HNB, BY, -HALF+BI), # 4 SW bot
        ( HNB, BY, -HALF+BI), # 5 SE bot
        ( HB,  BY,   HB),     # 6 NE bot
        (-HB,  BY,   HB),     # 7 NW bot
    ]

    def enc(tris):
        out = []
        for tri in tris:
            out += [tri[0], tri[1], -(tri[2] + 1)]
        return out

    tris = [
        (0, 2, 1),  # top 1
        (0, 3, 2),  # top 2
        (4, 5, 6),  # bottom 1
        (4, 6, 7),  # bottom 2
        (0, 1, 5),  # south 1
        (0, 5, 4),  # south 2
        (1, 2, 6),  # east 1
        (1, 6, 5),  # east 2
        (2, 3, 7),  # north 1
        (2, 7, 6),  # north 2
        (3, 0, 4),  # west 1
        (3, 4, 7),  # west 2
    ]

    # Dynamic normal computation (same helpers as penta)
    def cross3(a, b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

    def norm3(v):
        m = math.sqrt(sum(x*x for x in v))
        return tuple(x / m for x in v) if m > 1e-9 else (0, 1, 0)

    def face_n(tri):
        A, B, C = all_v[tri[0]], all_v[tri[1]], all_v[tri[2]]
        e1 = (B[0]-A[0], B[1]-A[1], B[2]-A[2])
        e2 = (C[0]-A[0], C[1]-A[1], C[2]-A[2])
        return norm3(cross3(e1, e2))

    normals = []
    for tri in tris:
        fn = face_n(tri)
        normals += [fn] * 3

    poly_vals   = enc(tris)
    poly_str    = ",\n\t\t\t".join(str(x) for x in poly_vals)
    poly_count  = len(poly_vals)
    normal_count = len(normals) * 3
    normal_lines = []
    for i, fn in enumerate(normals):
        s = f"{_nfmt(fn[0])},{_nfmt(fn[1])},{_nfmt(fn[2])}"
        normal_lines.append(s + ("," if i < len(normals) - 1 else ""))
    normals_str = "\n\t\t\t\t".join(normal_lines)

    uv_list = []
    for tri in tris:
        for vi in tri:
            vx, _, vz = all_v[vi]
            uv_list.append(((vx + HALF) / (2 * HALF), (vz + HALF) / (2 * HALF)))
    uv_count    = len(uv_list) * 2
    uvidx_count = len(uv_list)
    uv_str      = ",\n\t\t\t\t".join(f"{u:.4f},{v:.4f}" for u, v in uv_list)
    uvidx_str   = ",\n\t\t\t\t".join(str(i) for i in range(uvidx_count))

    smooth_count = len(tris)
    vert_count   = len(all_v) * 3
    vert_str     = ",\n\t\t\t".join(f"{x},{y},{z}" for x, y, z in all_v)

    fbx = f"""; FBX 7.3.0 project file
; Copyright (C) 1997-2010 Autodesk Inc. and/or its licensors.
; All rights reserved.
; ----------------------------------------------------

FBXHeaderExtension:  {{
\tFBXHeaderVersion: 1003
\tFBXVersion: 7300
\tCreationTimeStamp:  {{
\t\tVersion: 1000
\t\tYear: 2024
\t\tMonth: 1
\t\tDay: 1
\t\tHour: 0
\t\tMinute: 0
\t\tSecond: 0
\t\tMillisecond: 0
\t}}
\tCreator: "FBX SDK/FBX Plugins version 2016.0"
\tSceneInfo: "SceneInfo::GlobalInfo", "UserData" {{
\t\tType: "UserData"
\t\tVersion: 100
\t\tMetaData:  {{
\t\t\tVersion: 100
\t\t\tTitle: ""
\t\t\tSubject: ""
\t\t\tAuthor: ""
\t\t\tKeywords: ""
\t\t\tRevision: ""
\t\t\tComment: ""
\t\t}}
\t\tProperties70:  {{
\t\t\tP: "DocumentUrl", "KString", "Url", "", "arctic_ice_trap.fbx"
\t\t\tP: "SrcDocumentUrl", "KString", "Url", "", "arctic_ice_trap.fbx"
\t\t\tP: "Original", "Compound", "", ""
\t\t\tP: "Original|ApplicationVendor", "KString", "", "", "Autodesk"
\t\t\tP: "Original|ApplicationName", "KString", "", "", "3ds Max"
\t\t\tP: "Original|ApplicationVersion", "KString", "", "", "2014"
\t\t\tP: "LastSaved", "Compound", "", ""
\t\t\tP: "LastSaved|ApplicationVendor", "KString", "", "", "Autodesk"
\t\t\tP: "LastSaved|ApplicationName", "KString", "", "", "3ds Max"
\t\t\tP: "LastSaved|ApplicationVersion", "KString", "", "", "2014"
\t\t}}
\t}}
}}
GlobalSettings:  {{
\tVersion: 1000
\tProperties70:  {{
\t\tP: "UpAxis", "int", "Integer", "",1
\t\tP: "UpAxisSign", "int", "Integer", "",1
\t\tP: "FrontAxis", "int", "Integer", "",2
\t\tP: "FrontAxisSign", "int", "Integer", "",1
\t\tP: "CoordAxis", "int", "Integer", "",0
\t\tP: "CoordAxisSign", "int", "Integer", "",1
\t\tP: "OriginalUpAxis", "int", "Integer", "",2
\t\tP: "OriginalUpAxisSign", "int", "Integer", "",1
\t\tP: "UnitScaleFactor", "double", "Number", "",2.54
\t\tP: "OriginalUnitScaleFactor", "double", "Number", "",2.54
\t\tP: "AmbientColor", "ColorRGB", "Color", "",0,0,0
\t\tP: "DefaultCamera", "KString", "", "", "Producer Perspective"
\t\tP: "TimeMode", "enum", "", "",6
\t\tP: "TimeProtocol", "enum", "", "",2
\t\tP: "SnapOnFrameMode", "enum", "", "",0
\t\tP: "TimeSpanStart", "KTime", "Time", "",0
\t\tP: "TimeSpanStop", "KTime", "Time", "",153953860000
\t\tP: "CustomFrameRate", "double", "Number", "",-1
\t\tP: "TimeMarker", "Compound", "", ""
\t\tP: "CurrentTimeMarker", "int", "Integer", "",-1
\t}}
}}

Documents:  {{
\tCount: 1
\tDocument: 1000000, "", "Scene" {{
\t\tProperties70:  {{
\t\t\tP: "SourceObject", "object", "", ""
\t\t\tP: "ActiveAnimStackName", "KString", "", "", ""
\t\t}}
\t\tRootNode: 0
\t}}
}}

References:  {{
}}

Definitions:  {{
\tVersion: 100
\tCount: 5
\tObjectType: "GlobalSettings" {{
\t\tCount: 1
\t}}
\tObjectType: "AnimationStack" {{
\t\tCount: 1
\t\tPropertyTemplate: "FbxAnimStack" {{
\t\t\tProperties70:  {{
\t\t\t\tP: "Description", "KString", "", "", ""
\t\t\t\tP: "LocalStart", "KTime", "Time", "",0
\t\t\t\tP: "LocalStop", "KTime", "Time", "",0
\t\t\t\tP: "ReferenceStart", "KTime", "Time", "",0
\t\t\t\tP: "ReferenceStop", "KTime", "Time", "",0
\t\t\t}}
\t\t}}
\t}}
\tObjectType: "AnimationLayer" {{
\t\tCount: 1
\t\tPropertyTemplate: "FbxAnimLayer" {{
\t\t\tProperties70:  {{
\t\t\t\tP: "Weight", "Number", "", "A",100
\t\t\t\tP: "Mute", "bool", "", "",0
\t\t\t\tP: "Solo", "bool", "", "",0
\t\t\t\tP: "Lock", "bool", "", "",0
\t\t\t\tP: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8
\t\t\t\tP: "BlendMode", "enum", "", "",0
\t\t\t\tP: "RotationAccumulationMode", "enum", "", "",0
\t\t\t\tP: "ScaleAccumulationMode", "enum", "", "",0
\t\t\t\tP: "BlendModeBypass", "ULongLong", "", "",0
\t\t\t}}
\t\t}}
\t}}
\tObjectType: "Model" {{
\t\tCount: 1
\t}}
\tObjectType: "Geometry" {{
\t\tCount: 1
\t\tPropertyTemplate: "FbxMesh" {{
\t\t\tProperties70:  {{
\t\t\t\tP: "Color", "ColorRGB", "Color", "",0.8,0.8,0.8
\t\t\t\tP: "BBoxMin", "Vector3D", "Vector", "",0,0,0
\t\t\t\tP: "BBoxMax", "Vector3D", "Vector", "",0,0,0
\t\t\t\tP: "Primary Visibility", "bool", "", "",1
\t\t\t\tP: "Casts Shadows", "bool", "", "",1
\t\t\t\tP: "Receive Shadows", "bool", "", "",1
\t\t\t}}
\t\t}}
\t}}
\tObjectType: "Material" {{
\t\tCount: 1
\t}}
}}

Objects:  {{
\tAnimationStack: 5000, "AnimStack::Take 001", "" {{
\t\tProperties70:  {{
\t\t\tP: "LocalStop", "KTime", "Time", "",153953860000
\t\t\tP: "ReferenceStop", "KTime", "Time", "",153953860000
\t\t}}
\t}}
\tAnimationLayer: 6000, "AnimLayer::BaseLayer", "" {{
\t}}
\tGeometry: 2000, "Geometry::arctic_ice_trap", "Mesh" {{
\t\tVertices: *{vert_count} {{
\t\t\ta: {vert_str}
\t\t}}
\t\tPolygonVertexIndex: *{poly_count} {{
\t\t\ta: {poly_str}
\t\t}}
\t\tGeometryVersion: 124
\t\tLayerElementNormal: 0 {{
\t\t\tVersion: 101
\t\t\tName: ""
\t\t\tMappingInformationType: "ByPolygonVertex"
\t\t\tReferenceInformationType: "Direct"
\t\t\tNormals: *{normal_count} {{
\t\t\t\ta: {normals_str}
\t\t\t}}
\t\t}}
\t\tLayerElementUV: 0 {{
\t\t\tVersion: 101
\t\t\tName: "UVChannel_1"
\t\t\tMappingInformationType: "ByPolygonVertex"
\t\t\tReferenceInformationType: "IndexToDirect"
\t\t\tUV: *{uv_count} {{
\t\t\t\ta: {uv_str}
\t\t\t}}
\t\t\tUVIndex: *{uvidx_count} {{
\t\t\t\ta: {uvidx_str}
\t\t\t}}
\t\t}}
\t\tLayerElementSmoothing: 0 {{
\t\t\tVersion: 102
\t\t\tName: ""
\t\t\tMappingInformationType: "ByPolygon"
\t\t\tReferenceInformationType: "Direct"
\t\t\tSmoothing: *{smooth_count} {{
\t\t\t\ta: {",".join("0" for _ in range(smooth_count))}
\t\t\t}}
\t\t}}
\t\tLayerElementMaterial: 0 {{
\t\t\tVersion: 101
\t\t\tName: ""
\t\t\tMappingInformationType: "AllSame"
\t\t\tReferenceInformationType: "IndexToDirect"
\t\t\tMaterials: *1 {{
\t\t\t\ta: 0
\t\t\t}}
\t\t}}
\t\tLayer: 0 {{
\t\t\tVersion: 100
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementNormal"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementUV"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementMaterial"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t\tLayerElement:  {{
\t\t\t\tType: "LayerElementSmoothing"
\t\t\t\tTypedIndex: 0
\t\t\t}}
\t\t}}
\t}}
\tModel: 3000, "Model::arctic_ice_trap", "Mesh" {{
\t\tVersion: 232
\t\tProperties70:  {{
\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0
\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",0,0,0
\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0
\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1
\t\t}}
\t\tShading: T
\t\tCulling: "CullingOff"
\t}}
\tMaterial: 4000, "Material::white", "" {{
\t\tVersion: 102
\t\tShadingModel: "phong"
\t\tMultiLayer: 0
\t\tProperties70:  {{
\t\t\tP: "AmbientColor", "Color", "", "A",0,0,0
\t\t\tP: "DiffuseColor", "Color", "", "A",0.941176533699036,0.941176533699036,0.941176533699036
\t\t\tP: "SpecularColor", "Color", "", "A",0.5,0.5,0.5
\t\t\tP: "ShininessExponent", "Number", "", "A",25
\t\t\tP: "ReflectionFactor", "Number", "", "A",0
\t\t}}
\t}}
}}

Connections:  {{
\tC: "OO",3000,0
\tC: "OO",2000,3000
\tC: "OO",4000,3000
\tC: "OO",6000,5000
}}

Takes:  {{
\tCurrent: ""
\tTake: "Take 001" {{
\t\tFileName: "Take_001.tak"
\t\tLocalTime: 0,153953860000
\t\tReferenceTime: 0,153953860000
\t}}
}}
"""
    path = os.path.join(SDK_DIR, "meshes", "arctic_ice_trap.fbx")
    with open(path, "w", encoding="utf-8") as f:
        f.write(fbx)
    print(f"  Generated arctic_ice_trap.fbx ({MESH_SIZE_M} m trapezoid, narrow={int(NARROW*100)}%)")


# ── rotation matrices for Y-axis rotation ─────────────────────────────────────
def rot_matrix(deg):
    """Returns (cos, sin) for a Y-rotation, matching the 4x4 transform layout."""
    r = math.radians(deg)
    return math.cos(r), math.sin(r)

# ── XML helpers ───────────────────────────────────────────────────────────────
def build_transform_str(x, y, z, cos_r, sin_r, jitter_deg, scale=1.0):
    """Build a transform attribute string for inline XML.
    scale multiplies the rotation matrix rows, giving uniform XZ scaling with rotation.
    """
    if jitter_deg != 0:
        cos_r, sin_r = rot_matrix(jitter_deg)
    s_cos = scale * cos_r
    s_sin = scale * sin_r
    parts = []
    if s_cos != 1.0 or s_sin != 0.0:
        parts += [f'00="{s_cos:.6f}"', f'02="{s_sin:.6f}"',
                  f'20="{-s_sin:.6f}"', f'22="{s_cos:.6f}"']
    parts += [f'30="{x}"', f'31="{y}"', f'32="{z}"']
    return " ".join(parts)

def mesh_stamp_xml(stamp_id, mesh_file, x, y, z, cos_r, sin_r, jitter_deg, scale=1.0):
    t = build_transform_str(x, y, z, cos_r, sin_r, jitter_deg, scale)
    return f'\t\t<mesh id="{stamp_id}" file_name="meshes/{mesh_file}.mesh">\n\t\t\t<transform {t}/>\n\t\t</mesh>\n'

def phys_stamp_xml(stamp_id, phys_file, x, y, z, cos_r, sin_r, jitter_deg, scale=1.0):
    t = build_transform_str(x, y, z, cos_r, sin_r, jitter_deg, scale)
    return f'\t\t<physics_mesh id="{stamp_id}" file_name="meshes/{phys_file}.phys">\n\t\t\t<transform {t}/>\n\t\t</physics_mesh>\n'

# ── world tile patcher ────────────────────────────────────────────────────────
def tile_rng(fname):
    """Deterministic per-tile RNG seeded from filename + global seed.
    Ensures each tile always gets the same shape/rotation across rebuilds,
    but different tiles get different variations.
    """
    h = int(hashlib.md5(f"{RANDOM_SEED}:{fname}".encode()).hexdigest(), 16)
    return random.Random(h)


def patch_world_tiles():
    """
    Patch patchable tile types with ice visuals and physics.

    Each tile receives a deterministic random shape at a random rotation
    (0/45/90/135/180/225/270/315°)
    and a micro Y-jitter (±0.1 m) to prevent z-fighting between overlapping
    meshes from adjacent tiles.

    The mesh geometry size is set at build time by MESH_SIZE_M (default 1500 m)
    so the FBX bounding box is correct — no transform scaling.

    PRIMARY tiles (ice_shelf_*, arctic_tile_*, …): arctic-only — safe globally;
    output to tiles/mod/.

    EXTRA tiles (track_*, …): appear in multiple world regions (ice visuals will
    show outside the arctic too); output to tiles/mod_extra/.

    Both categories use per-grid-square physics activation (no radius limit).
    blank.xml ("ocean") is permanently inert and is never patched.

    Originals are backed up to ORIGINAL_DIR (required by disable.bat).  Always
    generated from the backup so repeated runs are idempotent.
    """
    primary_count = 0
    extra_count   = 0

    for fname in sorted(os.listdir(ROM_TILES_DIR)):
        if not fname.endswith(".xml"):
            continue

        is_primary = any(fname.startswith(p) for p in PRIMARY_PREFIXES)
        is_extra   = any(fname.startswith(p) for p in EXTRA_PREFIXES)

        if not is_primary and not is_extra:
            continue

        # Exclusion list: skip specific tiles even if prefix matches
        if fname[:-4] in TILE_EXCLUSIONS:
            continue

        # Per-tile deterministic variation
        rng  = tile_rng(fname)
        roll = rng.random()
        if roll < 0.40:
            mesh_name = "arctic_ice_penta"   # 40% — regular pentagon
        elif roll < 0.70:
            mesh_name = "arctic_ice_penta2"  # 30% — wide pentagon variant
        elif roll < 0.85:
            mesh_name = "arctic_ice_trap"    # 15% — trapezoid
        else:
            mesh_name = "arctic_ice_flat"    # 15% — square slab
        rot_deg   = rng.choice([0, 45, 90, 135, 180, 225, 270, 315])
        cos_r     = math.cos(math.radians(rot_deg))
        sin_r     = math.sin(math.radians(rot_deg))
        y_pos     = ICE_Y + rng.uniform(-0.01, 0.01)  # micro-jitter prevents z-fighting

        phys_s = phys_stamp_xml("flat_ice_phys", mesh_name, 0, y_pos, 0, cos_r, sin_r, 0)
        mesh_s = mesh_stamp_xml("flat_ice_vis",  mesh_name, 0, y_pos, 0, cos_r, sin_r, 0)

        rom_path  = os.path.join(ROM_TILES_DIR, fname)
        orig_path = os.path.join(ORIGINAL_DIR, fname)
        out_path  = os.path.join(OUTPUT_DIR if is_primary else EXTRA_OUTPUT_DIR, fname)

        # Bootstrap: copy from ROM the first time we see this file.
        if not os.path.exists(orig_path):
            shutil.copy(rom_path, orig_path)

        with open(orig_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        # ── Physics stamp ──────────────────────────────────────────────────────
        if "</physics_meshes>" in content:
            content = content.replace(
                "</physics_meshes>",
                phys_s + "\t</physics_meshes>",
                1,
            )
        elif "<physics_meshes/>" in content:
            content = content.replace(
                "<physics_meshes/>",
                f"<physics_meshes>\n{phys_s}\t</physics_meshes>",
            )
        else:
            print(f"  WARNING: no physics_meshes tag in {fname}, skipping")
            continue

        # ── Visual mesh stamp ──────────────────────────────────────────────────
        if "</meshes>" in content:
            content = content.replace(
                "</meshes>",
                mesh_s + "\t</meshes>",
                1,
            )
        elif "<meshes/>" in content:
            content = content.replace(
                "<meshes/>",
                f"<meshes>\n{mesh_s}\t</meshes>",
            )
        else:
            print(f"  WARNING: no meshes tag in {fname}, visual skipped")

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        if is_primary:
            primary_count += 1
        else:
            extra_count += 1

    print(f"  Primary tiles (visual + physics): {primary_count}")
    print(f"  Extra tiles  (visual + physics):  {extra_count}")
    return primary_count + extra_count


# ── main ──────────────────────────────────────────────────────────────────────
def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(EXTRA_OUTPUT_DIR, exist_ok=True)
    os.makedirs(ORIGINAL_DIR, exist_ok=True)

    # Copy all original tiles to mod output (unmodified baseline).
    # Source from ROM so this works on first run before ORIGINAL_DIR is populated.
    # Only bootstrap tiles that belong in the mod (primary, extra, or blank.xml).
    for fname in os.listdir(ROM_TILES_DIR):
        if not fname.endswith(".xml"):
            continue
        is_primary = any(fname.startswith(p) for p in PRIMARY_PREFIXES)
        if not (is_primary or fname == "blank.xml"):
            continue
        orig_path = os.path.join(ORIGINAL_DIR, fname)
        if not os.path.exists(orig_path):
            shutil.copy(os.path.join(ROM_TILES_DIR, fname), orig_path)
        shutil.copy(orig_path, os.path.join(OUTPUT_DIR, fname))

    # ── World tile patches ────────────────────────────────────────────────────
    # PRIMARY tiles (ice_shelf_*) → tiles/mod/       visual + physics
    # EXTRA tiles (track_*, …)   → tiles/mod_extra/  physics only
    # enable.bat lets the user choose whether to apply extra tiles.
    print(f"\nPatching world tiles...")
    patch_world_tiles()
    print(f"  Primary output: {OUTPUT_DIR}")
    print(f"  Extra output:   {EXTRA_OUTPUT_DIR}")

    print(f"\nDone.")
    print(f"Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    import sys
    if "--fbx-only" in sys.argv:
        generate_ice_flat_fbx()
        generate_ice_penta_fbx()
        generate_ice_penta_fbx(fbx_name="arctic_ice_penta2", bearings=[0, 80, 155, 230, 300])
        generate_ice_trap_fbx()
    else:
        generate()
