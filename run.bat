@echo off
chcp 65001 >nul
if not exist .venv (
  echo Rode o setup_windows.bat primeiro.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat

rem Deixa o Whisper achar as DLLs CUDA instaladas via pip (se existirem)
for /d %%D in (.venv\Lib\site-packages\nvidia\*) do set "PATH=%CD%\%%D\bin;%PATH%"

python -m capri %*
if errorlevel 1 pause
