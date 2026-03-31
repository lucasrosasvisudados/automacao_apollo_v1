"""
extract_apollo_sequences.py - VISU Dados
=========================================

Módulo de extração do relatório de Sequences Analytics do Apollo.io.

Representa a fase de **extração (Extract)** do pipeline ETL da VISU para
dados do Apollo. Utiliza o perfil Chrome logado da VISU, eliminando a
necessidade de armazenar credenciais em arquivos de configuração.

Fluxo de execução:
------------------
1. Abre o Chrome com o perfil VISU (já autenticado no Apollo)
2. verificar_e_configurar() confirma sessão ativa — ou guia login automático
3. Navega diretamente para https://app.apollo.io/#/sequences/analytics
4. Localiza o botão "More Actions Menu" via CSS e pressiona ENTER
5. Localiza o link "Export to CSV" no menu e aciona o download
6. Aguarda o download ser concluído na pasta configurada

Autenticação:
-------------
Nenhuma credencial é armazenada neste módulo. O login é mantido
pelo perfil Chrome em /projects/chrome_profiles/profile_visu.
Se a sessão expirar, o script abre a tela de login do Apollo e aguarda
o login manual automaticamente — sem necessidade de teclar ENTER.

Dependências:
-------------
- selenium (Selenium Manager cuida do chromedriver automaticamente)
- common_browser (módulo interno VISU)
- common_setup  (módulo interno VISU)
- perfil logado em: /projects/chrome_profiles/profile_visu
"""

# -------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------
import sys
import os
import time
import glob
import logging
from pathlib import Path
from typing import Optional

# Garante que /python esteja no sys.path para imports do common
sys.path.append(str(Path(__file__).resolve().parents[2]))

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from common.common_browser import iniciar_chrome_driver, CAMINHO_PERFIL_VISU
from common.common_setup import verificar_e_configurar

# -------------------------------------------------------------------------
# Configuração de logging
# -------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("apollo_sequences_extract.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Constantes
# -------------------------------------------------------------------------
URL_SEQUENCES_ANALYTICS = "https://app.apollo.io/#/sequences/analytics"

# ── Seletores CSS/XPath dos elementos do Apollo ───────────────────────────
#
# Elemento 1 — Botão "More Actions Menu":
#   <button aria-label="More Actions Menu" ...>
SELECTOR_BTN_MORE_ACTIONS = 'button[aria-label="More Actions Menu"]'

# Elemento 2 — Link "Export to CSV" no menu:
#   <a role="button" ...><span ...>Export to CSV</span></a>
XPATH_EXPORT_CSV = '//a[.//span[contains(text(), "Export to CSV")]]'

# Tempo máximo de espera por elementos na página (segundos)
TIMEOUT_ELEMENTO = 30

# Tempo máximo para o download completar (segundos)
TIMEOUT_DOWNLOAD = 60


# -------------------------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------------------------
def clicar_elemento_com_enter(
    driver,
    wait,
    seletor: str,
    tipo: str,
    n_enters: int = 1,
    descricao: str = ""
) -> bool:
    """
    Localiza um elemento na página (CSS ou XPath), foca nele via JS
    e pressiona ENTER N vezes.

    Usar focus() via JS em vez de click() evita duplo disparo em SPAs:
    click() já aciona o elemento, e o ENTER subsequente repetiria a ação
    (ex: abrir e fechar o menu imediatamente).
    """
    by = By.CSS_SELECTOR if tipo == "css" else By.XPATH
    nome = descricao or seletor

    log.info(f"  Localizando: {nome}...")
    try:
        elemento = wait.until(EC.element_to_be_clickable((by, seletor)))
    except TimeoutException:
        log.error(
            f"  ❌ Elemento não encontrado: {nome}\n"
            f"     Seletor: {seletor}\n"
            f"     Verifique se a página carregou e se o seletor ainda é válido."
        )
        driver.save_screenshot(f"erro_{nome.replace(' ', '_').lower()}.png")
        return False

    # Foca via JS (sem disparar click) e pressiona ENTER N vezes
    driver.execute_script("arguments[0].focus();", elemento)
    for i in range(n_enters):
        elemento.send_keys(Keys.RETURN)
        log.info(f"  → ENTER [{i+1}/{n_enters}] em: {nome}")
        time.sleep(0.5)

    return True


def aguardar_download_concluir(
    pasta_download: str,
    timeout: int = TIMEOUT_DOWNLOAD,
    extensao: str = ".csv"
) -> Optional[str]:
    """
    Aguarda até que um novo arquivo CSV apareça na pasta de download.
    Ignora arquivos .crdownload (download ainda em progresso no Chrome).
    """
    log.info(f"[DOWNLOAD] Aguardando arquivo {extensao} em: {pasta_download}")
    inicio = time.time()

    while time.time() - inicio < timeout:
        arquivos = [
            f for f in glob.glob(os.path.join(pasta_download, f"*{extensao}"))
            if not f.endswith(".crdownload")
        ]
        if arquivos:
            mais_recente = max(arquivos, key=os.path.getctime)
            if os.path.getctime(mais_recente) >= inicio:
                log.info(f"[DOWNLOAD] ✅ Arquivo recebido: {mais_recente}")
                return mais_recente
        time.sleep(1)

    log.error(f"[DOWNLOAD] ❌ Timeout: nenhum {extensao} encontrado em {timeout}s.")
    return None


def aguardar_pagina_analytics(driver, wait) -> bool:
    """
    Aguarda a renderização completa da página de Sequences Analytics.

    verificar_e_configurar() já navegou para URL_SEQUENCES_ANALYTICS.
    Esta função apenas confirma que o SPA terminou de renderizar,
    esperando o botão "More Actions Menu" aparecer no DOM.
    """
    log.info("[1/4] Aguardando renderização completa da página de Analytics...")
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, SELECTOR_BTN_MORE_ACTIONS)
        ))
    except TimeoutException:
        log.error(
            "[1/4] ❌ Timeout aguardando a página de Analytics renderizar.\n"
            "      O botão 'More Actions Menu' não apareceu dentro do tempo limite.\n"
            "      Possíveis causas:\n"
            "        • Sessão expirada — execute novamente para refazer login\n"
            "        • Apollo mudou o seletor do botão\n"
            "        • Conexão lenta — aumente TIMEOUT_ELEMENTO"
        )
        driver.save_screenshot("erro_navegacao.png")
        return False

    log.info(f"[1/4] ✅ Página carregada e pronta: {driver.current_url}")
    return True


# -------------------------------------------------------------------------
# Função principal de extração
# -------------------------------------------------------------------------
def extrair_sequences_analytics(
    download_dir: str = None,
    headless: bool = False,
    timeout: int = TIMEOUT_ELEMENTO
) -> Optional[str]:
    """
    Acessa o Apollo.io e exporta o relatório de Sequences Analytics como CSV.

    Parâmetros
    ----------
    download_dir : str, opcional
        Caminho absoluto da pasta onde o CSV será salvo.
        Se None, usa a pasta Downloads padrão do Windows.
    headless : bool, opcional
        Se True, Chrome roda sem interface gráfica.
        Use False na primeira execução para o login manual ser visível.
    timeout : int, opcional
        Tempo máximo (segundos) para aguardar cada elemento na página.

    Retorna
    -------
    str | None
        Caminho completo do arquivo CSV baixado, ou None em caso de erro.
    """
    pasta = download_dir or str(Path.home() / "Downloads")

    log.info("=" * 60)
    log.info("  APOLLO SEQUENCES EXTRACT — Iniciando")
    log.info("=" * 60)
    log.info(f"  URL:      {URL_SEQUENCES_ANALYTICS}")
    log.info(f"  Download: {pasta}")
    log.info(f"  Headless: {headless}")
    log.info("=" * 60)

    # ── Inicia o Chrome com o perfil VISU ─────────────────────────────────
    # O driver é iniciado ANTES de verificar_e_configurar para evitar
    # abertura dupla do Chrome. A função de setup recebe o driver já aberto
    # e opera dentro dele — sem abrir uma segunda instância.
    driver = iniciar_chrome_driver(
        headless=headless,
        usar_perfil_visu=True,
        download_dir=pasta
    )

    try:
        wait = WebDriverWait(driver, timeout)

        # ── PASSO 0: Verificar sessão e navegar para Analytics ────────────
        # verificar_e_configurar() checa a sessão no driver já aberto e,
        # ao final (sessão ok ou login renovado), navega para URL_SEQUENCES_ANALYTICS.
        # Se retornar False, a extração é cancelada.
        log.info("[0/4] Verificando sessão e navegando para Analytics...")
        if not verificar_e_configurar(driver, CAMINHO_PERFIL_VISU, URL_SEQUENCES_ANALYTICS):
            log.error("[EXTRACT] Ambiente não configurado. Extração cancelada.")
            return None

        # ── PASSO 1: Aguarda a renderização da página ─────────────────────
        if not aguardar_pagina_analytics(driver, wait):
            return None

        # ── PASSO 2: Botão "More Actions Menu" ───────────────────────────
        log.info('[2/4] Acionando botão "More Actions Menu"...')
        sucesso = clicar_elemento_com_enter(
            driver=driver,
            wait=wait,
            seletor=SELECTOR_BTN_MORE_ACTIONS,
            tipo="css",
            n_enters=1,
            descricao="More Actions Menu"
        )
        if not sucesso:
            return None

        log.info('[2/4] ✅ Menu aberto.')
        time.sleep(1)  # Aguarda animação do menu

        # ── PASSO 3: Opção "Export to CSV" ───────────────────────────────
        # Para links <a> no Apollo, click() é mais confiável que focus()+ENTER
        # para abrir o diálogo. Os send_keys(RETURN) confirmam a exportação.
        log.info('[3/4] Acionando "Export to CSV"...')
        try:
            btn_export = wait.until(
                EC.element_to_be_clickable((By.XPATH, XPATH_EXPORT_CSV))
            )
            btn_export.click()
            time.sleep(0.5)
            btn_export.send_keys(Keys.RETURN)
            time.sleep(0.5)
            btn_export.send_keys(Keys.RETURN)
            log.info('[3/4] ✅ Exportação acionada.')
        except TimeoutException:
            log.error(
                '[3/4] ❌ Elemento "Export to CSV" não encontrado.\n'
                f'      Seletor: {XPATH_EXPORT_CSV}\n'
                '      Verifique se o menu abriu corretamente.'
            )
            driver.save_screenshot("erro_export_csv.png")
            return None

        # ── PASSO 4: Aguarda o download completar ─────────────────────────
        log.info("[4/4] Aguardando arquivo CSV...")
        caminho_csv = aguardar_download_concluir(pasta)

        if caminho_csv:
            log.info(f"[4/4] ✅ Download concluído: {caminho_csv}")
        else:
            log.error("[4/4] ❌ Download não detectado dentro do tempo limite.")
            driver.save_screenshot("erro_download.png")

        return caminho_csv

    except Exception as e:
        log.error(f"[ERRO] Falha inesperada: {e}")
        try:
            driver.save_screenshot("erro_inesperado.png")
        except Exception:
            pass
        return None

    finally:
        driver.quit()
        log.info("[EXTRACT] Navegador encerrado.")


# -------------------------------------------------------------------------
# Execução direta (teste)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    resultado = extrair_sequences_analytics(headless=False)
    if resultado:
        print(f"\n[OK] CSV exportado: {resultado}")
    else:
        print("\n[ERRO] Extração falhou. Verifique os logs e screenshots.")
