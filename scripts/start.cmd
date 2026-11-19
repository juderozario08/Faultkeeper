@echo off
rem Windows launcher (double-click or run from cmd/PowerShell). Options: -Ai -Reset -NoOpen
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
