@echo off
chcp 65001 >nul
echo === Instalando a Capri Assistant ===

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.11 ou 3.12 em https://www.python.org/downloads/
  echo Marque a opcao "Add Python to PATH" na instalacao.
  pause
  exit /b 1
)

if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
set /p GPU="Instalar bibliotecas CUDA para o reconhecimento de voz na placa de video? (s/n): "
if /i "%GPU%"=="s" pip install -r requirements-gpu.txt

echo.
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama nao encontrado. Instale em https://ollama.com/download e rode este script de novo.
  pause
  exit /b 1
)
echo Baixando o modelo de linguagem (cerca de 5 GB, so na primeira vez)...
ollama pull qwen2.5:7b-instruct

echo.
echo Tudo pronto! Use o run.bat para abrir a Capri.
pause
