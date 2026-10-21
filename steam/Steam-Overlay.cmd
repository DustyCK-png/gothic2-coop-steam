@echo off
cd /d "%~dp0SteamLink"
G2Steam.exe overlay --host-saves --game "%~dp0."
pause
