# Automação no Envio de Mensagens © 2025 by Gustavo Nascimento  
# Licenciado sob CC BY-NC-ND 4.0. Para detalhes, visite https://creativecommons.org/licenses/by-nc-nd/4.0/
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import time
import threading
from queue import Queue
import re
from mimetypes import guess_type

# Variável global para armazenar o caminho do arquivo config.env
config_env_path = None

# ==================================================
# Funções de Configuração
# ==================================================
def carregar_config_env(caminho_config):
    global config_env_path
    config_env_path = Path(caminho_config)

    if not config_env_path.is_file():
        messagebox.showerror("Erro", "Arquivo config.env não encontrado!")
        return False

    load_dotenv(dotenv_path=config_env_path)

    api_url = os.getenv("API_URL")
    api_token = os.getenv("API_TOKEN")
    if not api_url or not api_token:
        messagebox.showerror(
            "Erro",
            "Variáveis API_URL ou API_TOKEN não foram carregadas do config.env. Verifique o arquivo."
        )
        return False

    messagebox.showinfo("Sucesso", "Arquivo config.env carregado com sucesso!")
    return True

def selecionar_config_env():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos ENV", "*.env")])
    if caminho:
        sucesso = carregar_config_env(caminho)
        if not sucesso:
            messagebox.showerror("Erro", "Erro ao carregar o arquivo config.env.")

def detectar_tipo_mime(caminho_arquivo):
    """
    Detecta o tipo MIME de um arquivo com base na extensão.
    """
    tipo_mime, _ = guess_type(caminho_arquivo)
    return tipo_mime or "application/octet-stream" 

# ==================================================
# Funções de Envio de Mensagens
# ==================================================
def enviar_mensagem_texto(numero, mensagem, abrir_ticket=0, ):  # Alterado para não abrir ticket
    api_url = os.getenv("API_URL")
    api_token = os.getenv("API_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "number": numero,
        "openTicket": str(abrir_ticket),
        "body": mensagem
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                return {"status": "Enviado", "detalhes": "Mensagem enviada com sucesso"}
            except ValueError:
                return {"status": "Erro", "detalhes": "Resposta inválida da API"}
        else:
            return {"status": "Erro", "detalhes": f"Erro {response.status_code}: {response.text}"}
    except requests.RequestException as e:
        return {"status": "Erro", "detalhes": f"Erro de requisição: {e}"}
    except Exception as e:
        return {"status": "Erro", "detalhes": f"Erro inesperado: {e}"}

def enviar_mensagem_midia(numero, mensagem, caminho_arquivo, abrir_ticket=0, id_fila=0):  # Alterado para não abrir ticket
    api_url = os.getenv("API_URL")
    api_token = os.getenv("API_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Origin": "https://sac.lifthubsolucoes.com.br",
        "Referer": "https://sac.lifthubsolucoes.com.br/",
    }

    try:
        with open(caminho_arquivo, "rb") as arquivo:
            tipo_mime = detectar_tipo_mime(caminho_arquivo)
            
            data = {
                "number": numero,
                "openTicket": str(abrir_ticket),
                "queueId": str(id_fila),
                "body": mensagem
            }

            files = {
                "medias": (
                    os.path.basename(caminho_arquivo),
                    arquivo,
                    tipo_mime
                )
            }

            response = requests.post(api_url, headers=headers, data=data, files=files)
            
            if response.status_code == 200:
                return {"status": "Enviado", "detalhes": "Mensagem com mídia enviada com sucesso"}
            else:
                return {"status": "Erro", "detalhes": f"Erro {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "Erro", "detalhes": f"Erro inesperado: {e}"}

# ==================================================
# Funções de Processamento
# ==================================================
def processar_envio_thread(queue, df, mensagem_universal, progress_bar, total_numeros, envia_midia, caminho_imagem):
    while not queue.empty():
        index, row = queue.get()
        numero = padronizar_numero(row['numero'])
        
        if numero:
            if envia_midia and caminho_imagem.strip():
                resultado = enviar_mensagem_midia(numero, mensagem_universal, caminho_imagem)
            else:
                resultado = enviar_mensagem_texto(numero, mensagem_universal)
            
            # Atualiza a planilha diretamente
            df.at[index, 'status_envio'] = resultado['status']
            df.at[index, 'detalhes_envio'] = resultado['detalhes']
            
            time.sleep(0.5)
            progress_bar.step(100 / total_numeros)
            progress_bar.update_idletasks()
        queue.task_done()

def padronizar_numero(numero):
    numero = re.sub(r"[^\d]", "", str(numero))
    if len(numero) >= 10:
        return f"55{numero}"
    return None

def processar_planilha(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar):
    try:
        with open(caminho_mensagem, "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()

        envia_midia = bool(caminho_imagem.strip()) if caminho_imagem else False

        # Carrega a planilha mantendo todos os dados originais
        df = pd.read_excel(caminho_planilha)
        
        # Verifica se as colunas de status já existem, se não, cria
        if 'status_envio' not in df.columns:
            df['status_envio'] = ''
        if 'detalhes_envio' not in df.columns:
            df['detalhes_envio'] = ''
        
        # Filtra números válidos
        numeros_validos = df[df['numero'].notna()]
        total_numeros = len(numeros_validos)

        queue = Queue()
        for index, row in numeros_validos.iterrows():
            queue.put((index, row))

        progress_bar["maximum"] = 100

        threads = []
        for _ in range(10):  # Número de threads
            thread = threading.Thread(
                target=processar_envio_thread,
                args=(queue, df, mensagem_universal, progress_bar, total_numeros, envia_midia, caminho_imagem)
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Salva a planilha original com as novas colunas
        df.to_excel(caminho_planilha, index=False)
        messagebox.showinfo("Concluído", f"Processo finalizado! Planilha atualizada em: {caminho_planilha}")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao processar a planilha: {e}")

# ==================================================
# Funções de Interface (mantidas iguais)
# ==================================================
def selecionar_arquivo_entrada():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos Excel", "*.xlsx")])
    entrada_var.set(caminho)

def selecionar_arquivo_mensagem():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Texto", "*.txt")])
    mensagem_var.set(caminho)

def selecionar_arquivo_imagem():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Imagem", "*.jpg *.jpeg *.png *.gif")])
    imagem_var.set(caminho)

def iniciar_envio():
    if not config_env_path:
        messagebox.showwarning("Aviso", "Selecione um arquivo config.env antes de continuar.")
        return

    caminho_planilha = entrada_var.get()
    caminho_mensagem = mensagem_var.get()
    caminho_imagem = imagem_var.get()

    if not caminho_planilha or not caminho_mensagem:
        messagebox.showwarning("Aviso", "Selecione todos os arquivos necessários!")
        return

    progress_bar["value"] = 0
    threading.Thread(
        target=processar_planilha, 
        args=(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar)
    ).start()

def exibir_sobre():
    mensagem = (
        "==================================================\n"
        "    Envio de Mensagens Automático\n"
        "    Criado por: Gustavo Nascimento (GN)\n"
        "    Versão: 2.0\n"
        "==================================================\n"
        "Copyright (C) [2025], Gustavo Nascimento\n"
        "Todos os direitos reservados.\n\n"
        "Este projeto está licenciado sob a [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International](LICENSE).\n"
        "Você pode compartilhá-lo, mas **não pode**: \n"
        "- Usar para fins comerciais. \n"
        "- Modificar ou criar obras derivadas. \n"
    )
    messagebox.showinfo("Sobre", mensagem)

# ==================================================
# Configuração da Interface Gráfica
# ==================================================
janela = tk.Tk()
janela.title("Envio de Mensagens")

# Variáveis de controle
entrada_var = tk.StringVar()
mensagem_var = tk.StringVar()
imagem_var = tk.StringVar()

# Componentes da interface
tk.Button(janela, text="Selecionar Config.env", command=selecionar_config_env, bg="blue", fg="white").grid(row=0, column=1, padx=10, pady=10)

# Seleção de planilha
tk.Label(janela, text="Planilha de Números:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=entrada_var, width=50).grid(row=1, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_entrada).grid(row=1, column=2, padx=10, pady=5)

# Seleção de mensagem
tk.Label(janela, text="Arquivo de Mensagem:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=mensagem_var, width=50).grid(row=2, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_mensagem).grid(row=2, column=2, padx=10, pady=5)

# Seleção de imagem
tk.Label(janela, text="Arquivo de Imagem:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=imagem_var, width=50).grid(row=3, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_imagem).grid(row=3, column=2, padx=10, pady=5)

# Barra de progresso
progress_bar = ttk.Progressbar(janela, orient="horizontal", mode="determinate", length=400)
progress_bar.grid(row=4, column=1, pady=10)

# Botões de ação
tk.Button(janela, text="Iniciar Envio", command=iniciar_envio, bg="green", fg="white").grid(row=5, column=1, padx=10, pady=10)
tk.Button(janela, text="Sobre", command=exibir_sobre, bg="gray", fg="white").grid(row=6, column=1, padx=10, pady=10)

janela.mainloop()