import pandas as pd
import re

def keep_only_rows_with_phone_numbers(file_path, output_file_path):
    """
    Mantém apenas as linhas que possuem um número de telefone na coluna 'Telefone'
    e salva o resultado em um novo CSV.

    Args:
        file_path (str): O caminho para o arquivo CSV de entrada.
        output_file_path (str): O caminho onde o CSV resultante será salvo.

    Returns:
        pandas.DataFrame: Um DataFrame com apenas as linhas que possuem número de telefone.
    """
    try:
        df = pd.read_csv(file_path)
        print("Original DataFrame head:")
        print(df.head())
        print("\nOriginal DataFrame info:")
        df.info()

        # Remove linhas onde 'Telefone' é NaN (Not a Number) ou vazio
        # Isso garante que apenas as linhas com algum valor na coluna 'Telefone' sejam mantidas.
        df_cleaned = df.dropna(subset=['Telefone'])
        print(f"\nDataFrame após remover linhas sem números de telefone: {len(df_cleaned)} linhas")

        # Opcional: Garante que a coluna 'Telefone' é do tipo string,
        # útil se for fazer alguma outra validação no futuro, mas para
        # apenas manter não é estritamente necessário após o dropna.
        df_cleaned['Telefone'] = df_cleaned['Telefone'].astype(str)


        print("\nDataFrame Resultante (apenas com números de telefone) head:")
        print(df_cleaned.head())
        print("\nDataFrame Resultante (apenas com números de telefone) info:")
        df_cleaned.info()

        # Salva o DataFrame resultante em um novo arquivo CSV
        df_cleaned.to_csv(output_file_path, index=False)
        print(f"\nDados com apenas números de telefone salvos em '{output_file_path}'")

        return df_cleaned

    except FileNotFoundError:
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        return pd.DataFrame()
    except KeyError:
        print("Erro: A coluna 'Telefone' não foi encontrada no CSV. Por favor, certifique-se de que o nome da coluna está correto.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        return pd.DataFrame()

# Especifique o caminho para o seu arquivo CSV de entrada
input_file_path = 'funcionarios_instagram.csv'
# Especifique o caminho para o arquivo CSV de saída
output_file_path = 'funcionarios_com_telefone.csv' # Nome do arquivo de saída ajustado

# Execute a função
processed_df = keep_only_rows_with_phone_numbers(input_file_path, output_file_path)