@echo off
chcp 65001 >nul
echo === Instalando a Capri Assistant ===
echo Pasta de instalacao: %CD%
echo Tudo que for pesado sera guardado dentro desta pasta (nao no disco C).
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.11 ou 3.12 em https://www.python.org/downloads/
  echo Marque a opcao "Add Python to PATH" na instalacao.
  pause
  exit /b 1
)

rem Cache do pip dentro da pasta do projeto, para nao encher o disco C
set "PIP_CACHE_DIR=%CD%\.pipcache"

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
  echo Dica: para instalar o Ollama em outro disco, rode no Prompt de Comando:
  echo    OllamaSetup.exe /DIR="G:\Ollama"
  pause
  exit /b 1
)

rem Os modelos do Ollama normalmente vao para o disco C. Aqui mandamos para esta pasta.
if not defined OLLAMA_MODELS (
  setx OLLAMA_MODELS "%CD%\ollama_models" >nul
  echo.
  echo Configurei os modelos do Ollama para ficarem em: %CD%\ollama_models
  echo AGORA: feche o Ollama ^(icone perto do relogio -^> Quit^), abra de novo
  echo e rode este setup_windows.bat mais uma vez para baixar o modelo.
  pause
  exit /b 0
)

echo Baixando o modelo de linguagem (cerca de 5 GB, so na primeira vez)...
echo Destino: %OLLAMA_MODELS%
ollama pull qwen2.5:7b-instruct

echo.
echo Tudo pronto! Use o run.bat para abrir a Capri.
pause
