"""
Classificador Otimizado de Seguidores do Instagram
=================================================

Este script analisa e classifica dados de seguidores do Instagram com
melhor performance, organização e tratamento de erros.

Principais melhorias:
- Operações vetorizadas para melhor performance
- Classes para melhor organização do código
- Type hints para melhor documentação
- Tratamento robusto de erros
- Configuração externa
- Logging estruturado
"""

import pandas as pd
import numpy as np
import logging
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConfiguracaoAnalise:
    """Configurações para análise de dados."""
    arquivo_entrada: str
    colunas_segmentacao: List[str]
    palavras_chave_empresa: List[str]
    palavras_chave_pessoa: List[str]
    capitais_cidades: List[str]
    estados: Dict[str, str]
    cidades_por_estado: Dict[str, str]
    nomes_masculinos: List[str]
    nomes_femininos: List[str]
    palavras_chave_estudante: Dict[str, List[str]]


class ClassificadorSeguidores:
    """Classe principal para classificação de seguidores."""
    
    def __init__(self, config: ConfiguracaoAnalise):
        self.config = config
        self.setup_logging()
        
        # Compilar regex patterns para melhor performance
        self.regex_patterns = {
            'estados': [re.compile(rf'\b{sigla.lower()}\b') for sigla in config.estados.keys()],
            'estudante_regex': [re.compile(pattern) for pattern in config.palavras_chave_estudante.get("PADROES_REGEX", [])],
            'estudante_termos': [re.compile(rf'\b{termo}\b') for termo in config.palavras_chave_estudante.get("TERMOS_GENERICOS", [])],
            'estudante_instituicoes': [re.compile(rf'\b{inst}\b') for inst in config.palavras_chave_estudante.get("INSTITUICOES", [])],
            'estudante_cursos': [re.compile(rf'\b{curso}\b') for curso in config.palavras_chave_estudante.get("CURSOS", [])]
        }
    
    def setup_logging(self) -> None:
        """Configura o sistema de logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('classificador.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def converter_para_numero_vetorizado(self, serie: pd.Series) -> pd.Series:
        """Converte strings com sufixos (k, m) para números de forma vetorizada."""
        def converter_valor(valor):
            if pd.isna(valor):
                return 0
            if isinstance(valor, (int, float)):
                return int(valor)
            if not isinstance(valor, str):
                return 0
            
            valor = str(valor).lower().strip().replace(',', '.')
            
            # Processa sufixos k e m
            if 'k' in valor:
                try:
                    return int(float(valor.replace('k', '')) * 1000)
                except ValueError:
                    return 0
            elif 'm' in valor:
                try:
                    return int(float(valor.replace('m', '')) * 1000000)
                except ValueError:
                    return 0
            else:
                # Remove caracteres não numéricos
                numeros = re.sub(r'\D', '', valor)
                return int(numeros) if numeros else 0
        
        return serie.apply(converter_valor)
    
    def classificar_nivel_influencia(self, seguidores: pd.Series) -> pd.Series:
        """Classifica o nível de influência baseado no número de seguidores."""
        return pd.cut(
            seguidores,
            bins=[-1, 1000, 10000, 100000, 1000000, float('inf')],
            labels=['Iniciante', 'Nano', 'Micro', 'Médio', 'Macro/Mega'],
            include_lowest=True
        )
    
    def extrair_localizacao_vetorizada(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrai cidade e estado de forma vetorizada."""
        # Combina textos relevantes
        texto_completo = (
            df.get('bio', '').fillna('') + ' ' + 
            df.get('nome_completo', '').fillna('')
        ).str.lower()
        
        # Inicializa colunas
        df['cidade'] = ''
        df['estado'] = ''
        
        # Busca por estados
        for sigla, pattern in zip(self.config.estados.keys(), self.regex_patterns['estados']):
            mask = texto_completo.str.contains(pattern, regex=True, na=False)
            df.loc[mask & (df['estado'] == ''), 'estado'] = sigla
        
        # Busca por cidades
        for cidade in self.config.capitais_cidades:
            mask = texto_completo.str.contains(cidade, na=False)
            df.loc[mask & (df['cidade'] == ''), 'cidade'] = cidade.title()
            
            # Associa estado se não definido
            if cidade in self.config.cidades_por_estado:
                estado = self.config.cidades_por_estado[cidade]
                df.loc[mask & (df['estado'] == ''), 'estado'] = estado
        
        return df
    
    def classificar_tipo_perfil_vetorizada(self, df: pd.DataFrame) -> pd.Series:
        """Classifica tipo de perfil (empresa/pessoa) de forma vetorizada."""
        # Combina textos relevantes
        texto_completo = (
            df.get('categoria', '').fillna('') + ' ' +
            df.get('bio', '').fillna('') + ' ' +
            df.get('nome_completo', '').fillna('')
        ).str.lower()
        
        # Calcula scores
        score_empresa = pd.Series([0] * len(df), index=df.index)
        score_pessoa = pd.Series([0] * len(df), index=df.index)
        
        # Score para empresa
        for palavra in self.config.palavras_chave_empresa:
            mask = texto_completo.str.contains(palavra, na=False)
            score_empresa += mask.astype(int)
        
        # Score para pessoa
        for palavra in self.config.palavras_chave_pessoa:
            mask = texto_completo.str.contains(palavra, na=False)
            score_pessoa += mask.astype(int)
        
        # Classificação final
        return np.where(score_empresa > score_pessoa, "Empresa / Comércio", "Pessoa / Criador")
    
    def identificar_estudante_vetorizada(self, df: pd.DataFrame) -> pd.Series:
        """Identifica estudantes de forma vetorizada."""
        texto_completo = (
            df.get('bio', '').fillna('') + ' ' +
            df.get('categoria', '').fillna('')
        ).str.lower()
        
        eh_estudante = pd.Series([False] * len(df), index=df.index)
        
        # Verifica padrões regex
        for pattern in self.regex_patterns['estudante_regex']:
            mask = texto_completo.str.contains(pattern, regex=True, na=False)
            eh_estudante |= mask
        
        # Verifica termos genéricos
        for pattern in self.regex_patterns['estudante_termos']:
            mask = texto_completo.str.contains(pattern, regex=True, na=False)
            eh_estudante |= mask
        
        # Verifica instituições
        for pattern in self.regex_patterns['estudante_instituicoes']:
            mask = texto_completo.str.contains(pattern, regex=True, na=False)
            eh_estudante |= mask
        
        # Verifica cursos
        for pattern in self.regex_patterns['estudante_cursos']:
            mask = texto_completo.str.contains(pattern, regex=True, na=False)
            eh_estudante |= mask
        
        return eh_estudante.map({True: "Sim", False: "Não"})
    
    def inferir_genero_vetorizada(self, df: pd.DataFrame) -> pd.Series:
        """Infere gênero baseado no primeiro nome de forma vetorizada."""
        # Extrai primeiro nome
        primeiro_nome = (
            df.get('nome_completo', '')
            .fillna('')
            .str.lower()
            .str.split(' ')
            .str[0]
        )
        
        # Classifica gênero
        genero = pd.Series(['Indefinido'] * len(df), index=df.index)
        
        # Feminino
        mask_feminino = primeiro_nome.isin(self.config.nomes_femininos)
        genero.loc[mask_feminino] = 'Feminino'
        
        # Masculino
        mask_masculino = primeiro_nome.isin(self.config.nomes_masculinos)
        genero.loc[mask_masculino] = 'Masculino'
        
        return genero
    
    def validar_dataframe(self, df: pd.DataFrame) -> bool:
        """Valida se o DataFrame possui as colunas necessárias."""
        colunas_obrigatorias = ['username']
        colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltando:
            self.logger.error(f"Colunas obrigatórias faltando: {colunas_faltando}")
            return False
        
        if df.empty:
            self.logger.error("DataFrame está vazio")
            return False
        
        return True
    
    def sanitizar_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica sanitização básica ao DataFrame."""
        self.logger.info("Iniciando sanitização dos dados...")
        
        # Remove duplicatas
        tamanho_original = len(df)
        df = df.drop_duplicates(subset=['username'], keep='first')
        duplicatas_removidas = tamanho_original - len(df)
        
        if duplicatas_removidas > 0:
            self.logger.info(f"Removidas {duplicatas_removidas} duplicatas")
        
        # Preenche valores nulos em colunas de texto
        colunas_texto = ['bio', 'categoria', 'nome_completo', 'endereco']
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].fillna('')
        
        self.logger.info("Sanitização concluída")
        return df
    
    def analisar_e_classificar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pipeline principal de análise e classificação."""
        self.logger.info("Iniciando pipeline de análise e classificação...")
        
        # Validação
        if not self.validar_dataframe(df):
            raise ValueError("DataFrame inválido")
        
        # Sanitização
        df = self.sanitizar_dataframe(df.copy())
        
        # Análise de influência
        if 'n_seguidores' in df.columns:
            self.logger.info("Processando dados de seguidores...")
            df['n_seguidores_num'] = self.converter_para_numero_vetorizado(df['n_seguidores'])
            df['nivel_influencia'] = self.classificar_nivel_influencia(df['n_seguidores_num'])
        
        if 'n_seguindo' in df.columns:
            df['n_seguindo_num'] = self.converter_para_numero_vetorizado(df['n_seguindo'])
        
        # Extração de localização
        self.logger.info("Extraindo informações de localização...")
        df = self.extrair_localizacao_vetorizada(df)
        
        # Classificação de tipo de perfil
        self.logger.info("Classificando tipos de perfil...")
        df['tipo_perfil'] = self.classificar_tipo_perfil_vetorizada(df)
        
        # Identificação de estudantes
        self.logger.info("Identificando estudantes...")
        df['eh_estudante'] = self.identificar_estudante_vetorizada(df)
        
        # Inferência de gênero
        self.logger.info("Inferindo gênero...")
        df['genero_inferido'] = self.inferir_genero_vetorizada(df)
        
        self.logger.info("✅ Análise concluída com sucesso!")
        return df
    
    def criar_nome_arquivo_seguro(self, nome: str) -> str:
        """Cria um nome de arquivo/pasta seguro."""
        return re.sub(r'[^\w\s-]', '', str(nome)).strip().replace(' ', '_')
    
    def salvar_segmentos(self, df: pd.DataFrame, base_path: Path, 
                        colunas_para_segmentar: List[str]) -> Dict[str, int]:
        """Salva segmentos do DataFrame e retorna estatísticas."""
        self.logger.info("Iniciando salvamento dos segmentos...")
        estatisticas = {}
        
        for coluna in colunas_para_segmentar:
            if coluna not in df.columns:
                self.logger.warning(f"Coluna '{coluna}' não encontrada. Pulando.")
                continue
            
            grupos = df.groupby(coluna)
            pasta_categoria = base_path / coluna.replace('_', ' ').title()
            pasta_categoria.mkdir(exist_ok=True)
            
            estatisticas[coluna] = {}
            
            for nome_grupo, df_grupo in grupos:
                if pd.isna(nome_grupo) or not nome_grupo:
                    continue
                
                nome_limpo = self.criar_nome_arquivo_seguro(nome_grupo)
                caminho_csv = pasta_categoria / f"{nome_limpo}.csv"
                
                try:
                    df_grupo.to_csv(caminho_csv, index=False, encoding='utf-8')
                    estatisticas[coluna][nome_grupo] = len(df_grupo)
                    self.logger.info(f"   - Salvando: {caminho_csv} ({len(df_grupo)} registros)")
                except Exception as e:
                    self.logger.error(f"Erro ao salvar {caminho_csv}: {e}")
        
        self.logger.info("✅ Salvamento dos segmentos concluído")
        return estatisticas


class GerenciadorConfiguracao:
    """Gerencia configurações do sistema."""
    
    @staticmethod
    def carregar_configuracao_padrao() -> ConfiguracaoAnalise:
        """Carrega configuração padrão."""
        return ConfiguracaoAnalise(
            arquivo_entrada="dados_avancados_curtidas_completo_sebraeto.csv",
            colunas_segmentacao=[
                'tipo_perfil', 'estado', 'cidade', 'eh_estudante', 
                'genero_inferido', 'nivel_influencia'
            ],
            palavras_chave_empresa=[
                'salão', 'beleza', 'estética', 'barbearia', 'loja', 'restaurante', 
                'delivery', 'oficial', 'store', 'shop', 'boutique', 'studio', 
                'clínica', 'consultório', 'agência', 'serviços', 'encomendas', 
                'pedidos', 'agendamento', 'orçamento', 'atacado', 'varejo', 
                'imóveis', 'advocacia', 'contabilidade', 'empresa', 'corporativo', 
                'negócios', 'ecommerce', 'marketplace', 'consultoria', 'academia', 'escola'
            ],
            palavras_chave_pessoa=[
                'blogueira', 'blogger', 'influencer', 'criador de conteúdo', 
                'atleta', 'artista', 'pessoal', 'public figure', 'figura pública', 
                'digital creator', 'modelo', 'creator', 'youtuber', 'tiktoker'
            ],
            capitais_cidades=[
                'palmas', 'goiânia', 'brasilia', 'são paulo', 'rio de janeiro', 
                'belo horizonte', 'salvador', 'fortaleza', 'recife', 'curitiba', 
                'porto alegre', 'manaus', 'belém', 'gurupi', 'araguaína', 
                'porto nacional', 'paraíso do tocantins'
            ],
            estados={
                'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
                'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 
                'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão',
                'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais',
                'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco',
                'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
                'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima',
                'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'
            },
            cidades_por_estado={
                'palmas': 'TO', 'gurupi': 'TO', 'araguaína': 'TO', 
                'porto nacional': 'TO', 'paraíso do tocantins': 'TO', 
                'goiânia': 'GO', 'brasilia': 'DF'
            },
            nomes_masculinos=[
                'josé', 'joão', 'antônio', 'francisco', 'carlos', 'paulo', 'pedro', 
                'lucas', 'luiz', 'marcos', 'luís', 'gabriel', 'rafael', 'daniel', 
                'marcelo', 'bruno', 'eduardo', 'felipe', 'andré', 'fernando', 
                'rodrigo', 'gustavo', 'guilherme', 'ricardo', 'tiago', 'sérgio', 'vinícius'
            ],
            nomes_femininos=[
                'maria', 'ana', 'francisca', 'antônia', 'adriana', 'juliana', 
                'márcia', 'fernanda', 'patrícia', 'aline', 'sandra', 'camila', 
                'amanda', 'bruna', 'jéssica', 'letícia', 'júlia', 'luciana', 
                'vanessa', 'mariana', 'gabriela', 'vera', 'vitória', 'larissa', 
                'cláudia', 'beatriz'
            ],
            palavras_chave_estudante={
                "TERMOS_GENERICOS": ['estudante', 'aluno', 'aluna', 'acadêmico', 'cursando', 'formando'],
                "INSTITUICOES": ['faculdade', 'universidade', 'escola', 'instituto', 'uf', 'ue', 'puc', 'uft', 'unitins', 'ifto'],
                "CURSOS": ['direito', 'medicina', 'engenharia', 'administração', 'adm'],
                "PADROES_REGEX": [r'\dº\s?período', r'\d\s?semestre', r'turma\s?\d+']
            }
        )
    
    @staticmethod
    def salvar_configuracao(config: ConfiguracaoAnalise, caminho: str):
        """Salva configuração em arquivo JSON."""
        config_dict = {
            'arquivo_entrada': config.arquivo_entrada,
            'colunas_segmentacao': config.colunas_segmentacao,
            'palavras_chave_empresa': config.palavras_chave_empresa,
            'palavras_chave_pessoa': config.palavras_chave_pessoa,
            'capitais_cidades': config.capitais_cidades,
            'estados': config.estados,
            'cidades_por_estado': config.cidades_por_estado,
            'nomes_masculinos': config.nomes_masculinos,
            'nomes_femininos': config.nomes_femininos,
            'palavras_chave_estudante': config.palavras_chave_estudante
        }
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)


def main():
    """Função principal."""
    # Configuração de caminhos
    dir_script = Path(__file__).parent
    dir_dados = dir_script.parent / "5-dadosTratados"
    arquivo_entrada = dir_dados / "dados_tratados_dados_avancados_curtidas_tratado_confresa_vila_rica_sao_felix_MT.csv"
    
    # Verifica se arquivo existe
    if not arquivo_entrada.exists():
        print(f"❌ Arquivo não encontrado: {arquivo_entrada}")
        return
    
    try:
        # Carrega configuração
        config = GerenciadorConfiguracao.carregar_configuracao_padrao()
        config.arquivo_entrada = str(arquivo_entrada)
        
        # Inicializa classificador
        classificador = ClassificadorSeguidores(config)
        
        # Carrega dados
        classificador.logger.info(f"Carregando dados: {arquivo_entrada}")
        df_original = pd.read_csv(arquivo_entrada)
        classificador.logger.info(f"Dados carregados: {len(df_original)} registros")
        
        # Executa análise
        df_analisado = classificador.analisar_e_classificar(df_original)
        
        # Salva resultado completo
        arquivo_saida = dir_script / "analise_completa_otimizada.csv"
        df_analisado.to_csv(arquivo_saida, index=False, encoding='utf-8')
        classificador.logger.info(f"🎉 Análise completa salva: {arquivo_saida}")
        
        # Salva segmentos
        estatisticas = classificador.salvar_segmentos(
            df_analisado, dir_script, config.colunas_segmentacao
        )
        
        # Exibe estatísticas
        print("\n📊 ESTATÍSTICAS DE SEGMENTAÇÃO:")
        for coluna, grupos in estatisticas.items():
            print(f"\n{coluna.replace('_', ' ').title()}:")
            for grupo, quantidade in grupos.items():
                print(f"  - {grupo}: {quantidade} registros")
        
        print(f"\n✅ Processamento concluído com sucesso!")
        print(f"📁 Arquivos salvos em: {dir_script}")
        
    except Exception as e:
        logging.error(f"❌ Erro durante processamento: {e}")
        raise


if __name__ == "__main__":
    main()
