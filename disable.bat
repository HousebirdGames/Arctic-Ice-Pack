@echo off
setlocal

set MOD_DIR=%~dp0
set ROM_DIR=%MOD_DIR%..\..\rom

echo === Arctic Ice Pack - DISABLE ===
echo.

REM Remove mod mesh files from ROM
echo Removing meshes...
del /Q "%ROM_DIR%\meshes\arctic_ice_flat.mesh"   2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_flat.phys"   2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_penta.mesh"  2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_penta.phys"  2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_penta2.mesh" 2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_penta2.phys" 2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_trap.mesh"   2>nul
del /Q "%ROM_DIR%\meshes\arctic_ice_trap.phys"   2>nul

REM Restore original tile XMLs from backup
echo Restoring original tiles...
for %%f in ("%MOD_DIR%tiles\original\*.xml") do (
    copy /Y "%%f" "%ROM_DIR%\data\tiles\%%~nxf" >nul
    echo   %%~nxf
)

echo.
echo Mod DISABLED. Original arctic tiles restored.
if /i not "%~1"=="silent" pause
