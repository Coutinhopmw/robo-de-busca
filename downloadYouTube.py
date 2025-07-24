from pytube import YouTube
from pytube.exceptions import PytubeError

# ===================================================================
#    ↓↓↓ COLOQUE A URL CORRETA DO VÍDEO DO YOUTUBE AQUI ↓↓↓
# ===================================================================
video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Exemplo de URL válida. Substitua!

try:
    print("Conectando ao YouTube...")
    
    # Cria um objeto YouTube com a URL do vídeo
    yt = YouTube(video_url)

    print(f"Título: {yt.title}")
    print(f"Autor: {yt.author}")
    print("Buscando a melhor resolução...")

    # Seleciona o stream com a maior resolução que seja "progressivo" (vídeo + áudio)
    stream = yt.streams.get_highest_resolution()

    if stream:
        print(f"Baixando: {yt.title} ({stream.resolution})")
        print(f"Tamanho: {round(stream.filesize / (1024*1024), 2)} MB")
        
        # Baixa o vídeo para o diretório onde o script está
        print("Iniciando o download...")
        stream.download()
        
        print("\nDownload concluído com sucesso!")
    else:
        print("Nenhum stream com vídeo e áudio foi encontrado.")

# Captura erros específicos da pytube e outros erros de conexão
except PytubeError as e:
    print(f"\nOcorreu um erro específico da Pytube: {e}")
    print("Verifique se a URL está correta ou tente atualizar a biblioteca com: pip install --upgrade pytube")
except Exception as e:
    print(f"\nOcorreu um erro inesperado: {e}")
    print("A causa mais provável é uma URL inválida. Verifique o link do vídeo.")