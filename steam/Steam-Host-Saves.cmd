@echo off
cd /d "%~dp0SteamLink"
G2Steam.exe host --host-saves --game "%~dp0."
pause
