import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import requests
from dotenv import load_dotenv
import os
import time

# Carregar variáveis de ambiente
load_dotenv("config.env")

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
if not API_URL or not API_TOKEN:
    raise ValueError("API_URL ou API_TOKEN não foram definidos. Verifique o arquivo config.env.")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def normalizar_numero(numero):
    try:
        numero = str(numero).strip()
        if numero.endswith(".0"):
            numero = numero[:-2]
        return numero
    except Exception:
        return None

def enviar_mensagem_texto(numero, mensagem, abrir_ticket=1, id_fila=22):
    payload = {
        "number": numero,
        "openTicket": str(abrir_ticket),
        "queueId": str(id_fila),
        "body": mensagem
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            return {"numero": numero, "status": "Sucesso"}
        else:
            return {"numero": numero, "status": f"Erro {response.status_code}: {response.text}"}
    except Exception as e:
        return {"numero": numero, "status": f"Erro: {e}"}

def processar_planilha(caminho_planilha, caminho_mensagem):
    try:
        with open(caminho_mensagem, "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()

        df = pd.read_excel(caminho_planilha, usecols=["numero"])
        numeros = df["numero"].drop_duplicates().dropna().apply(normalizar_numero)

        resultados = []
        for numero in numeros:
            if numero:
                resultado = enviar_mensagem_texto(numero, mensagem_universal)
                resultados.append(resultado)
                time.sleep(0.5)

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
    caminho_planilha = entrada_var.get()
    caminho_mensagem = mensagem_var.get()
    if not caminho_planilha or not caminho_mensagem:
        messagebox.showwarning("Aviso", "Selecione todos os arquivos necessários!")
        return
    processar_planilha(caminho_planilha, caminho_mensagem)


janela = tk.Tk()
janela.title("Envio de Mensagens")

entrada_var = tk.StringVar()
mensagem_var = tk.StringVar()

tk.Label(janela, text="Planilha de Números:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=entrada_var, width=50).grid(row=0, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_entrada).grid(row=0, column=2, padx=10, pady=5)

tk.Label(janela, text="Arquivo de Mensagem:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
tk.Entry(janela, textvariable=mensagem_var, width=50).grid(row=1, column=1, padx=10, pady=5)
tk.Button(janela, text="Selecionar", command=selecionar_arquivo_mensagem).grid(row=1, column=2, padx=10, pady=5)

tk.Button(janela, text="Iniciar Envio", command=iniciar_envio, bg="green", fg="white").grid(row=2, column=1, padx=10, pady=10)

janela.mainloop()
