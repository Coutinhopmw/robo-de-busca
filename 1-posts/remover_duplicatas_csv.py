#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script genérico para remoção de duplicatas em arquivos CSV
Uso: python remover_duplicatas_csv.py [caminho_arquivo] [coluna_referencia]
"""

import pandas as pd
import sys
import os
from datetime import datetime

def processar_arquivo(caminho_arquivo, coluna_referencia='username_curtiu'):
    """
    Processa um arquivo CSV removendo duplicatas
    """
    
    print(f"Processando: {caminho_arquivo}")
    print(f"Coluna de referência: {coluna_referencia}")
    print("-" * 50)
    
    try:
        # Carrega o CSV
        df = pd.read_csv(caminho_arquivo)
        
        # Estatísticas antes
        total_antes = len(df)
        duplicatas = df.duplicated(subset=[coluna_referencia]).sum()
        unicos = df[coluna_referencia].nunique()
        
        print(f"📊 Registros originais: {total_antes}")
        print(f"🔄 Duplicatas encontradas: {duplicatas}")
        print(f"👤 Usuários únicos: {unicos}")
        
        # Remove duplicatas (mantém primeira ocorrência)
        df_limpo = df.drop_duplicates(subset=[coluna_referencia], keep='first')
        
        # Estatísticas depois
        total_depois = len(df_limpo)
        removidos = total_antes - total_depois
        percentual = (removidos / total_antes) * 100 if total_antes > 0 else 0
        
        print(f"✅ Registros finais: {total_depois}")
        print(f"🗑️  Registros removidos: {removidos}")
        print(f"📈 Percentual removido: {percentual:.2f}%")
        
        # Salva arquivo limpo
        diretorio = os.path.dirname(caminho_arquivo)
        nome_arquivo = os.path.basename(caminho_arquivo)
        nome_base, extensao = os.path.splitext(nome_arquivo)
        
        arquivo_saida = os.path.join(diretorio, f"{nome_base}_sem_duplicatas{extensao}")
        df_limpo.to_csv(arquivo_saida, index=False, encoding='utf-8')
        
        print(f"💾 Arquivo salvo: {arquivo_saida}")
        
        return arquivo_saida
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return None

if __name__ == "__main__":
    # Verifica argumentos da linha de comando
    if len(sys.argv) < 2:
        print("Uso: python remover_duplicatas_csv.py [arquivo.csv] [coluna_opcional]")
        print("Exemplo: python remover_duplicatas_csv.py curtidas.csv username_curtiu")
        sys.exit(1)
    
    arquivo = sys.argv[1]
    coluna = sys.argv[2] if len(sys.argv) > 2 else 'username_curtiu'
    
    if os.path.exists(arquivo):
        processar_arquivo(arquivo, coluna)
    else:
        print(f"❌ Arquivo não encontrado: {arquivo}")
