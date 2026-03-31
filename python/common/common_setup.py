# -------------------------------------------------------------------------
# common_setup.py - VISU Dados
# -------------------------------------------------------------------------
# Módulo de verificação e configuração inicial do ambiente de automação.
#
# Responsabilidades:
#   1. Verificar se o perfil Chrome da VISU existe e tem sessão ativa
#   2. Se não houver perfil ou sessão, abrir o Chrome e aguardar o login
#      manual do usuário no Apollo.io via Google — SEM input() bloqueante
#   3. Confirmar que a sessão foi estabelecida antes de prosseguir
#
# CORREÇÕES aplicadas nesta versão:
#   - Removido input() bloqueante: o script agora detecta o login
#     automaticamente via polling da URL, sem intervenção manual.
#   - Removida abertura dupla do Chrome: verificar_e_configurar() agora
#     recebe o driver já iniciado (passado pelo script de extração), evitando
#     o problema de perfil travado entre duas instâncias do Chrome.
#   - A navegação para a URL de destino após login confirmado é feita
#     diretamente nesta função, dentro do mesmo driver.
# -------------------------------------------------------------------------

import os
import time
import logging
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.common_browser import CAMINHO_PERFIL_VISU

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
URL_APOLLO_LOGIN    = "https://app.apollo.io/#/login"
URL_APOLLO_HOME     = "https://app.apollo.io"

# Tempo máximo aguardando o usuário concluir o login manualmente (segundos).
# 3 minutos é suficiente para qualquer fluxo OAuth do Google.
TIMEOUT_LOGIN_MANUAL = 180

# Arquivo de cookie que o Google OAuth salva após login bem-sucedido.
COOKIE_FILE_RELATIVO = Path("Default") / "Cookies"


# -------------------------------------------------------------------------
# Verificação do perfil (sem abrir Chrome)
# -------------------------------------------------------------------------
def perfil_existe(caminho_perfil: Path) -> bool:
    """
    Retorna True se a pasta do perfil existe e contém o arquivo de cookies.
    Verificação puramente de sistema de arquivos — não abre o Chrome.
    """
    cookies_path = caminho_perfil / COOKIE_FILE_RELATIVO
    existe = caminho_perfil.exists() and cookies_path.exists()
    if existe:
        log.info(f"[SETUP] Perfil Chrome encontrado em: {caminho_perfil}")
    else:
        log.warning(f"[SETUP] Perfil Chrome NÃO encontrado em: {caminho_perfil}")
    return existe


# -------------------------------------------------------------------------
# Verificação de sessão (usando o driver já aberto)
# -------------------------------------------------------------------------
def sessao_ativa(driver) -> bool:
    """
    Navega até a home do Apollo e verifica se a sessão está ativa.
    Usa o driver já iniciado — não abre um Chrome separado.

    Retorna True se a sessão está ativa, False se expirou ou não existe.
    """
    log.info("[SETUP] Verificando se a sessão do Apollo está ativa...")
    try:
        driver.get(URL_APOLLO_HOME)
        # Aguarda o SPA redirecionar: sessão ativa vai para /home ou similar;
        # sessão expirada vai para /#/login
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
# Login manual assistido — sem input() bloqueante
# -------------------------------------------------------------------------
def aguardar_login_manual(driver, timeout: int = TIMEOUT_LOGIN_MANUAL) -> bool:
    """
    Navega para a tela de login do Apollo e aguarda automaticamente
    até detectar que o usuário concluiu o login (polling de URL).

    Substitui o input() bloqueante anterior: em vez de parar e esperar
    que o usuário tecle ENTER, o script verifica a URL a cada 2 segundos.
    Quando a URL deixa de conter 'login', o login foi concluído.

    Exibe instruções no terminal para guiar o usuário, mas não trava
    o processo esperando entrada de teclado.

    Retorna True se o login foi detectado dentro do timeout, False caso contrário.
    """
    driver.get(URL_APOLLO_LOGIN)

    print()
    print("=" * 60)
    print("  LOGIN NECESSÁRIO — VISU Dados / Apollo.io")
    print("=" * 60)
    print()
    print("  O Chrome está aberto na página de login do Apollo.io.")
    print()
    print("  Por favor:")
    print("    1. Clique em 'Log in with Google'")
    print("    2. Selecione a conta @visudados.com.br")
    print("    3. Aguarde ser redirecionado para o Apollo")
    print()
    print(f"  O script continuará automaticamente após detectar o login.")
    print(f"  Tempo limite: {timeout // 60} minutos.")
    print("=" * 60)
    print()

    inicio = time.time()
    while time.time() - inicio < timeout:
        url_atual = driver.current_url
        if "login" not in url_atual and "apollo.io" in url_atual:
            log.info(f"[SETUP] ✅ Login detectado automaticamente. URL: {url_atual}")
            print("  ✅ Login detectado! Continuando automação...")
            print()
            return True
        time.sleep(2)

    log.error(
        f"[SETUP] ❌ Timeout: login não detectado em {timeout}s.\n"
        "         Certifique-se de completar o login dentro do tempo limite."
    )
    print(f"  ❌ Tempo limite atingido. Execute o script novamente.")
    print()
    return False


# -------------------------------------------------------------------------
# Função principal — recebe o driver já iniciado pelo script de extração
# -------------------------------------------------------------------------
def verificar_e_configurar(driver, caminho_perfil: Path, url_destino: str) -> bool:
    """
    Verifica se o ambiente está pronto e navega para url_destino.

    MUDANÇA DE ASSINATURA: agora recebe o `driver` já iniciado pelo script
    de extração. Isso elimina a abertura dupla do Chrome que causava o
    travamento do perfil entre duas instâncias.

    Fluxo de decisão:
      1. Perfil sem cookies (primeiro uso) → abre tela de login, aguarda
         login automático, navega para url_destino
      2. Perfil com cookies + sessão ativa → navega direto para url_destino
      3. Perfil com cookies + sessão expirada → abre tela de login, aguarda
         login automático, navega para url_destino

    Parâmetros
    ----------
    driver        : WebDriver já iniciado por iniciar_chrome_driver()
    caminho_perfil: Path do perfil VISU (para checar existência de cookies)
    url_destino   : URL para onde navegar após confirmar sessão ativa

    Retorna True se pronto para extração, False em caso de falha.
    """
    log.info("[SETUP] ── Verificação de ambiente ──────────────────────────")

    # ── Caso 1: perfil sem cookies — primeiro uso ──────────────────────────
    if not perfil_existe(caminho_perfil):
        log.info("[SETUP] Perfil não configurado. Iniciando login inicial...")
        if not aguardar_login_manual(driver):
            return False
        # Após login, navega para a URL de destino da extração
        log.info(f"[SETUP] Navegando para destino: {url_destino}")
        driver.get(url_destino)
        return True

    # ── Caso 2/3: perfil existe — verifica sessão no driver atual ─────────
    if sessao_ativa(driver):
        # Sessão OK — navega direto para o destino
        log.info(f"[SETUP] ✅ Sessão ativa. Navegando para: {url_destino}")
        driver.get(url_destino)
        return True
    else:
        # Sessão expirada — guia renovação e navega após login
        log.warning("[SETUP] Sessão expirada. Abrindo tela de login para renovação...")
        if not aguardar_login_manual(driver):
            return False
        log.info(f"[SETUP] Navegando para destino após renovação: {url_destino}")
        driver.get(url_destino)
        return True
