@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0" || exit /b 1

set "DS2_CONFIG=Release"
if not "%~1"=="" set "DS2_CONFIG=%~1"
if /I "%DS2_CONFIG%"=="Release" goto release
if /I "%DS2_CONFIG%"=="Debug" goto debug
echo Usage: do_build.bat [Release^|Debug]
exit /b 1

:release
set "DS2_CONFIG=Release"
set "DS2_CFLAGS=/O2 /MT /DNDEBUG"
goto toolchain

:debug
set "DS2_CONFIG=Debug"
set "DS2_CFLAGS=/Od /MTd /D_DEBUG"

:toolchain
set "DS2_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%DS2_VSWHERE%" (
    echo ERROR: vswhere.exe was not found. Install Visual Studio C++ build tools.
    exit /b 1
)
set "DS2_VS_PATH="
for /f "usebackq delims=" %%I in (`"%DS2_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "DS2_VS_PATH=%%I"
if not defined DS2_VS_PATH (
    echo ERROR: No Visual Studio installation with x64/x86 C++ tools was found.
    echo Open Visual Studio Installer and add Desktop development with C++ and a Windows SDK.
    exit /b 1
)
if not exist "%DS2_VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" (
    echo ERROR: vcvars64.bat was not found in "%DS2_VS_PATH%".
    exit /b 1
)
echo Visual Studio: %DS2_VS_PATH%
call "%DS2_VS_PATH%\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1

set "DS2_OUTPUT=build\%DS2_CONFIG%"
if not exist "%DS2_OUTPUT%" mkdir "%DS2_OUTPUT%"
if not exist "%DS2_OUTPUT%" exit /b 1

echo Building DS2NoSlowMo ^(%DS2_CONFIG%, x64^)...
cl /nologo /std:c++17 /EHsc /permissive- /utf-8 /W4 /WX /Zi %DS2_CFLAGS% /DWIN32_LEAN_AND_MEAN /DNOMINMAX /LD src\ds2_no_slowmo.cpp /Fo"%DS2_OUTPUT%\ds2_no_slowmo.obj" /Fd"%DS2_OUTPUT%\compiler.pdb" /Fe"%DS2_OUTPUT%\DS2NoSlowMo.asi" /link /MACHINE:X64 /INCREMENTAL:NO /DEBUG:FULL /OPT:REF /OPT:ICF /PDB:"%DS2_OUTPUT%\DS2NoSlowMo.pdb" /IMPLIB:"%DS2_OUTPUT%\DS2NoSlowMo.lib"
if errorlevel 1 (
    echo ERROR: Build failed.
    exit /b 1
)
echo Built: %CD%\%DS2_OUTPUT%\DS2NoSlowMo.asi
exit /b 0
