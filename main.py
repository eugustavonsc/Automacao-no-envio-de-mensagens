import pandas as pd
import requests
from dotenv import load_dotenv
import os
import time

# Carregar variáveis de ambiente do arquivo config.env
load_dotenv("config.env")

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
if not API_URL or not API_TOKEN:
    raise ValueError("API_URL ou API_TOKEN não foram definidos. Verifique o arquivo config.env.")

HEADERS = {
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
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            print(f"Mensagem enviada com sucesso para {numero}: {response.json()}")
            return {"numero": numero, "status": "Sucesso"}
        else:
            print(f"Erro ao enviar mensagem para {numero}: {response.status_code}, {response.text}")
            return {"numero": numero, "status": f"Erro {response.status_code}: {response.text}"}
    except Exception as e:
        print(f"Erro ao processar o envio para {numero}: {e}")
        return {"numero": numero, "status": f"Erro: {e}"}

def processar_planilha_e_enviar_mensagens(caminho_planilha, mensagem_universal):

    try:
        # Ler a planilha
        df = pd.read_excel(caminho_planilha, usecols=["numero"])

        # Verificar se a coluna 'numero' está presente
        if "numero" not in df.columns:
            print("A planilha deve conter uma coluna chamada 'numero'.")
            return

        # Remover duplicatas e valores inválidos
        numeros = df["numero"].drop_duplicates().dropna().astype(str).str.strip()

        resultados = []
        for numero in numeros:
            resultado = enviar_mensagem_texto(numero, mensagem_universal)
            resultados.append(resultado)

            # Pausa entre os envios para evitar sobrecarga
            time.sleep(0.5)  # Ajuste conforme necessário

        # Salvar os resultados em um arquivo Excel
        resultados_df = pd.DataFrame(resultados)
        resultados_df.to_excel("resultados_envio.xlsx", index=False)
        print("Processo concluído. Resultados salvos em 'resultados_envio.xlsx'.")

    except Exception as e:
        print(f"Erro ao processar a planilha: {e}")

if __name__ == "__main__":
    # Carregar a mensagem universal do arquivo mensagem.txt
    try:
        with open("mensagem.txt", "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()
    except FileNotFoundError:
        raise ValueError("O arquivo mensagem.txt não foi encontrado. Verifique se ele existe e está no diretório correto.")

    # Caminho da planilha com os números de clientes
    caminho_planilha = "clientes.xlsx"

    # Processar a planilha e enviar mensagens
    processar_planilha_e_enviar_mensagens(caminho_planilha, mensagem_universal)
