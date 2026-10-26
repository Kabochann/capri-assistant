@echo off
chcp 65001 >nul
if not exist .venv (
  echo Rode o setup_windows.bat primeiro.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat

python -c "import requests, numpy, sounddevice, faster_whisper, edge_tts, pygame, PIL" >nul 2>nul
if errorlevel 1 (
  echo Faltam bibliotecas no ambiente. Rode o setup_windows.bat de novo
  echo e confira se ele termina sem erros em vermelho.
  pause
  exit /b 1
)

rem Deixa o Whisper achar as DLLs CUDA instaladas via pip (se existirem)
for /d %%D in (.venv\Lib\site-packages\nvidia\*) do set "PATH=%CD%\%%D\bin;%PATH%"

python -m capri %*
if errorlevel 1 pause
