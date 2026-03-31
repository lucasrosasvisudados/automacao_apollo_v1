"""
run_apollo_extractor.py - VISU Dados
======================================

Script de entrada para execução da extração de Sequences Analytics do Apollo.io.
Segue o padrão run_*.py do projeto VISU: ponto de entrada simples que
instancia os módulos de extract/transform/load conforme necessário.

Uso:
----
    python run_apollo_extractor.py

Autenticação:
-------------
Nenhuma credencial necessária. O Chrome abre com o perfil VISU
(/projects/chrome_profiles/profile_visu) que mantém a sessão ativa.
Para renovar a sessão, abra o Chrome com esse perfil e faça login
manualmente no Apollo — feito isso, este script não precisa de ajuste.

Configuração:
-------------
Ajuste as variáveis da seção CONFIG abaixo conforme necessário.
Não há arquivo .env — todas as configurações são não-sensíveis.
"""

import sys
import os
from pathlib import Path

# Garante que /python esteja no sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from projects.extract.extract_apollo_sequences import extrair_sequences_analytics

# -------------------------------------------------------------------------
# CONFIG — ajuste conforme necessário
# -------------------------------------------------------------------------

# Pasta de destino do CSV exportado.
# None = usa a pasta Downloads padrão do Windows do usuário atual.
# Exemplo com caminho fixo: r"C:\Relatorios\Apollo"
DOWNLOAD_DIR = None

# False = abre o Chrome visível (recomendado para validação)
# True  = roda em segundo plano (para agendamentos automatizados)
HEADLESS = False

# Tempo máximo (segundos) para aguardar cada elemento na página
TIMEOUT = 30

# -------------------------------------------------------------------------
# Execução
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  VISU Dados — Apollo Sequences Extractor")
    print("=" * 60)
    print()

    resultado = extrair_sequences_analytics(
        download_dir=DOWNLOAD_DIR,
        headless=HEADLESS,
        timeout=TIMEOUT,
    )

    print()
    if resultado:
        print("=" * 60)
        print("  Extração concluída com sucesso!")
        print(f"  Arquivo: {resultado}")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  Extração falhou.")
        print("  Verifique: apollo_sequences_extract.log")
        print("  Screenshots: erro_*.png (se geradas)")
        print("=" * 60)
    print()
