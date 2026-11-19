@echo off
rem Windows: run the full CI pipeline locally. Options: -Quick -InstallHook
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check.ps1" %*
