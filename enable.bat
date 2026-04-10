@echo off
setlocal

set MOD_DIR=%~dp0
set ROM_DIR=%MOD_DIR%..\..\rom

echo === Arctic Ice Pack - ENABLE ===
echo.

REM Always restore originals first so stale stamps from a previous build are gone
call "%MOD_DIR%disable.bat" silent >nul 2>&1
echo.

REM Check that mod tiles exist
if not exist "%MOD_DIR%tiles\mod\arctic_tile_22.xml" (
    echo ERROR: Mod tiles not found. Run build.bat first.
    pause
    exit /b 1
)

REM Copy mesh files to ROM
echo Copying meshes...
copy /Y "%MOD_DIR%meshes\arctic_ice_flat.mesh" "%ROM_DIR%\meshes\arctic_ice_flat.mesh" >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_flat.phys" "%ROM_DIR%\meshes\arctic_ice_flat.phys" >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta.mesh"  "%ROM_DIR%\meshes\arctic_ice_penta.mesh"  >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta.phys"  "%ROM_DIR%\meshes\arctic_ice_penta.phys"  >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta2.mesh" "%ROM_DIR%\meshes\arctic_ice_penta2.mesh" >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_penta2.phys" "%ROM_DIR%\meshes\arctic_ice_penta2.phys" >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_trap.mesh"   "%ROM_DIR%\meshes\arctic_ice_trap.mesh"   >nul
copy /Y "%MOD_DIR%meshes\arctic_ice_trap.phys"   "%ROM_DIR%\meshes\arctic_ice_trap.phys"   >nul

REM Copy primary mod tiles (ice_shelf + arctic — visual + physics)
echo.
echo Copying primary tiles (ice_shelf + arctic)...
for %%f in ("%MOD_DIR%tiles\mod\*.xml") do (
    copy /Y "%%f" "%ROM_DIR%\data\tiles\%%~nxf" >nul
    echo   %%~nxf
)

REM Ask about extra tiles (track, island — physics only)
echo.
echo Extra tiles add more tiles increasing the ice coverage by including
echo common tiles (i.e. rails) – but this means there will also be ice in
echo the other regions of the game
echo.
set /p EXTRA=Include extra tiles? (Y/N, default N):

if /i "%EXTRA%"=="Y" (
    if not exist "%MOD_DIR%tiles\mod_extra\" (
        echo WARNING: mod_extra folder not found. Run build.bat first.
    ) else (
        echo.
        echo Copying extra tiles...
        for %%f in ("%MOD_DIR%tiles\mod_extra\*.xml") do (
            copy /Y "%%f" "%ROM_DIR%\data\tiles\%%~nxf" >nul
            echo   %%~nxf
        )
    )
) else (
    echo Skipping extra tiles.
)

echo.
echo Mod ENABLED. Start Stormworks to see the ice sheet.
pause
