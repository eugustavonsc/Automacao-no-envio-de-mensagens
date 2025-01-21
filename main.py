"""
==================================================
    Envio de Mensagens Automático
    Criado por: Gustavo Nascimento (GN)
    Versão: 1.0
==================================================
Copyright (C) [2025], Gustavo Nascimento
Todos os direitos reservados.

Este software é distribuído sob a licença MIT.
Para mais detalhes, consulte o arquivo LICENSE no diretório
do projeto ou visite: https://opensource.org/licenses/MIT

Este software foi desenvolvido para facilitar o envio de mensagens
em massa de forma eficiente e organizada. O uso deste programa está
sujeito aos termos da licença acima mencionada.
==================================================
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import time
import threading
from queue import Queue
import re

# Variável para armazenar o caminho do config.env
config_env_path = None

# Função para carregar as variáveis de ambiente
def carregar_config_env(caminho_config):
    global config_env_path
    config_env_path = Path(caminho_config)
    if not config_env_path.is_file():
        messagebox.showerror("Erro", "Arquivo config.env não encontrado!")
        return False

    load_dotenv(config_env_path)
    return True

# Função para enviar mensagem
def enviar_mensagem_texto(numero, mensagem, abrir_ticket=1, id_fila=22):
    api_url = os.getenv("API_URL")
    api_token = os.getenv("API_TOKEN")
    
    if not api_url or not api_token:
        raise ValueError("API_URL ou API_TOKEN não estão definidos no config.env.")
    
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
            response_data = response.json()
            nome = response_data.get("ticket", {}).get("contact", {}).get("name", "Desconhecido")
            status_envio = response_data.get("mensagem", "Mensagem enviada")
            return {"nome": nome, "numero": numero, "status": status_envio}
        else:
            return {"nome": "N/A", "numero": numero, "status": f"Erro {response.status_code}: {response.text}"}
    except Exception as e:
        return {"nome": "N/A", "numero": numero, "status": f"Erro: {e}"}

# Função que executa o envio em threads
def processar_envio_thread(queue, resultados, mensagem_universal):
    while not queue.empty():
        numero = queue.get()
        if numero:
            resultado = enviar_mensagem_texto(numero, mensagem_universal)
            resultados.append(resultado)
            time.sleep(0.5)  # Evitar sobrecarregar a API
        queue.task_done()

# Função para padronizar os números
def padronizar_numero(numero):
    numero = re.sub(r"[^\d]", "", numero)  # Remove caracteres não numéricos
    if len(numero) >= 10:  # Verifica se tem ao menos 10 dígitos (DDD + número)
        return f"55{numero}"  # Adiciona o código do Brasil
    return None

# Processa a planilha e envia mensagens
def processar_planilha(caminho_planilha, caminho_mensagem):
    try:
        with open(caminho_mensagem, "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()

        df = pd.read_excel(caminho_planilha, usecols=["numero"])
        numeros = df["numero"].drop_duplicates().dropna()
        numeros_padronizados = numeros.apply(padronizar_numero).dropna()

        queue = Queue()
        resultados = []

        # Adiciona os números à fila
        for numero in numeros_padronizados:
            queue.put(numero)

        # Cria threads para processar o envio
        threads = []
        for _ in range(10):  # Número de threads 
            thread = threading.Thread(target=processar_envio_thread, args=(queue, resultados, mensagem_universal))
            thread.start()
            threads.append(thread)

        # Aguarda todas as threads terminarem
        for thread in threads:
            thread.join()

        # Salva os resultados no arquivo Excel
        resultados_df = pd.DataFrame(resultados)
        resultados_df.to_excel("resultados_envio.xlsx", index=False)
        messagebox.showinfo("Concluído", "Mensagens enviadas com sucesso! Resultados salvos em 'resultados_envio.xlsx'.")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao processar a planilha: {e}")

# Selecionar o arquivo config.env
def selecionar_config_env():
    caminho = filedialog.askopenfilename(filetypes=[("Arquivos ENV", "*.env")])
    if caminho:
        sucesso = carregar_config_env(caminho)
        if sucesso:
            messagebox.showinfo("Configuração", "Config.env carregado com sucesso!")

# Selecionar outros arquivos
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
    processar_planilha(caminho_planilha, caminho_mensagem)

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

# Botão de início
tk.Button(janela, text="Iniciar Envio", command=iniciar_envio, bg="green", fg="white").grid(row=3, column=1, padx=10, pady=10)

# Botão "Sobre"
tk.Button(janela, text="Sobre", command=exibir_sobre, bg="gray", fg="white").grid(row=4, column=1, padx=10, pady=10)

janela.mainloop()
