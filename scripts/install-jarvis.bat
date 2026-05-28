@echo off
chcp 65001 >nul
title JARVIS - Restauration / Verification (DR)
setlocal

:: ============================================================
::  Point d'entree ERGONOMIQUE de la DR JARVIS depuis le coffre.
::  install-jarvis.ps1 n'est PAS un menu (il se ferme apres exec).
::  Ce .bat fournit un menu clair + garde la fenetre ouverte (pause)
::  + gere l'elevation admin pour la restauration reelle.
::  Apres une reinstall Windows : double-clic sur ce .bat depuis le coffre
::  (D:\BACKUP-WINDOWS\JARVIS\scripts\install-jarvis.bat).
:: ============================================================

set "SCRIPT=%~dp0install-jarvis.ps1"

if not exist "%SCRIPT%" (
    echo.
    echo   [XX] install-jarvis.ps1 introuvable a cote de ce .bat
    echo        attendu : %SCRIPT%
    echo.
    pause
    exit /b 1
)

:menu
cls
echo.
echo   ==================================================
echo      JARVIS  --  Restauration / Verification  (DR)
echo   ==================================================
echo.
echo     [1]  Verifier le coffre        (simulation, sans admin)
echo     [2]  Simuler la restauration   (etapes 0 a 8, sans admin)
echo     [3]  RESTAURATION REELLE       (admin - apres reinstall Windows)
echo     [Q]  Quitter
echo.
set /p "choix=  Choix : "

if /i "%choix%"=="1" goto dryrun
if /i "%choix%"=="2" goto simrestore
if /i "%choix%"=="3" goto restore
if /i "%choix%"=="Q" goto fin
goto menu

:dryrun
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -DryRun
echo.
pause
goto menu

:simrestore
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -DryRunRestore
echo.
pause
goto menu

:restore
echo.
echo   /!\ RESTAURATION REELLE : reinstalle TOUTE la stack JARVIS
echo       (pilote NVIDIA, Python, Ollama, PyTorch, JARVIS, modeles, raccourcis).
echo       A lancer UNIQUEMENT apres une reinstallation Windows.
echo.
set /p "confirm=  Taper OUI en majuscules pour confirmer : "
if /i not "%confirm%"=="OUI" (
    echo   Annule.
    timeout /t 2 >nul
    goto menu
)
echo.
echo   Lancement avec elevation administrateur (cliquer OUI sur la fenetre UAC)...
powershell -NoProfile -Command "Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','%SCRIPT%','-Unattended'"
echo.
echo   La restauration tourne dans une fenetre administrateur dediee.
pause
goto menu

:fin
endlocal
exit /b 0
