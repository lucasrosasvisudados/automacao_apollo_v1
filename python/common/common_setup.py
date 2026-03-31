# -------------------------------------------------------------------------
# common_setup.py - VISU Dados
# -------------------------------------------------------------------------
# Módulo de verificação e configuração inicial do ambiente de automação.
#
# Responsabilidades:
#   1. Verificar se o perfil Chrome da VISU existe e tem sessão ativa
#   2. Se não houver perfil ou sessão, abrir o Chrome e guiar o login
#      manual do usuário no Apollo.io via Google
#   3. Confirmar que a sessão foi estabelecida antes de prosseguir
#
# Quando usar:
#   Chamado automaticamente no início de qualquer script de extração.
#   Garante que a automação não tente rodar sem autenticação válida,
#   especialmente em máquinas novas ou após limpeza de armazenamento.
# -------------------------------------------------------------------------

import os
import time
import logging
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.common_browser import CAMINHO_PERFIL_VISU

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# -------------------------------------------------------------------------
# Configuração de logging
# -------------------------------------------------------------------------
log = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Constantes
# -------------------------------------------------------------------------
URL_APOLLO_LOGIN  = "https://app.apollo.io/#/login"
URL_APOLLO_HOME   = "https://app.apollo.io"

# Arquivo de cookie que o Google OAuth salva após login bem-sucedido.
# Sua presença indica que o perfil tem uma sessão registrada.
COOKIE_FILE_RELATIVO = Path("Default") / "Cookies"


# -------------------------------------------------------------------------
# Verificação do perfil
# -------------------------------------------------------------------------

# Verifica se a pasta do perfil Chrome existe e contém dados de sessão.
def perfil_existe(caminho_perfil: Path) -> bool:
    """
    Retorna True se a pasta do perfil existe e contém o arquivo de cookies,
    indicando que houve pelo menos um login anterior neste perfil.

    A presença do arquivo Cookies não garante que a sessão ainda é válida
    (pode ter expirado), mas garante que o perfil foi configurado pelo menos
    uma vez. A validação da sessão ativa é feita por sessao_ativa().
    """
    cookies_path = caminho_perfil / COOKIE_FILE_RELATIVO
    existe = caminho_perfil.exists() and cookies_path.exists()
    if existe:
        log.info(f"[SETUP] Perfil Chrome encontrado em: {caminho_perfil}")
    else:
        log.warning(f"[SETUP] Perfil Chrome NÃO encontrado em: {caminho_perfil}")
    return existe


# Verifica se a sessão do Apollo ainda está ativa navegando até a home.
def sessao_ativa(driver) -> bool:
    """
    Navega até a home do Apollo e verifica se fomos redirecionados para login.
    Retorna True se a sessão está ativa, False se expirou ou não existe.
    """
    log.info("[SETUP] Verificando se a sessão do Apollo está ativa...")
    try:
        driver.get(URL_APOLLO_HOME)
        time.sleep(3)
        url_atual = driver.current_url
        ativa = "login" not in url_atual and "apollo.io" in url_atual
        if ativa:
            log.info(f"[SETUP] ✅ Sessão ativa. URL: {url_atual}")
        else:
            log.warning(f"[SETUP] ⚠️  Sessão expirada ou inválida. URL: {url_atual}")
        return ativa
    except Exception as e:
        log.error(f"[SETUP] Erro ao verificar sessão: {e}")
        return False


# -------------------------------------------------------------------------
# Configuração do perfil — primeiro uso ou sessão expirada
# -------------------------------------------------------------------------

# Abre o Chrome com o perfil VISU e guia o usuário pelo login manual no Apollo.
def configurar_perfil_chrome(caminho_perfil: Path) -> bool:
    """
    Abre o Chrome com o perfil VISU apontando para a tela de login do Apollo.
    O usuário faz o login manualmente (via Google ou e-mail/senha).
    O script aguarda até detectar que o login foi concluído, confirmando
    que o perfil agora tem uma sessão ativa salva.

    Este fluxo é necessário em:
      - Primeiro uso em uma máquina nova
      - Após limpeza de dados do navegador / reinstalação do Chrome
      - Após expiração longa de sessão que não pode ser renovada automaticamente

    Retorna True se o login foi concluído com sucesso, False caso contrário.
    """
    log.info("[SETUP] Iniciando configuração do perfil Chrome...")
    log.info("[SETUP] O Chrome será aberto para login manual.")

    # Abre Chrome com o perfil VISU (cria a pasta se não existir)
    options = Options()
    os.makedirs(str(caminho_perfil), exist_ok=True)
    options.add_argument(f"--user-data-dir={caminho_perfil}")
    options.add_argument("--window-size=1280,800")

    print()
    print("=" * 60)
    print("  CONFIGURAÇÃO DO PERFIL CHROME — VISU Dados")
    print("=" * 60)
    print()
    print("  O Chrome será aberto na página de login do Apollo.io.")
    print()
    print("  Por favor:")
    print("    1. Clique em 'Log in with Google'")
    print("    2. Selecione ou faça login com a conta @visudados.com.br")
    print("    3. Aguarde ser redirecionado para o Apollo")
    print("    4. Volte aqui e pressione ENTER para continuar")
    print()
    print("  IMPORTANTE: Não feche o Chrome — ele será encerrado")
    print("  automaticamente pelo script após a confirmação.")
    print("=" * 60)
    print()

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(URL_APOLLO_LOGIN)

        # Aguarda o usuário concluir o login e pressionar ENTER
        input("  Pressione ENTER aqui após concluir o login no Chrome... ")
        print()

        # Verifica se o login foi realmente concluído
        if sessao_ativa(driver):
            log.info("[SETUP] ✅ Login concluído. Perfil salvo com sessão ativa.")
            print("  ✅ Login confirmado! Perfil configurado com sucesso.")
            print()
            return True
        else:
            log.error(
                "[SETUP] ❌ Login não detectado após confirmação do usuário.\n"
                "         Certifique-se de que o login foi concluído no Chrome\n"
                "         antes de pressionar ENTER."
            )
            print("  ❌ Login não detectado. Execute o script novamente e")
            print("     certifique-se de completar o login antes de pressionar ENTER.")
            print()
            return False

    except Exception as e:
        log.error(f"[SETUP] Erro durante configuração do perfil: {e}")
        return False

    finally:
        if driver:
            driver.quit()
            log.info("[SETUP] Chrome de configuração encerrado.")


# -------------------------------------------------------------------------
# Função principal — ponto de entrada para os scripts de extração
# -------------------------------------------------------------------------

# Verifica se o ambiente está pronto (perfil + sessão) e configura se necessário.
def verificar_e_configurar(caminho_perfil: Path) -> bool:
    """
    Ponto de entrada chamado antes de qualquer extração.

    Fluxo de decisão:
      1. Perfil não existe ou sem cookies → abre Chrome para login manual
      2. Perfil existe → abre Chrome para verificar se sessão ainda é válida
         2a. Sessão ativa   → retorna True, extração pode prosseguir
         2b. Sessão expirada → abre Chrome para login manual (renovação)

    Retorna True se o ambiente está pronto, False se houve falha na configuração.
    """
    log.info("[SETUP] ── Verificação de ambiente ──────────────────────────")

    # ── Caso 1: perfil não existe — primeiro uso ou após limpeza ──────────
    if not perfil_existe(caminho_perfil):
        log.info("[SETUP] Perfil não configurado. Iniciando configuração inicial...")
        return configurar_perfil_chrome(caminho_perfil)

    # ── Caso 2: perfil existe — verifica se a sessão ainda é válida ───────
    log.info("[SETUP] Perfil encontrado. Verificando sessão...")
    options = Options()
    options.add_argument(f"--user-data-dir={caminho_perfil}")
    options.add_argument("--window-size=1280,800")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        if sessao_ativa(driver):
            # Sessão OK — encerra o Chrome de verificação e libera para extração
            log.info("[SETUP] ✅ Ambiente pronto. Prosseguindo para extração.")
            return True
        else:
            # Sessão expirada — guia renovação de login
            log.warning("[SETUP] Sessão expirada. Renovação de login necessária.")
            driver.get(URL_APOLLO_LOGIN)

            print()
            print("=" * 60)
            print("  RENOVAÇÃO DE SESSÃO — VISU Dados")
            print("=" * 60)
            print()
            print("  Sua sessão no Apollo expirou.")
            print()
            print("  O Chrome já está aberto na página de login.")
            print("  Por favor:")
            print("    1. Clique em 'Log in with Google'")
            print("    2. Selecione a conta @visudados.com.br")
            print("    3. Aguarde ser redirecionado para o Apollo")
            print("    4. Volte aqui e pressione ENTER para continuar")
            print("=" * 60)
            print()

            input("  Pressione ENTER após concluir o login... ")
            print()

            if sessao_ativa(driver):
                log.info("[SETUP] ✅ Sessão renovada com sucesso.")
                print("  ✅ Sessão renovada! Prosseguindo para extração.")
                print()
                return True
            else:
                log.error("[SETUP] ❌ Sessão não renovada após confirmação.")
                print("  ❌ Sessão não detectada. Execute o script novamente.")
                print()
                return False

    except Exception as e:
        log.error(f"[SETUP] Erro durante verificação de sessão: {e}")
        return False

    finally:
        if driver:
            driver.quit()
            log.info("[SETUP] Chrome de verificação encerrado.")
