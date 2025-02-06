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

# Variável global para armazenar o caminho do arquivo config.env
config_env_path = None

def carregar_config_env(caminho_config):
    """
    Carrega o arquivo config.env e valida as variáveis de ambiente.
    """
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
    """
    Seleciona o arquivo config.env via diálogo e tenta carregá-lo.
    """
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos ENV", "*.env")])
    if caminho:
        sucesso = carregar_config_env(caminho)
        if not sucesso:
            messagebox.showerror("Erro", "Erro ao carregar o arquivo config.env.")

def enviar_mensagem_texto(numero, mensagem, abrir_ticket=1, id_fila=47):
    """
    Envia uma mensagem para o número especificado usando a API.
    """
    api_url = os.getenv("API_URL")
    api_token = os.getenv("API_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "number": numero,
        "openTicket": str(abrir_ticket),
        "queueId": str(id_fila),
        "body": mensagem
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                if not isinstance(response_data, dict):
                    return {"nome": "N/A", "numero": numero, "status": "Erro: Resposta inesperada da API"}
                
                nome = response_data.get("ticket", {}).get("contact", {}).get("name", "Desconhecido")
                status_envio = response_data.get("mensagem", "Mensagem enviada")
                return {"nome": nome, "numero": numero, "status": status_envio}
            except ValueError:
                return {"nome": "N/A", "numero": numero, "status": "Erro: Resposta inválida da API"}
        else:
            return {"nome": "N/A", "numero": numero, "status": f"Erro {response.status_code}: {response.text}"}
    except requests.RequestException as e:
        return {"nome": "N/A", "numero": numero, "status": f"Erro de requisição: {e}"}
    except Exception as e:
        return {"nome": "N/A", "numero": numero, "status": f"Erro inesperado: {e}"}

def processar_envio_thread(queue, resultados, mensagem_universal, progress_bar, total_numeros):
    """
    Processa o envio das mensagens em uma thread separada.
    """
    while not queue.empty():
        numero = queue.get()
        if numero:
            resultado = enviar_mensagem_texto(numero, mensagem_universal)
            resultados.append(resultado)
            time.sleep(0.5)  # Evitar sobrecarregar a API
            progress_bar.step(100 / total_numeros)  # Atualiza a barra de progresso
            progress_bar.update_idletasks()  # Atualiza a UI sem bloqueá-la
        queue.task_done()

def padronizar_numero(numero):
    """
    Padroniza o número, removendo caracteres inválidos e adicionando o código do Brasil.
    """
    numero = re.sub(r"[^\d]", "", numero)
    if len(numero) >= 10:
        return f"55{numero}"
    return None

def processar_planilha(caminho_planilha, caminho_mensagem, progress_bar):
    """
    Processa a planilha de números e envia as mensagens.
    """
    try:
        with open(caminho_mensagem, "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()

        df = pd.read_excel(caminho_planilha, usecols=["numero"])
        numeros = df["numero"].drop_duplicates().dropna()
        numeros_padronizados = numeros.apply(padronizar_numero).dropna()

        queue = Queue()
        resultados = []
        total_numeros = len(numeros_padronizados)

        for numero in numeros_padronizados:
            queue.put(numero)

        progress_bar["maximum"] = 100  # Define o máximo da barra como 100%

        threads = []
        for _ in range(10):  # Número de threads
            thread = threading.Thread(
                target=processar_envio_thread,
                args=(queue, resultados, mensagem_universal, progress_bar, total_numeros)
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        resultados_df = pd.DataFrame(resultados)
        resultados_df.to_excel("resultados_envio.xlsx", index=False)
        messagebox.showinfo("Concluído", "Mensagens enviadas com sucesso! Resultados salvos em 'resultados_envio.xlsx'.")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao processar a planilha: {e}")

def selecionar_arquivo_entrada():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos Excel", "*.xlsx")])
    entrada_var.set(caminho)

def selecionar_arquivo_mensagem():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Texto", "*.txt")])
    mensagem_var.set(caminho)

def iniciar_envio():
    if not config_env_path:
        messagebox.showwarning("Aviso", "Selecione um arquivo config.env antes de continuar.")
        return

    caminho_planilha = entrada_var.get()
    caminho_mensagem = mensagem_var.get()
    if not caminho_planilha or not caminho_mensagem:
        messagebox.showwarning("Aviso", "Selecione todos os arquivos necessários!")
        return

    progress_bar["value"] = 0
    threading.Thread(target=processar_planilha, args=(caminho_planilha, caminho_mensagem, progress_bar)).start()

def exibir_sobre():
    mensagem = (
        "==================================================\n"
        "    Envio de Mensagens Automático\n"
        "    Criado por: Gustavo Nascimento (GN)\n"
        "    Versão: 1.0\n"
        "==================================================\n"
        "Copyright (C) [2025], Gustavo Nascimento\n"
        "Todos os direitos reservados.\n\n"
        "Este software é distribuído sob a licença MIT.\n"
        "Para mais detalhes, consulte o arquivo LICENSE no diretório\n"
        "do projeto ou visite: https://opensource.org/licenses/MIT\n"
    )
    messagebox.showinfo("Sobre", mensagem)

# Criar interface gráfica
janela = tk.Tk()
janela.title("Envio de Mensagens")

entrada_var = tk.StringVar()
mensagem_var = tk.StringVar()

# Configuração do config.env
tk.Button(janela, text="Selecionar Config.env", command=selecionar_config_env, bg="blue", fg="white").grid(row=0, column=1, padx=10, pady=10)

# Seleção de arquivos
tk.Label(janela, text="Planilha de Números:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=entrada_var, width=50).grid(row=1, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_entrada).grid(row=1, column=2, padx=10, pady=5)

tk.Label(janela, text="Arquivo de Mensagem:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=mensagem_var, width=50).grid(row=2, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_mensagem).grid(row=2, column=2, padx=10, pady=5)

# Barra de progresso
progress_bar = ttk.Progressbar(janela, orient="horizontal", mode="determinate", length=400)
progress_bar.grid(row=3, column=1, pady=10)

# Botão de início
tk.Button(janela, text="Iniciar Envio", command=iniciar_envio, bg="green", fg="white").grid(row=4, column=1, padx=10, pady=10)

# Botão "Sobre"
tk.Button(janela, text="Sobre", command=exibir_sobre, bg="gray", fg="white").grid(row=5, column=1, padx=10, pady=10)

janela.mainloop()
