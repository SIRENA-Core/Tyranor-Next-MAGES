@echo off
rem Build bink2dump.exe (32-bit, the game's bink2w32.dll is 32-bit) with the Visual Studio Build Tools.
call "C:\Program Files (x86)\Microsoft Visual Studio‚2\BuildTools\VC\Auxiliary\Buildcvars32.bat" >nul
cd /d "%~dp0"
cl /nologo /O2 /W3 bink2dump.c /Fe:bink2dump.exe
