import pandas as pd
import os
import re

# Palavras-chave para classificação
CLASSES = {
    'medico': [r'medico', r'médico', r'dr\b', r'dr\.', r'doutor', r'doutora', r'clinica médica', r'consultorio medico'],
    'dentista': [r'dentista', r'odontolog', r'ortodont', r'consultorio odontologico', r'clinica odontologica'],
    'psicologo': [r'psicolog', r'psicoterapia', r'psicoterapeuta'],
    'fisioterapeuta': [r'fisioterap', r'fisio'],
    'nutricionista': [r'nutricionist', r'nutrição', r'nutri'],
    'personal_trainer': [r'personal trainer', r'personal', r'treinador', r'coach fitness'],
    'esteticista': [r'esteticista', r'estetica', r'estética', r'limpeza de pele', r'procedimento estético'],
    'cabeleireiro': [r'cabeleireiro', r'salão de beleza', r'salão', r'corte de cabelo', r'escova', r'coloracao'],
    'barbeiro': [r'barbeiro', r'barbearia'],
    'manicure_pedicure': [r'manicure', r'pedicure', r'unhas', r'esmalteria'],
    'massoterapeuta': [r'massoterapeuta', r'massagem', r'massagista'],
    'fotografo': [r'fotografo', r'fotógrafo', r'fotografia', r'estudio fotografico'],
    'professor_particular': [r'professor', r'aula particular', r'aulas particulares', r'música', r'idiomas', r'reforço escolar'],
    'advogado': [r'advogado', r'advocacia', r'consultoria juridica', r'consulta juridica', r'escritorio de advocacia'],
    'contador': [r'contador', r'contabilidade', r'consultoria contábil', r'consultoria contábil'],
    'terapeuta_ocupacional': [r'terapeuta ocupacional', r'terapia ocupacional'],
    'veterinario': [r'veterinario', r'veterinária', r'clínica veterinária', r'pet shop'],
    'clinica_exames': [r'laboratorio', r'exames laboratoriais', r'analises clinicas', r'clínica de exames'],
    'oficina_mecanica': [r'oficina mecânica', r'mecânico', r'revisão automotiva', r'manutenção automotiva', r'auto center'],
    'tecnico_informatica': [r'técnico de informática', r'técnico informática', r'informática', r'suporte técnico', r'computador', r'notebook'],
    'pilates': [r'pilates'],
    'dr': [r'\bdr\b', r'\bdra\b', r'dr\.', r'dra\.', r'doutor', r'doutora'],
    'clinica': [r'clinica', r'clínica'],
}

PASTA_SAIDA = os.path.join(os.path.dirname(__file__), 'classificados')
ARQUIVO_ENTRADA = os.path.join(os.path.dirname(__file__), 'superCSV.csv')

# Carrega o CSV consolidado
print(f"Lendo arquivo: {ARQUIVO_ENTRADA}")
df = pd.read_csv(ARQUIVO_ENTRADA)

# Função para buscar palavras-chave em colunas relevantes
def classificar_linha(row):
    texto = str(row.get('nome_completo', '')) + ' ' + str(row.get('username', ''))
    texto = texto.lower()
    for classe, keywords in CLASSES.items():
        for kw in keywords:
            if re.search(kw, texto):
                return classe
    return 'outros'

# Aplica classificação
print("Classificando registros...")
df['classe'] = df.apply(classificar_linha, axis=1)

# Salva um CSV para cada classe
for classe in df['classe'].unique():
    df_classe = df[df['classe'] == classe]
    caminho_saida = os.path.join(PASTA_SAIDA, f'{classe}.csv')
    df_classe.to_csv(caminho_saida, index=False, encoding='utf-8')
    print(f"Arquivo salvo: {caminho_saida} ({len(df_classe)} registros)")

print("Classificação concluída!")
