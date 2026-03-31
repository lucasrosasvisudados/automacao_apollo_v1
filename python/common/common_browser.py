# -------------------------------------------------------------------------
# common_browser.py - VISU Dados
# -------------------------------------------------------------------------
# Módulo central para inicialização padronizada do ChromeDriver em todos os
# scripts da VISU. Inclui:
#  - Caminhos relativos ao projeto
#  - Suporte a perfil logado (ex: conta VISU)
#  - Configurações padrão do Chrome
#  - Suporte a pasta de download personalizada (parâmetro download_dir)
#
# NOTA — chromedriver.exe:
#   Este módulo NÃO usa mais o chromedriver.exe local.
#   O Selenium Manager (embutido no Selenium 4.6+) detecta a versão do
#   Chrome instalada na máquina e baixa automaticamente o driver correto.
#   Isso elimina o erro "This version of ChromeDriver only supports Chrome
#   version X" causado por incompatibilidade entre driver e browser.
# -------------------------------------------------------------------------

import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# -------------------------------------------------------------------------
# Caminhos base
# -------------------------------------------------------------------------
ROOT_PATH = Path(__file__).resolve().parents[1]  # sobe de /common para /python
PROJECTS_PATH = ROOT_PATH / "projects"

# Perfil logado VISU — mantém a sessão ativa no Apollo sem credenciais
CAMINHO_PERFIL_VISU = PROJECTS_PATH / "chrome_profiles" / "profile_visu"

# -------------------------------------------------------------------------
# Função principal
# -------------------------------------------------------------------------
def iniciar_chrome_driver(
    headless: bool = False,
    usar_perfil_visu: bool = True,
    window_size: str = "1920,1080",
    user_agent: str = None,
    download_dir: str = None
) -> webdriver.Chrome:
    """
    Inicializa o ChromeDriver com as configurações padrão da VISU.

    Usa o Selenium Manager para gerenciar o ChromeDriver automaticamente —
    nenhum chromedriver.exe manual necessário. O driver correto é baixado
    e cacheado na primeira execução conforme a versão do Chrome instalado.

    Parâmetros:
    -----------
    headless : bool
        Define se o Chrome será aberto em modo invisível.
    usar_perfil_visu : bool
        Se True, usa o perfil logado da VISU em
        /projects/chrome_profiles/profile_visu.
    window_size : str
        Tamanho da janela (largura,altura).
    user_agent : str
        User-Agent personalizado (opcional).
    download_dir : str
        Caminho absoluto da pasta de destino para downloads automáticos.
        Se None, usa a pasta Downloads padrão do Windows.

    Retorna:
    --------
    driver : webdriver.Chrome
        Instância pronta do navegador Chrome configurado.
    """

    chrome_options = Options()

    # ── Perfil logado da VISU ─────────────────────────────────────────────
    if usar_perfil_visu:
        perfil_path = str(CAMINHO_PERFIL_VISU)
        os.makedirs(perfil_path, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={perfil_path}")

    # ── Configurações padrão ──────────────────────────────────────────────
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={window_size}")

    # ── User-Agent VISU padrão ────────────────────────────────────────────
    default_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.5993.70 Safari/537.36"
    )
    chrome_options.add_argument(f"user-agent={user_agent or default_ua}")

    # ── Pasta de download personalizada ───────────────────────────────────
    # Configura o Chrome para salvar arquivos diretamente na pasta indicada,
    # sem exibir o diálogo "Salvar como".
    pasta_download = download_dir or str(Path.home() / "Downloads")
    os.makedirs(pasta_download, exist_ok=True)

    chrome_options.add_experimental_option("prefs", {
        "download.default_directory":  pasta_download,
        "download.prompt_for_download": False,
        "download.directory_upgrade":   True,
        "safebrowsing.enabled":         True,
    })

    # ── Inicializa o Chrome via Selenium Manager ───────────────────────────
    # Service() sem argumentos ativa o Selenium Manager automaticamente:
    # detecta a versão do Chrome instalada e usa o driver compatível.
    # O driver é baixado uma vez e cacheado em %USERPROFILE%\.cache\selenium
    print(f"[BROWSER] Iniciando Chrome via Selenium Manager (driver automático)...")
    print(f"[BROWSER] Perfil VISU: {'ativo' if usar_perfil_visu else 'desativado'}")
    print(f"[BROWSER] Download configurado em: {pasta_download}")

    driver = webdriver.Chrome(options=chrome_options)
    return driver
