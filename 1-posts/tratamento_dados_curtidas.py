#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para tratamento de dados de curtidas do Instagram
Remove dados duplicados baseado na coluna username_curtiu
"""

import pandas as pd
import os
from datetime import datetime

def remover_duplicatas_curtidas(caminho_arquivo, coluna_referencia='username_curtiu', manter_primeiro=True):
    """
    Remove duplicatas de um arquivo CSV baseado na coluna especificada
    
    Parâmetros:
    - caminho_arquivo: Caminho para o arquivo CSV
    - coluna_referencia: Coluna para identificar duplicatas (padrão: 'username_curtiu')
    - manter_primeiro: Se True, mantém a primeira ocorrência; se False, mantém a última
    
    Retorna:
    - DataFrame pandas com os dados tratados
    """
    
    print(f"Iniciando tratamento do arquivo: {caminho_arquivo}")
    print(f"Coluna de referência para duplicatas: {coluna_referencia}")
    
    try:
        # Carrega o arquivo CSV
        df = pd.read_csv(caminho_arquivo)
        print(f"Arquivo carregado com sucesso! Total de registros: {len(df)}")
        
        # Verifica se a coluna de referência existe
        if coluna_referencia not in df.columns:
            print(f"Erro: Coluna '{coluna_referencia}' não encontrada no arquivo!")
            print(f"Colunas disponíveis: {list(df.columns)}")
            return None
        
        # Mostra informações antes do tratamento
        total_antes = len(df)
        duplicatas_antes = df.duplicated(subset=[coluna_referencia]).sum()
        unicos_antes = df[coluna_referencia].nunique()
        
        print(f"\n=== ANÁLISE ANTES DO TRATAMENTO ===")
        print(f"Total de registros: {total_antes}")
        print(f"Registros duplicados: {duplicatas_antes}")
        print(f"Usuários únicos: {unicos_antes}")
        
        # Remove duplicatas mantendo a primeira ou última ocorrência
        if manter_primeiro:
            df_tratado = df.drop_duplicates(subset=[coluna_referencia], keep='first')
            print(f"\nMantendo PRIMEIRA ocorrência de cada usuário...")
        else:
            df_tratado = df.drop_duplicates(subset=[coluna_referencia], keep='last')
            print(f"\nMantendo ÚLTIMA ocorrência de cada usuário...")
        
        # Mostra informações depois do tratamento
        total_depois = len(df_tratado)
        removidos = total_antes - total_depois
        
        print(f"\n=== ANÁLISE DEPOIS DO TRATAMENTO ===")
        print(f"Total de registros: {total_depois}")
        print(f"Registros removidos: {removidos}")
        print(f"Percentual removido: {(removidos/total_antes)*100:.2f}%")
        
        return df_tratado
        
    except Exception as e:
        print(f"Erro ao processar arquivo: {str(e)}")
        return None

def salvar_arquivo_tratado(df, caminho_original):
    """
    Salva o DataFrame tratado em um novo arquivo
    
    Parâmetros:
    - df: DataFrame pandas com os dados tratados
    - caminho_original: Caminho do arquivo original
    """
    
    if df is None:
        print("Erro: DataFrame vazio, não é possível salvar.")
        return
    
    # Cria o nome do arquivo tratado
    diretorio = os.path.dirname(caminho_original)
    nome_arquivo = os.path.basename(caminho_original)
    nome_base, extensao = os.path.splitext(nome_arquivo)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_tratado = f"{nome_base}_tratado_{timestamp}{extensao}"
    caminho_tratado = os.path.join(diretorio, nome_tratado)
    
    try:
        # Salva o arquivo tratado
        df.to_csv(caminho_tratado, index=False, encoding='utf-8')
        print(f"\n=== ARQUIVO SALVO ===")
        print(f"Arquivo tratado salvo em: {caminho_tratado}")
        print(f"Total de registros salvos: {len(df)}")
        
        return caminho_tratado
        
    except Exception as e:
        print(f"Erro ao salvar arquivo: {str(e)}")
        return None

def analisar_duplicatas(caminho_arquivo, coluna_referencia='username_curtiu'):
    """
    Analisa e mostra quais usuários aparecem duplicados
    
    Parâmetros:
    - caminho_arquivo: Caminho para o arquivo CSV
    - coluna_referencia: Coluna para analisar duplicatas
    """
    
    try:
        df = pd.read_csv(caminho_arquivo)
        
        # Encontra duplicatas
        duplicatas = df[df.duplicated(subset=[coluna_referencia], keep=False)]
        
        if len(duplicatas) > 0:
            print(f"\n=== ANÁLISE DETALHADA DE DUPLICATAS ===")
            contagem_duplicatas = duplicatas[coluna_referencia].value_counts()
            
            print(f"Usuários com mais de uma curtida:")
            for usuario, quantidade in contagem_duplicatas.head(10).items():
                print(f"  {usuario}: {quantidade} curtidas")
            
            if len(contagem_duplicatas) > 10:
                print(f"  ... e mais {len(contagem_duplicatas) - 10} usuários")
        else:
            print("\nNenhuma duplicata encontrada!")
            
    except Exception as e:
        print(f"Erro ao analisar duplicatas: {str(e)}")

def main():
    """
    Função principal para executar o tratamento
    """
    
    # Configurações
    arquivo_entrada = "curtidas_completo_laizamassoneleonardo.csv"
    caminho_completo = os.path.join(os.path.dirname(__file__), arquivo_entrada)
    
    print("="*60)
    print("TRATAMENTO DE DADOS - CURTIDAS INSTAGRAM")
    print("="*60)
    
    # Verifica se o arquivo existe
    if not os.path.exists(caminho_completo):
        print(f"Erro: Arquivo não encontrado em {caminho_completo}")
        return
    
    # Analisa duplicatas antes do tratamento
    analisar_duplicatas(caminho_completo)
    
    # Remove duplicatas
    df_tratado = remover_duplicatas_curtidas(caminho_completo)
    
    if df_tratado is not None:
        # Salva arquivo tratado
        caminho_salvo = salvar_arquivo_tratado(df_tratado, caminho_completo)
        
        if caminho_salvo:
            print(f"\n=== RESUMO FINAL ===")
            print(f"✅ Tratamento concluído com sucesso!")
            print(f"📁 Arquivo original: {arquivo_entrada}")
            print(f"📁 Arquivo tratado: {os.path.basename(caminho_salvo)}")
            print(f"📊 Dados únicos por usuário mantidos")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
