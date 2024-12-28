import pandas as pd
import requests
from dotenv import load_dotenv
import os

load_dotenv("config.env")

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
if not API_URL or not API_TOKEN:
    raise ValueError("API_URL ou API_TOKEN não foram definidos. Verifique o arquivo config.env.")


headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def enviar_mensagem_texto(numero, mensagem, abrir_ticket=1, id_fila=22):
    payload = {
        "number": numero,
        "openTicket": str(abrir_ticket),
        "queueId": str(id_fila),
        "body": mensagem
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Mensagem enviada com sucesso para {numero}: {response.json()}")
        else:
            print(f"Erro ao enviar mensagem para {numero}: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Erro ao processar o envio para {numero}: {e}")


def processar_planilha_e_enviar_mensagens(caminho_planilha, mensagem_universal):
    try:
        
        df = pd.read_excel(caminho_planilha)

        
        if "numero" not in df.columns:
            print("A planilha deve conter uma coluna chamada 'numero'.")
            return

        
        for _, row in df.iterrows():
            numero = str(row["numero"]).strip()  
            enviar_mensagem_texto(numero, mensagem_universal)

    except Exception as e:
        print(f"Erro ao processar a planilha: {e}")


try:
    with open("mensagem.txt", "r", encoding="utf-8") as file:
        mensagem_universal = file.read()
except FileNotFoundError:
    raise ValueError("O arquivo mensagem.txt não foi encontrado. Verifique se ele existe e está no diretório correto.")



caminho_planilha = "clientes.xlsx"


processar_planilha_e_enviar_mensagens(caminho_planilha, mensagem_universal)
