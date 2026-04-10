@echo off
setlocal

set MOD_DIR=%~dp0
set SDK_DIR=%MOD_DIR%..\..\sdk

echo === Arctic Ice Pack - BUILD ===
echo.
echo Grid size, visual scale, and ice height are set in src\config.json.
echo.

REM Step 1a: Generate FBX files (must run before compiler so sizes are correct)
echo [1/4] Generating FBX meshes from config...
cd /d "%MOD_DIR%"
python src\generate_tiles.py --fbx-only
if errorlevel 1 ( echo ERROR generating FBX & pause & exit /b 1 )

REM Step 1b: Compile FBX meshes
echo [2/4] Compiling meshes...
cd /d "%SDK_DIR%"

call mesh_compiler.com meshes\arctic_ice_flat.fbx
if errorlevel 1 ( echo ERROR compiling arctic_ice_flat & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_flat.fbx -m physics_mesh
if errorlevel 1 ( echo ERROR compiling arctic_ice_flat phys & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_penta.fbx
if errorlevel 1 ( echo ERROR compiling arctic_ice_penta & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_penta.fbx -m physics_mesh
if errorlevel 1 ( echo ERROR compiling arctic_ice_penta phys & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_penta2.fbx
if errorlevel 1 ( echo ERROR compiling arctic_ice_penta2 & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_penta2.fbx -m physics_mesh
if errorlevel 1 ( echo ERROR compiling arctic_ice_penta2 phys & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_trap.fbx
if errorlevel 1 ( echo ERROR compiling arctic_ice_trap & pause & exit /b 1 )

call mesh_compiler.com meshes\arctic_ice_trap.fbx -m physics_mesh
if errorlevel 1 ( echo ERROR compiling arctic_ice_trap phys & pause & exit /b 1 )

REM Step 3: Copy compiled meshes to mod folder
echo [3/4] Copying meshes to mod...
if not exist "%MOD_DIR%meshes\" mkdir "%MOD_DIR%meshes"
copy /Y "output\arctic_ice_flat.mesh" "%MOD_DIR%meshes\arctic_ice_flat.mesh" >nul
copy /Y "output\arctic_ice_flat.phys" "%MOD_DIR%meshes\arctic_ice_flat.phys" >nul
copy /Y "output\arctic_ice_penta.mesh"  "%MOD_DIR%meshes\arctic_ice_penta.mesh"  >nul
copy /Y "output\arctic_ice_penta.phys"  "%MOD_DIR%meshes\arctic_ice_penta.phys"  >nul
copy /Y "output\arctic_ice_penta2.mesh" "%MOD_DIR%meshes\arctic_ice_penta2.mesh" >nul
copy /Y "output\arctic_ice_penta2.phys" "%MOD_DIR%meshes\arctic_ice_penta2.phys" >nul
copy /Y "output\arctic_ice_trap.mesh"   "%MOD_DIR%meshes\arctic_ice_trap.mesh"   >nul
copy /Y "output\arctic_ice_trap.phys"   "%MOD_DIR%meshes\arctic_ice_trap.phys"   >nul

REM Step 4: Generate tile XMLs
echo [4/4] Generating tile XMLs...
cd /d "%MOD_DIR%"
python src\generate_tiles.py
if errorlevel 1 ( echo ERROR running generate_tiles.py & pause & exit /b 1 )

echo.
echo Build complete. Run enable.bat to apply the mod.
pause
