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
    Função principal para processar múltiplos arquivos CSV, consolidar dados e salvar em um único CSV tratado.
    """
    import glob
    from datetime import datetime

    # Configurações
    pasta_csvs = os.path.join(os.path.dirname(__file__), "dados_nao_tratados")
    padrao_csvs = os.path.join(pasta_csvs, "*.csv")
    arquivos_csv = glob.glob(padrao_csvs)
    arquivo_saida = os.path.join(os.path.dirname(__file__), "afya-paloma-bandeira-fisioulbra-primicast-ulbrapalmas-seducgo-unitop.csv")
    data_leitura = datetime.now().strftime("%Y-%m-%d")

    print("="*60)
    print("TRATAMENTO DE DADOS - CURTIDAS INSTAGRAM (MÚLTIPLOS ARQUIVOS)")
    print("="*60)

    if not arquivos_csv:
        print("Nenhum arquivo CSV encontrado para processar.")
        return

    lista_dfs = []
    for caminho_csv in arquivos_csv:
        try:
            df = pd.read_csv(caminho_csv)
            # Renomeia colunas
            if 'username_curtiu' in df.columns:
                df = df.rename(columns={'username_curtiu': 'username'})
            if 'nome_completo_curtiu' in df.columns:
                df = df.rename(columns={'nome_completo_curtiu': 'nome_completo'})
            # Remove colunas indesejadas
            for col in ['data_post', 'texto_post']:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # Ajusta coluna de foto de perfil
            if 'url_foto_perfil' in df.columns:
                # Considera que se o valor não for vazio/nulo, tem foto de perfil
                df['foto_perfil'] = df['url_foto_perfil'].apply(lambda x: 1 if pd.notnull(x) and str(x).strip() != '' else 0)

            # Adiciona coluna de origem
            df['arquivo_origem'] = os.path.basename(caminho_csv)
            # Adiciona data da leitura
            df['data_leitura'] = data_leitura
            lista_dfs.append(df)
        except Exception as e:
            print(f"Erro ao processar {caminho_csv}: {e}")

    if not lista_dfs:
        print("Nenhum dado válido para consolidar.")
        return

    # Concatena todos os DataFrames
    df_unificado = pd.concat(lista_dfs, ignore_index=True)

    # Conta aparições por usuário
    if 'username' in df_unificado.columns:
        contagem = df_unificado['username'].value_counts()
        df_unificado['quantidade_aparicoes'] = df_unificado['username'].map(contagem)
    else:
        print("Coluna 'username' não encontrada após renomeação. Abortando.")
        return

    # Remove duplicatas mantendo a primeira ocorrência de cada usuário
    df_final = df_unificado.drop_duplicates(subset=['username'], keep='first')

    # Se arquivo de saída já existe, anexa os novos dados sem sobrescrever
    if os.path.exists(arquivo_saida):
        try:
            df_existente = pd.read_csv(arquivo_saida)
            df_final = pd.concat([df_existente, df_final], ignore_index=True)
            # Atualiza quantidade_aparicoes considerando o total consolidado
            contagem_total = df_final['username'].value_counts()
            df_final['quantidade_aparicoes'] = df_final['username'].map(contagem_total)
            # Remove duplicatas novamente
            df_final = df_final.drop_duplicates(subset=['username'], keep='first')
        except Exception as e:
            print(f"Erro ao ler arquivo de saída existente: {e}")

    # Salva o DataFrame final
    try:
        df_final.to_csv(arquivo_saida, index=False, encoding='utf-8')
        print(f"\n=== ARQUIVO UNIFICADO SALVO ===")
        print(f"Arquivo consolidado salvo em: {arquivo_saida}")
        print(f"Total de registros únicos: {len(df_final)}")
    except Exception as e:
        print(f"Erro ao salvar arquivo unificado: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
