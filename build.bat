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
echo [4/5] Generating tile XMLs...
cd /d "%MOD_DIR%"
python src\generate_tiles.py
if errorlevel 1 ( echo ERROR running generate_tiles.py & pause & exit /b 1 )

REM Step 5: Update standalone mod folder
echo [5/5] Updating standalone mod...

REM Bump build number in mod.xml
set MOD_XML=%MOD_DIR%mod\arctic_ice_pack\mod.xml
python -c "import re; p=r'%MOD_XML%'; t=open(p).read(); m=re.search(r'Build (\d+)', t); n=int(m.group(1))+1 if m else 1; open(p,'w').write(re.sub(r'Build \d+', 'Build '+str(n), t)); print('  Build number ->', n)"
if errorlevel 1 ( echo ERROR bumping build number & pause & exit /b 1 )

REM Create standalone mod subfolders if needed
if not exist "%MOD_DIR%mod\arctic_ice_pack\data\tiles\" mkdir "%MOD_DIR%mod\arctic_ice_pack\data\tiles"
if not exist "%MOD_DIR%mod\arctic_ice_pack\meshes\"     mkdir "%MOD_DIR%mod\arctic_ice_pack\meshes"

REM Copy tiles to standalone mod
xcopy /Y /Q "%MOD_DIR%tiles\mod\*.xml" "%MOD_DIR%mod\arctic_ice_pack\data\tiles\" >nul
if errorlevel 1 ( echo ERROR copying tiles to standalone mod & pause & exit /b 1 )
echo   Tiles copied.

REM Copy meshes to standalone mod
copy /Y "%MOD_DIR%meshes\arctic_ice_flat.mesh"   "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_flat.mesh"   >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_flat.phys"   "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_flat.phys"   >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta.mesh"  "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_penta.mesh"  >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta.phys"  "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_penta.phys"  >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta2.mesh" "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_penta2.mesh" >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta2.phys" "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_penta2.phys" >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_trap.mesh"   "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_trap.mesh"   >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_trap.phys"   "%MOD_DIR%mod\arctic_ice_pack\meshes\arctic_ice_trap.phys"   >nul
echo   Meshes copied.

echo.
echo Build complete. Run enable.bat to apply the mod.
pause
