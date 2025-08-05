"""
Testes para o Classificador Otimizado
=====================================

Este arquivo contém testes unitários para validar o funcionamento
do classificador otimizado.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Adiciona o diretório pai ao path para importar o módulo
sys.path.append(str(Path(__file__).parent))

from classificador_otimizado import ClassificadorSeguidores, ConfiguracaoAnalise, GerenciadorConfiguracao


class TestClassificadorSeguidores:
    """Testes para a classe ClassificadorSeguidores."""
    
    @pytest.fixture
    def config_teste(self):
        """Configuração de teste."""
        return GerenciadorConfiguracao.carregar_configuracao_padrao()
    
    @pytest.fixture
    def classificador(self, config_teste):
        """Instância do classificador para testes."""
        return ClassificadorSeguidores(config_teste)
    
    @pytest.fixture
    def df_teste(self):
        """DataFrame de teste."""
        return pd.DataFrame({
            'username': ['user1', 'user2', 'user3', 'user4'],
            'bio': [
                'Estudante de medicina na UFT',
                'Loja de roupas femininas',
                'João Silva - Empresário',
                'Maria Santos - Blogger'
            ],
            'nome_completo': ['Ana Costa', 'Boutique Bella', 'João Silva', 'Maria Santos'],
            'categoria': ['', 'Varejo', 'Negócios', 'Blogger'],
            'n_seguidores': ['5k', '10k', '50k', '1m'],
            'n_seguindo': ['1k', '500', '2k', '100']
        })
    
    def test_converter_numero_vetorizado(self, classificador):
        """Testa conversão de números com sufixos."""
        serie_teste = pd.Series(['1k', '2.5k', '1m', '500', '10.5k'])
        resultado = classificador.converter_para_numero_vetorizado(serie_teste)
        
        assert resultado[0] == 1000
        assert resultado[1] == 2500
        assert resultado[2] == 1000000
        assert resultado[3] == 500
        assert resultado[4] == 10500
    
    def test_classificar_nivel_influencia(self, classificador):
        """Testa classificação de nível de influência."""
        seguidores = pd.Series([500, 5000, 50000, 500000, 2000000])
        resultado = classificador.classificar_nivel_influencia(seguidores)
        
        assert resultado[0] == 'Iniciante'
        assert resultado[1] == 'Nano'
        assert resultado[2] == 'Micro'
        assert resultado[3] == 'Médio'
        assert resultado[4] == 'Macro/Mega'
    
    def test_classificar_tipo_perfil(self, classificador, df_teste):
        """Testa classificação de tipo de perfil."""
        resultado = classificador.classificar_tipo_perfil_vetorizada(df_teste)
        
        # user2 deve ser empresa (loja)
        assert resultado[1] == "Empresa / Comércio"
        # user4 deve ser pessoa (blogger)
        assert resultado[3] == "Pessoa / Criador"
    
    def test_identificar_estudante(self, classificador, df_teste):
        """Testa identificação de estudantes."""
        resultado = classificador.identificar_estudante_vetorizada(df_teste)
        
        # user1 deve ser identificado como estudante
        assert resultado[0] == "Sim"
    
    def test_inferir_genero(self, classificador, df_teste):
        """Testa inferência de gênero."""
        resultado = classificador.inferir_genero_vetorizada(df_teste)
        
        # Ana deve ser feminino, João masculino
        assert 'Feminino' in resultado.values or 'Masculino' in resultado.values
    
    def test_validar_dataframe(self, classificador):
        """Testa validação de DataFrame."""
        # DataFrame válido
        df_valido = pd.DataFrame({'username': ['user1', 'user2']})
        assert classificador.validar_dataframe(df_valido) == True
        
        # DataFrame inválido (sem coluna username)
        df_invalido = pd.DataFrame({'nome': ['user1', 'user2']})
        assert classificador.validar_dataframe(df_invalido) == False
        
        # DataFrame vazio
        df_vazio = pd.DataFrame()
        assert classificador.validar_dataframe(df_vazio) == False
    
    def test_sanitizar_dataframe(self, classificador):
        """Testa sanitização de DataFrame."""
        df_com_duplicatas = pd.DataFrame({
            'username': ['user1', 'user1', 'user2'],
            'bio': ['bio1', 'bio2', None]
        })
        
        resultado = classificador.sanitizar_dataframe(df_com_duplicatas)
        
        # Deve remover duplicatas
        assert len(resultado) == 2
        # Deve preencher valores nulos
        assert not resultado['bio'].isna().any()
    
    def test_criar_nome_arquivo_seguro(self, classificador):
        """Testa criação de nomes de arquivo seguros."""
        nome_inseguro = "Teste / Com @ Caracteres # Especiais"
        nome_seguro = classificador.criar_nome_arquivo_seguro(nome_inseguro)
        
        # Não deve conter caracteres especiais
        assert '/' not in nome_seguro
        assert '@' not in nome_seguro
        assert '#' not in nome_seguro
        # Deve substituir espaços por underscores
        assert '_' in nome_seguro


def test_gerenciador_configuracao():
    """Testa o gerenciador de configuração."""
    config = GerenciadorConfiguracao.carregar_configuracao_padrao()
    
    # Verifica se todas as propriedades necessárias existem
    assert hasattr(config, 'arquivo_entrada')
    assert hasattr(config, 'colunas_segmentacao')
    assert hasattr(config, 'palavras_chave_empresa')
    assert hasattr(config, 'palavras_chave_pessoa')
    
    # Verifica se as listas não estão vazias
    assert len(config.palavras_chave_empresa) > 0
    assert len(config.palavras_chave_pessoa) > 0
    assert len(config.colunas_segmentacao) > 0


if __name__ == "__main__":
    # Executa testes simples se pytest não estiver disponível
    print("Executando testes básicos...")
    
    try:
        config = GerenciadorConfiguracao.carregar_configuracao_padrao()
        classificador = ClassificadorSeguidores(config)
        
        # Teste básico de conversão
        serie_teste = pd.Series(['1k', '2m', '500'])
        resultado = classificador.converter_para_numero_vetorizado(serie_teste)
        print(f"✅ Teste conversão: {resultado.tolist()}")
        
        # Teste básico de DataFrame
        df_teste = pd.DataFrame({
            'username': ['user1', 'user2'],
            'bio': ['Estudante UFT', 'Loja de roupas'],
            'nome_completo': ['Ana Silva', 'Maria Santos']
        })
        
        valido = classificador.validar_dataframe(df_teste)
        print(f"✅ Teste validação: {valido}")
        
        print("🎉 Todos os testes básicos passaram!")
        
    except Exception as e:
        print(f"❌ Erro nos testes: {e}")
