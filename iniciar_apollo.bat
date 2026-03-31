@echo off
:: ============================================================
::  VISU Dados — iniciar_apollo.bat
::  Duplo-clique para executar a extração do Apollo.io.
::  Instala o ambiente automaticamente se necessário.
:: ============================================================
SETLOCAL ENABLEDELAYEDEXPANSION
title VISU — Apollo Extractor

echo.
echo  ====================================================
echo   VISU Dados — Apollo Sequences Extractor
echo  ====================================================
echo.
timeout /t 2 /nobreak >nul

:: ── O bat está na raiz do repositório.
:: ── O pyproject.toml e os scripts ficam em /python.
:: ── Todas as operações do uv rodam de dentro de /python.
SET "SCRIPT_DIR=%~dp0"
SET "PYTHON_DIR=%SCRIPT_DIR%python"

IF NOT EXIST "%PYTHON_DIR%\pyproject.toml" (
    echo  [ERRO] Pasta "python" ou pyproject.toml nao encontrado.
    echo  Certifique-se de que iniciar_apollo.bat esta na raiz do repositorio.
    echo.
    pause
    exit /b 1
)

:: ── PASSO 1: Instalar uv se ausente ───────────────────────────
where uv >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo  [1/3] uv nao encontrado. Instalando...
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    IF !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [ERRO] Falha ao instalar o uv.
        echo  Verifique sua conexao com a internet e tente novamente.
        echo.
        pause
        exit /b 1
    )
    :: Recarrega o PATH para encontrar o uv recém-instalado
    SET "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"

    where uv >nul 2>&1
    IF !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [AVISO] uv instalado mas nao encontrado no PATH ainda.
        echo  Feche este terminal, abra um novo e execute iniciar_apollo.bat novamente.
        echo.
        pause
        exit /b 1
    )
    echo  [1/3] uv instalado com sucesso.
) ELSE (
    echo  [1/3] uv OK.
)
timeout /t 2 /nobreak >nul

:: ── PASSO 2: Instalar dependencias Python ─────────────────────
echo  [2/3] Verificando dependencias Python...
cd /d "%PYTHON_DIR%"

uv sync
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Falha ao instalar dependencias.
    echo  Verifique sua conexao com a internet e tente novamente.
    echo.
    pause
    exit /b 1
)
echo  [2/3] Dependencias OK.
timeout /t 2 /nobreak >nul

:: ── PASSO 3: Executar a automação ─────────────────────────────
echo  [3/3] Executando Apollo Extractor...
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
