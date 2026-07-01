@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  UTNS2 TTS -> KML  (single stitched Finland map)
REM  Finds the TTS save in this folder, runs the converter, and
REM  copies the generated KML to the repo root + an archive folder.
REM ============================================================

REM --- Find the save file (first *.json in this folder) ---
set "SAVE_FILE="
for %%F in (*.json) do (
    if not defined SAVE_FILE set "SAVE_FILE=%%F"
)
if not defined SAVE_FILE (
    echo No JSON save files found in this folder!
    pause
    exit /b 1
)
echo Found save file: %SAVE_FILE%

REM --- Prompt for archive folder name ---
echo.
set /p ARCHIVE_NAME=Enter archive folder name (e.g., GT3): 
if "%ARCHIVE_NAME%"=="" (
    echo No archive folder name provided. Exiting.
    pause
    exit /b 1
)
set "ARCHIVE_DIR=Archived KML's\%ARCHIVE_NAME%"
echo Archive folder will be: "%ARCHIVE_DIR%"
mkdir "%ARCHIVE_DIR%" 2>nul

REM --- Prompt for unit filters ---
echo.
set "FILTER_FLAGS="
set /p SHOW_RUSSIA=Show Russian units? (Y/N) [N]: 
if /I not "%SHOW_RUSSIA%"=="Y" set "FILTER_FLAGS=%FILTER_FLAGS% --hide-russia"
set /p SHOW_HIDDEN=Show units tagged "HIDDEN"? (Y/N) [N]: 
if /I not "%SHOW_HIDDEN%"=="Y" set "FILTER_FLAGS=%FILTER_FLAGS% --hide-hidden"

REM --- Stage the save into the pipeline folder ---
echo Copying save file to TTS2KML...
copy /Y "%SAVE_FILE%" "TTS2KML\" >nul

REM --- Clean any previously generated KMLs (keep Sample*) ---
for %%F in ("TTS2KML\*.kml") do (
    if /I not "%%~nF"=="SampleScenario" del "%%~fF"
)

REM --- Run the converter ---
echo Processing map...
cd TTS2KML
python tts2kml.py "%SAVE_FILE%"!FILTER_FLAGS!
if errorlevel 1 (
    echo Error processing map
    cd ..
    goto :error
)
cd ..

REM --- Collect the generated KML (name derived from SaveName) ---
set "KML_SOURCE="
for %%F in ("TTS2KML\*.kml") do (
    if /I not "%%~nF"=="SampleScenario" set "KML_SOURCE=%%~fF"
)
if not defined KML_SOURCE (
    echo Warning: No KML file was generated.
    goto :error
)
for %%F in ("!KML_SOURCE!") do set "KML_NAME=%%~nxF"

REM --- Copy to repo root and archive ---
copy /Y "!KML_SOURCE!" "!KML_NAME!" >nul
call :TrimKml "!KML_NAME!"
copy /Y "!KML_NAME!" "%ARCHIVE_DIR%\!KML_NAME!" >nul
copy /Y "%SAVE_FILE%" "%ARCHIVE_DIR%\%SAVE_FILE%" >nul

REM --- Cleanup staged copies ---
del "TTS2KML\%SAVE_FILE%" 2>nul
for %%F in ("TTS2KML\*.kml") do (
    if /I not "%%~nF"=="SampleScenario" del "%%~fF"
)

echo.
echo Done! Generated "!KML_NAME!" (also archived in "%ARCHIVE_DIR%").
pause
exit /b 0

:TrimKml
if exist "%~1" (
    python -c "from pathlib import Path; p = Path(r'%~f1'); p.write_bytes(p.read_bytes().rstrip(b'\r\n\t '))"
)
exit /b

:error
echo Script failed!
pause
exit /b 1