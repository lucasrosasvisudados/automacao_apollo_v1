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
2. Navega diretamente para https://app.apollo.io/#/sequences/analytics
3. Localiza o botão "More Actions Menu" via CSS e pressiona ENTER
4. Localiza o link "Export to CSV" no menu e pressiona ENTER duas vezes
5. Aguarda o download ser concluído na pasta configurada

Autenticação:
-------------
Nenhuma credencial é armazenada neste módulo. O login é mantido
pelo perfil Chrome em /projects/chrome_profiles/profile_visu.
Para registrar ou renovar a sessão, abra o Chrome com esse perfil,
faça login manualmente no Apollo e execute este script novamente.

Dependências:
-------------
- selenium (Selenium Manager cuida do chromedriver automaticamente)
- common_browser (módulo interno VISU)
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

from common.common_browser import iniciar_chrome_driver
from common.common_setup import verificar_e_configurar, CAMINHO_PERFIL_VISU

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
#   aria-label é o seletor mais estável — não depende de classes CSS
#   que mudam a cada deploy do Apollo.
SELECTOR_BTN_MORE_ACTIONS = 'button[aria-label="More Actions Menu"]'

# Elemento 2 — Link "Export to CSV" no menu:
#   <a role="button" ...><span ...>Export to CSV</span></a>
#   XPath busca o <a> que contém um span com o texto exato.
XPATH_EXPORT_CSV = '//a[.//span[contains(text(), "Export to CSV")]]'

# Tempo máximo de espera por elementos na página (segundos)
TIMEOUT_ELEMENTO = 30

# Tempo máximo para o download completar (segundos)
TIMEOUT_DOWNLOAD = 60


# -------------------------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------------------------
def verificar_sessao_ativa(driver) -> bool:
    """
    Verifica se o perfil ainda tem sessão ativa no Apollo.
    Se a URL contiver 'login', a sessão expirou — fazer login manualmente
    com o perfil VISU no Chrome e executar novamente.
    """
    url_atual = driver.current_url
    if "login" in url_atual:
        log.error(
            "[SESSÃO] Sessão expirada ou perfil não autenticado.\n"
            "         Abra o Chrome com o perfil VISU, faça login no Apollo\n"
            "         manualmente e execute o script novamente."
        )
        return False
    log.info(f"[SESSÃO] Sessão ativa. URL atual: {url_atual}")
    return True


def clicar_elemento_com_enter(driver, wait, seletor: str, tipo: str, n_enters: int = 1, descricao: str = "") -> bool:
    """
    Localiza um elemento na página (CSS ou XPath), foca nele e pressiona
    ENTER N vezes.

    Parâmetros
    ----------
    driver      : WebDriver
    wait        : WebDriverWait configurado
    seletor     : str — seletor CSS ou XPath do elemento
    tipo        : str — "css" ou "xpath"
    n_enters    : int — quantas vezes pressionar ENTER (padrão: 1)
    descricao   : str — nome legível do elemento para logs

    Retorna
    -------
    bool — True se encontrou e acionou, False se timeout
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

    # Foca o elemento e pressiona ENTER N vezes
    elemento.click()
    for i in range(n_enters):
        elemento.send_keys(Keys.RETURN)
        log.info(f"  → ENTER [{i+1}/{n_enters}] em: {nome}")
        time.sleep(0.3)

    return True


def aguardar_download_concluir(
    pasta_download: str,
    timeout: int = TIMEOUT_DOWNLOAD,
    extensao: str = ".csv"
) -> Optional[str]:
    """
    Aguarda até que um novo arquivo CSV apareça na pasta de download.
    Ignora arquivos .crdownload (download ainda em progresso no Chrome).

    Retorna o caminho do arquivo baixado, ou None se timeout atingido.
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
            # Confirma que o arquivo foi criado após o início desta execução
            if os.path.getctime(mais_recente) >= inicio:
                log.info(f"[DOWNLOAD] ✅ Arquivo recebido: {mais_recente}")
                return mais_recente
        time.sleep(1)

    log.error(f"[DOWNLOAD] ❌ Timeout: nenhum {extensao} encontrado em {timeout}s.")
    return None


# Navega o browser para a página de Sequences Analytics do Apollo e aguarda o carregamento completo do SPA.
def navegar_para_sequences_analytics(driver, wait) -> bool:
    """
    Acessa https://app.apollo.io/#/sequences/analytics e aguarda a renderização
    completa da página antes de prosseguir.

    O Apollo usa React (SPA): o DOM pode reportar "complete" antes dos
    componentes estarem visíveis. A estratégia aqui é aguardar o botão
    "More Actions Menu" ficar presente no DOM — isso garante que a página
    de Analytics carregou de facto, não apenas que a URL está correta.

    Parâmetros
    ----------
    driver : WebDriver
    wait   : WebDriverWait configurado com o timeout desejado

    Retorna
    -------
    bool — True se a página carregou e a sessão está ativa, False caso contrário
    """
    log.info("[1/4] Navegando para Sequences Analytics...")
    driver.get(URL_SEQUENCES_ANALYTICS)

    # Aguarda o DOM sinalizar carregamento completo
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    # Confirma que não fomos redirecionados para a tela de login
    if not verificar_sessao_ativa(driver):
        return False

    # Aguarda o botão "More Actions Menu" aparecer no DOM.
    # Esse é o indicador mais confiável de que a página de Analytics
    # terminou de renderizar — enquanto ele não existir, a página ainda
    # está carregando dados e os cliques seguintes falhariam.
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
            "        • Sessão expirada — faça login manual com o perfil VISU\n"
            "        • Apollo mudou o seletor do botão\n"
            "        • Conexão lenta — aumente TIMEOUT em run_apollo_extractor.py"
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
        Define se o Chrome será executado sem interface gráfica.
        Recomendado False na primeira execução para validar o fluxo.
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

    # ── PASSO 0: Verificar perfil Chrome e sessão Apollo ──────────────────
    # Garante que o perfil existe e tem sessão ativa antes de qualquer ação.
    # Em máquinas novas ou sessões expiradas, guia o login manual automaticamente.
    if not verificar_e_configurar(CAMINHO_PERFIL_VISU):
        log.error("[EXTRACT] Ambiente não configurado. Extração cancelada.")
        return None

    # ── Inicia o Chrome com o perfil VISU ─────────────────────────────────
    driver = iniciar_chrome_driver(
        headless=headless,
        usar_perfil_visu=True,
        download_dir=pasta
    )

    try:
        # ── PASSO 1: Navega para Sequences Analytics ───────────────────────
        wait = WebDriverWait(driver, timeout)
        if not navegar_para_sequences_analytics(driver, wait):
            return None

        # ── PASSO 2: Elemento 1 — botão "More Actions Menu" ───────────────
        # Localiza pelo aria-label, clica para focar e pressiona ENTER 1x
        # para abrir o menu de ações.
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

        # Aguarda o menu animar e os itens ficarem clicáveis
        time.sleep(1)

        # ── PASSO 3: Elemento 2 — opção "Export to CSV" ───────────────────
        # Localiza o link pelo XPath (texto do span interno), pressiona
        # ENTER 2 vezes para confirmar a exportação.
        log.info('[3/4] Acionando "Export to CSV"...')
        sucesso = clicar_elemento_com_enter(
            driver=driver,
            wait=wait,
            seletor=XPATH_EXPORT_CSV,
            tipo="xpath",
            n_enters=2,
            descricao="Export to CSV"
        )
        if not sucesso:
            return None

        log.info('[3/4] ✅ Exportação acionada.')

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
