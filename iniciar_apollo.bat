@echo off
:: ============================================================
::  VISU Dados — iniciar_apollo.bat
::  Duplo-clique para executar a extração do Apollo.io.
::  Verifica e instala o ambiente automaticamente se necessário.
:: ============================================================
SETLOCAL ENABLEDELAYEDEXPANSION
title VISU — Apollo Extractor

echo.
echo  ====================================================
echo   VISU Dados — Apollo Sequences Extractor
echo  ====================================================
echo.
timeout /t 2 /nobreak >nul

:: Define caminhos base a partir da localização do próprio .bat
SET "SCRIPT_DIR=%~dp0"
SET "PYTHON_DIR=%SCRIPT_DIR%python"
SET "VENV_DIR=%PYTHON_DIR%\.venv"

IF NOT EXIST "%PYTHON_DIR%\pyproject.toml" (
    echo  [ERRO] Pasta "python" ou pyproject.toml nao encontrado.
    echo  Certifique-se de que iniciar_apollo.bat esta na raiz do repositorio.
    echo.
    pause
    exit /b 1
)

:: ── PASSO 1: Verificar uv ─────────────────────────────────────
echo  [1/4] Verificando gerenciador de ambiente (uv)...
where uv >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo         uv nao encontrado. Instalando automaticamente...
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    IF !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [ERRO] Falha ao instalar o uv.
        echo  Verifique sua conexao com a internet e tente novamente.
        echo.
        pause
        exit /b 1
    )
    SET "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
    where uv >nul 2>&1
    IF !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [AVISO] uv instalado mas ainda nao visivel neste terminal.
        echo  Feche esta janela, abra uma nova e execute iniciar_apollo.bat novamente.
        echo.
        pause
        exit /b 1
    )
    echo  [1/4] uv instalado com sucesso.
) ELSE (
    echo  [1/4] uv: OK
)
timeout /t 2 /nobreak >nul

:: ── PASSO 2: Verificar ambiente virtual (.venv) ───────────────
echo  [2/4] Verificando ambiente virtual Python (.venv)...
cd /d "%PYTHON_DIR%"

IF EXIST "%VENV_DIR%" (
    echo  [2/4] Ambiente virtual: JA EXISTE em python\.venv
) ELSE (
    echo         Ambiente virtual nao encontrado. Criando...
    uv sync
    IF !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [ERRO] Falha ao criar o ambiente virtual.
        echo  Verifique sua conexao com a internet e tente novamente.
        echo.
        pause
        exit /b 1
    )
    echo  [2/4] Ambiente virtual criado com sucesso em python\.venv
)
timeout /t 2 /nobreak >nul

:: ── PASSO 3: Sincronizar dependencias ─────────────────────────
:: Roda sempre — detecta mudancas no pyproject.toml automaticamente.
:: Se nada mudou, termina em milissegundos sem baixar nada.
echo  [3/4] Verificando dependencias Python...
uv sync
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Falha ao sincronizar dependencias.
    echo  Verifique sua conexao com a internet e tente novamente.
    echo.
    pause
    exit /b 1
)
echo  [3/4] Dependencias: OK
timeout /t 2 /nobreak >nul

:: ── PASSO 4: Executar a automacao ─────────────────────────────
echo  [4/4] Iniciando Apollo Extractor...
echo.

uv run python projects\run_apollo_extractor.py
SET RESULT=%ERRORLEVEL%

echo.
IF %RESULT% EQU 0 (
    echo  ====================================================
    echo   Concluido com sucesso!
    echo   O CSV foi salvo na pasta Downloads do Windows
    echo   (ou no caminho configurado em run_apollo_extractor.py).
    echo  ====================================================
    echo.
    timeout /t 5 /nobreak >nul
) ELSE (
    echo  ====================================================
    echo   Ocorreu um erro durante a execucao.
    echo.
    echo   Arquivos de diagnostico (pasta python\projects):
    echo     apollo_sequences_extract.log
    echo     erro_*.png  (screenshot do momento do erro)
    echo  ====================================================
    echo.
    pause
)

ENDLOCAL
