@echo off
setlocal

cd /d "%~dp0"
set "CONDA_CMD="

rem Obtiene conda.bat desde el PATH del usuario.
for /f "delims=" %%P in ('where conda 2^>nul') do if not defined CONDA_CMD set "CONDA_CMD=%%P"

if not defined CONDA_CMD (
    echo No se encontro "conda" en el PATH de este usuario.
    echo Agregue la carpeta "condabin" de Anaconda al PATH de las variables del usuario.
    pause
    exit /b 1
)

echo Activando el entorno base de Conda...
call "%CONDA_CMD%" activate base
if errorlevel 1 (
    echo No fue posible activar el entorno base de Conda.
    pause
    exit /b 1
)

echo.
echo Iniciando el validador...
python cli.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
pause
exit /b %EXIT_CODE%
