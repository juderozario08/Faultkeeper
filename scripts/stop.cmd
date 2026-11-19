@echo off
rem Windows: stop everything. Option: -WipeData
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
