# Automação no Envio de Mensagens © 2025 by Gustavo Nascimento
# Licenciado sob CC BY-NC-ND 4.0. Para detalhes, visite https://creativecommons.org/licenses/by-nc-nd/4.0/
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText # Para um log mais detalhado no futuro
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
import logging
import random ### ALTERAÇÃO INÍCIO ### (Importamos a biblioteca random)

# Configuração de logging avançado
log_path = Path(__file__).parent / 'envio_mensagens.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(threadName)s %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('EnvioMensagens')

# --- Variáveis Globais ---
config_env_path_global = None
api_client_global = None

# --- Classe para Cliente da API ---
class APIClient:
    """
    Encapsula a lógica de comunicação com a API de envio de mensagens.
    """
    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.api_token = api_token
        if not self.api_url or not self.api_token:
            raise ValueError("API URL e API Token são obrigatórios para o cliente API.")
        self.base_headers = {"Authorization": f"Bearer {self.api_token}"}

    def enviar_mensagem_texto(self, numero, mensagem, abrir_ticket=1, id_fila=203):
        """
        Envia uma mensagem de texto simples, abrindo ticket e fila.
        Retorna um dicionário com 'status' e 'detalhes'.
        """
        headers = {**self.base_headers, "Content-Type": "application/json"}
        payload = {
            "number": numero,
            "openTicket": str(abrir_ticket), # Sempre 1
            "queueId": str(id_fila),       # Sempre 203
            "body": mensagem
        }
        logger.info(f"[TEXTO] Enviando para {numero} | Payload: {payload}")
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=25)
            logger.info(f"[TEXTO] Resposta HTTP {response.status_code} | Conteúdo: {response.text}")
            response.raise_for_status()
            try:
                response_data = response.json()
                logger.info(f"[TEXTO] Resposta JSON: {response_data}")
                return {"status": "Enviado", "detalhes": response_data.get("message", "Mensagem enviada com sucesso")}
            except ValueError:
                logger.warning(f"[TEXTO] Resposta não-JSON: {response.text}")
                if response.text:
                    return {"status": "Enviado?", "detalhes": f"Resposta não-JSON, mas status {response.status_code}: {response.text[:100]}"}
                return {"status": "Enviado", "detalhes": f"Mensagem enviada (status {response.status_code}), resposta vazia."}
        except requests.HTTPError as http_err:
            logger.error(f"[TEXTO] Erro HTTP: {http_err.response.status_code} | {http_err.response.text}")
            return {"status": "Erro HTTP", "detalhes": f"Erro {http_err.response.status_code}: {http_err.response.text}"}
        except requests.RequestException as req_err:
            logger.error(f"[TEXTO] Erro de Requisição: {req_err}")
            return {"status": "Erro de Requisição", "detalhes": f"Erro de conexão/timeout: {req_err}"}
        except Exception as e:
            logger.exception(f"[TEXTO] Erro inesperado ao enviar mensagem para {numero}")
            return {"status": "Erro Inesperado", "detalhes": f"Erro desconhecido: {e}"}

    def enviar_mensagem_midia(self, numero, mensagem, caminho_arquivo, abrir_ticket=1, id_fila=203):
        """
        Envia uma mensagem com arquivo de mídia.
        Retorna um dicionário com 'status' e 'detalhes'.
        """
        headers = {
            **self.base_headers,
            "Origin": "https://sac.lifthubsolucoes.com.br",
            "Referer": "https://sac.lifthubsolucoes.com.br/",
        }
        logger.info(f"[MIDIA] Enviando para {numero} | Arquivo: {caminho_arquivo} | Payload: mensagem='{mensagem}', abrir_ticket=1, id_fila=203")
        try:
            with open(caminho_arquivo, "rb") as arquivo_midia:
                tipo_mime = detectar_tipo_mime(caminho_arquivo)
                data_payload = {
                    "number": numero,
                    "openTicket": str(abrir_ticket),
                    "queueId": str(id_fila),
                    "caption": mensagem  # Corrigido para caption
                }
                files_payload = {
                    "medias": (
                        os.path.basename(caminho_arquivo),
                        arquivo_midia,
                        tipo_mime
                    )
                }
                logger.info(f"[MIDIA] Data: {data_payload} | Files: {files_payload['medias'][0]}, {files_payload['medias'][2]}")
                response = requests.post(self.api_url, headers=headers, data=data_payload, files=files_payload, timeout=30)
                logger.info(f"[MIDIA] Resposta HTTP {response.status_code} | Conteúdo: {response.text}")
                response.raise_for_status()
                try:
                    response_data = response.json()
                    logger.info(f"[MIDIA] Resposta JSON: {response_data}")
                    return {"status": "Enviado", "detalhes": response_data.get("message", "Mensagem com mídia enviada com sucesso")}
                except ValueError:
                    logger.warning(f"[MIDIA] Resposta não-JSON: {response.text}")
                    if response.text:
                        return {"status": "Enviado?", "detalhes": f"Resposta não-JSON, mas status {response.status_code}: {response.text[:100]}"}
                    return {"status": "Enviado", "detalhes": f"Mensagem com mídia enviada (status {response.status_code}), resposta vazia."}
        except FileNotFoundError:
            logger.error(f"[MIDIA] Arquivo de mídia não encontrado: {caminho_arquivo}")
            return {"status": "Erro de Arquivo", "detalhes": f"Arquivo de mídia não encontrado: {caminho_arquivo}"}
        except requests.HTTPError as http_err:
            logger.error(f"[MIDIA] Erro HTTP: {http_err.response.status_code} | {http_err.response.text}")
            return {"status": "Erro HTTP", "detalhes": f"Erro {http_err.response.status_code}: {http_err.response.text}"}
        except requests.RequestException as req_err:
            logger.error(f"[MIDIA] Erro de Requisição: {req_err}")
            return {"status": "Erro de Requisição", "detalhes": f"Erro de conexão/timeout: {req_err}"}
        except Exception as e:
            logger.exception(f"[MIDIA] Erro inesperado ao enviar mídia para {numero}")
            return {"status": "Erro Inesperado", "detalhes": f"Erro desconhecido ao enviar mídia: {e}"}

# ==================================================
# Funções de Configuração
# ==================================================
def carregar_config_env(caminho_config_str):
    """Carrega o arquivo .env e inicializa o APIClient."""
    global config_env_path_global, api_client_global
    
    config_path = Path(caminho_config_str)
    if not config_path.is_file():
        messagebox.showerror("Erro de Configuração", f"Arquivo config.env não encontrado em: {config_path}")
        return False

    load_dotenv(dotenv_path=config_path)
    api_url = os.getenv("API_URL")
    api_token = os.getenv("API_TOKEN")

    if not api_url or not api_token:
        messagebox.showerror(
            "Erro de Configuração",
            "Variáveis API_URL ou API_TOKEN não encontradas no config.env. Verifique o arquivo."
        )
        return False
    
    try:
        api_client_global = APIClient(api_url, api_token)
        config_env_path_global = config_path # Armazena o caminho globalmente se tudo deu certo
        messagebox.showinfo("Sucesso", "Arquivo config.env carregado e cliente API configurado!")
        return True
    except ValueError as ve:
        messagebox.showerror("Erro de Configuração", str(ve))
        return False

def selecionar_config_env():
    """Permite ao usuário selecionar o arquivo config.env."""
    caminho = filedialog.askopenfilename(
        title="Selecione o arquivo config.env",
        filetypes=[("Arquivos ENV", "*.env")]
    )
    if caminho:
        carregar_config_env(caminho)

def detectar_tipo_mime(caminho_arquivo):
    """Detecta o tipo MIME de um arquivo com base na extensão."""
    tipo_mime, _ = guess_type(caminho_arquivo)
    return tipo_mime or "application/octet-stream" # Fallback genérico

# ==================================================
# Funções de Processamento
# ==================================================
### ALTERAÇÃO INÍCIO ###
# Adicionamos os parâmetros delay_min e delay_max
def processar_envio_individual_thread(fila_trabalho, fila_resultados, mensagem_universal, envia_midia, caminho_imagem, delay_min, delay_max):
### ALTERAÇÃO FIM ###
    """
    Thread worker para processar um único envio.
    Pega um item da fila_trabalho, envia a mensagem e coloca o resultado na fila_resultados.
    """
    global api_client_global 
    if not api_client_global:
        while not fila_trabalho.empty():
            try:
                index, _ = fila_trabalho.get_nowait()
                fila_resultados.put((index, "Erro de Config", "Cliente API não inicializado"))
                fila_trabalho.task_done()
            except Queue.Empty:
                break
        return

    while not fila_trabalho.empty():
        try:
            index, row_data = fila_trabalho.get_nowait()
        except Queue.Empty:
            break

        numero_original = row_data.get('Telefone Celular', '')
        numero_padronizado = padronizar_numero(numero_original)
        
        resultado = {"status": "Não Processado", "detalhes": "Número inválido ou ausente"}

        if numero_padronizado:
            if envia_midia and caminho_imagem and caminho_imagem.strip():
                if not Path(caminho_imagem).is_file():
                    resultado = {"status": "Erro de Arquivo", "detalhes": f"Arquivo de imagem não encontrado: {caminho_imagem}"}
                else:
                    resultado = api_client_global.enviar_mensagem_midia(numero_padronizado, mensagem_universal, caminho_imagem)
            else:
                resultado = api_client_global.enviar_mensagem_texto(numero_padronizado, mensagem_universal)
        
        fila_resultados.put((index, resultado['status'], resultado['detalhes']))
        
        ### ALTERAÇÃO INÍCIO ###
        # Pausa com tempo aleatório entre os envios
        tempo_de_espera = random.uniform(delay_min, delay_max)
        logger.info(f"Pausando por {tempo_de_espera:.2f} segundos antes do próximo envio.")
        time.sleep(tempo_de_espera)
        ### ALTERAÇÃO FIM ###
        
        fila_trabalho.task_done()


def padronizar_numero(numero):
    """Limpa e padroniza o número de telefone para o formato E.164 (Brasil)."""
    if pd.isna(numero) or numero is None:
        return None
    
    numero_str = str(numero)
    if numero_str.startswith('+'):
        numero_limpo = '+' + re.sub(r"[^\d]", "", numero_str[1:])
    else:
        numero_limpo = re.sub(r"[^\d]", "", numero_str)

    if numero_limpo.startswith("55") and len(numero_limpo) > 11 :
        numero_limpo = numero_limpo[2:]
    
    if len(numero_limpo) == 10 or len(numero_limpo) == 11:
        return f"55{numero_limpo}"
    elif numero_limpo.startswith("+55") and (len(numero_limpo) == 13 or len(numero_limpo) == 14):
        return numero_limpo
        
    return None

### ALTERAÇÃO INÍCIO ###
# Adicionamos os parâmetros delay_min e delay_max
def processar_planilha(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar_var, app_controls, delay_min, delay_max):
### ALTERAÇÃO FIM ###
    """
    Função principal para processar a planilha e disparar os envios.
    `app_controls` é um dicionário com widgets da GUI para controle (ex: botão de iniciar).
    """
    btn_iniciar = app_controls.get("btn_iniciar")

    try:
        if not Path(caminho_planilha).is_file():
            messagebox.showerror("Erro de Arquivo", f"Planilha não encontrada: {caminho_planilha}")
            return
        if not Path(caminho_mensagem).is_file():
            messagebox.showerror("Erro de Arquivo", f"Arquivo de mensagem não encontrado: {caminho_mensagem}")
            return
        
        envia_midia = bool(caminho_imagem and caminho_imagem.strip())
        if envia_midia and not Path(caminho_imagem).is_file():
            messagebox.showerror("Erro de Arquivo", f"Arquivo de imagem para envio não encontrado: {caminho_imagem}")
            return

        with open(caminho_mensagem, "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()
        
        if not mensagem_universal:
            messagebox.showwarning("Aviso", "O arquivo de mensagem está vazio.")
            return

        df = pd.read_excel(caminho_planilha, dtype={'Telefone Celular': str})
        
        if 'Telefone Celular' not in df.columns:
            messagebox.showerror("Erro na Planilha", "A coluna 'Telefone Celular' não foi encontrada na planilha.")
            return

        if 'status_envio' not in df.columns:
            df['status_envio'] = ''
        if 'detalhes_envio' not in df.columns:
            df['detalhes_envio'] = ''
        
        df_para_processar = df[df['Telefone Celular'].notna() & (df['Telefone Celular'].astype(str).str.strip() != '')].copy()
        
        total_numeros_para_processar = len(df_para_processar)
        if total_numeros_para_processar == 0:
            messagebox.showinfo("Informação", "Nenhum número válido para processar na planilha.")
            return

        fila_trabalho = Queue()
        fila_resultados = Queue()

        for index, row in df_para_processar.iterrows():
            fila_trabalho.put((index, row.to_dict())) 

        progress_bar_var.set(0)

        num_threads = min(10, os.cpu_count() or 1 + 4)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(
                target=processar_envio_individual_thread,
                ### ALTERAÇÃO INÍCIO ###
                # Passamos os delays para a thread
                args=(fila_trabalho, fila_resultados, mensagem_universal, envia_midia, caminho_imagem, delay_min, delay_max),
                ### ALTERAÇÃO FIM ###
                daemon=True
            )
            thread.start()
            threads.append(thread)

        itens_processados_count = 0
        while itens_processados_count < total_numeros_para_processar:
            if not any(t.is_alive() for t in threads) and fila_trabalho.qsize() > 0 :
                break 
            
            resultados_atuais = fila_resultados.qsize() 
            progresso_atual = (resultados_atuais / total_numeros_para_processar) * 100
            progress_bar_var.set(progresso_atual)
            
            if resultados_atuais >= total_numeros_para_processar:
                    break
            
            janela.update_idletasks()
            time.sleep(0.1)


        fila_trabalho.join()

        for t in threads:
            t.join(timeout=5.0)

        while not fila_resultados.empty():
            try:
                idx, status, detalhes = fila_resultados.get_nowait()
                df.loc[idx, 'status_envio'] = status
                df.loc[idx, 'detalhes_envio'] = detalhes
                fila_resultados.task_done()
            except Queue.Empty:
                break
        
        progress_bar_var.set(100)

        try:
            df.to_excel(caminho_planilha, index=False)
            messagebox.showinfo("Concluído", f"Processo finalizado! Planilha atualizada em: {caminho_planilha}")
        except PermissionError:
            novo_caminho = Path(caminho_planilha)
            novo_caminho_salvar = novo_caminho.with_name(f"{novo_caminho.stem}_atualizado{novo_caminho.suffix}")
            try:
                df.to_excel(novo_caminho_salvar, index=False)
                messagebox.showwarning("Concluído com Aviso", 
                                      f"Não foi possível salvar em '{caminho_planilha}' (pode estar aberto).\n"
                                      f"Planilha atualizada salva como: '{novo_caminho_salvar}'")
            except Exception as e_save:
                messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar a planilha atualizada: {e_save}")

    except FileNotFoundError as fnf_err:
        messagebox.showerror("Erro de Arquivo", str(fnf_err))
    except pd.errors.EmptyDataError:
        messagebox.showerror("Erro na Planilha", "A planilha está vazia ou em formato não reconhecido.")
    except KeyError as ke:
        messagebox.showerror("Erro na Planilha", f"Coluna não encontrada na planilha: {ke}")
    except Exception as e:
        messagebox.showerror("Erro Crítico no Processamento", f"Ocorreu um erro inesperado: {e}")
    finally:
        if btn_iniciar:
            btn_iniciar.config(state=tk.NORMAL)
        progress_bar_var.set(0)

# ==================================================
# Funções de Interface
# ==================================================
def criar_interface(root):
    """Cria e configura os widgets da interface gráfica."""
    global janela
    janela = root
    root.title("Envio de Mensagens Automatizado v2.2")
    root.geometry("650x500") # Aumentamos a altura da janela

    # --- Estilo ---
    style = ttk.Style(root)
    available_themes = style.theme_names()
    if "clam" in available_themes:
        style.theme_use("clam")
    elif "vista" in available_themes:
        style.theme_use("vista")
    
    style.configure("TButton", padding=6, relief="flat", font=('Helvetica', 10))
    style.configure("Blue.TButton", foreground="white", background="#007bff")
    style.configure("Green.TButton", foreground="white", background="#28a745")
    style.configure("Gray.TButton", foreground="white", background="#6c757d")
    style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))

    # --- Variáveis de Controle Tkinter ---
    entrada_var = tk.StringVar()
    mensagem_var = tk.StringVar()
    imagem_var = tk.StringVar()
    progress_bar_var = tk.DoubleVar()
    ### ALTERAÇÃO INÍCIO ###
    delay_min_var = tk.StringVar(value="5") # Valor padrão de 5 segundos
    delay_max_var = tk.StringVar(value="15") # Valor padrão de 15 segundos
    ### ALTERAÇÃO FIM ###

    # --- Frame Principal ---
    main_frame = ttk.Frame(root, padding="10 10 10 10")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # --- Configuração do .env ---
    config_frame = ttk.LabelFrame(main_frame, text="Configuração da API", padding="10")
    config_frame.pack(fill=tk.X, pady=5)
    
    btn_selecionar_env = ttk.Button(
        config_frame, text="1. Selecionar Config.env",
        command=selecionar_config_env, style="Blue.TButton"
    )
    btn_selecionar_env.pack(pady=5)


    # --- Seleção de Arquivos ---
    files_frame = ttk.LabelFrame(main_frame, text="Arquivos de Entrada", padding="10")
    files_frame.pack(fill=tk.X, pady=5)

    ttk.Label(files_frame, text="Planilha de Números (.xlsx):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(files_frame, textvariable=entrada_var, width=50).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    ttk.Button(files_frame, text="Selecionar", command=lambda: selecionar_arquivo_dialog(entrada_var, [("Arquivos Excel", "*.xlsx")])).grid(row=0, column=2, padx=5, pady=5)

    ttk.Label(files_frame, text="Arquivo de Mensagem (.txt):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(files_frame, textvariable=mensagem_var, width=50).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    ttk.Button(files_frame, text="Selecionar", command=lambda: selecionar_arquivo_dialog(mensagem_var, [("Arquivos de Texto", "*.txt")])).grid(row=1, column=2, padx=5, pady=5)

    ttk.Label(files_frame, text="Arquivo de Imagem (Opcional):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(files_frame, textvariable=imagem_var, width=50).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    ttk.Button(files_frame, text="Selecionar", command=lambda: selecionar_arquivo_dialog(imagem_var, [("Arquivos de Imagem", "*.jpg *.jpeg *.png *.gif")])).grid(row=2, column=2, padx=5, pady=5)
    
    files_frame.columnconfigure(1, weight=1)

    ### ALTERAÇÃO INÍCIO ###
    # --- Frame para Configuração de Delay ---
    delay_frame = ttk.LabelFrame(main_frame, text="Configuração de Delay (Intervalo entre mensagens)", padding="10")
    delay_frame.pack(fill=tk.X, pady=(10, 5))

    ttk.Label(delay_frame, text="Delay Mínimo (s):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(delay_frame, textvariable=delay_min_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky="w")
    
    ttk.Label(delay_frame, text="Delay Máximo (s):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    ttk.Entry(delay_frame, textvariable=delay_max_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky="w")
    
    delay_frame.columnconfigure(1, weight=1)
    delay_frame.columnconfigure(3, weight=1)
    ### ALTERAÇÃO FIM ###

    # --- Barra de Progresso ---
    progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate", length=400, variable=progress_bar_var)
    progress_bar.pack(pady=10, fill=tk.X, padx=10)

    # --- Botões de Ação ---
    action_frame = ttk.Frame(main_frame, padding="5")
    action_frame.pack(fill=tk.X)

    btn_iniciar = ttk.Button(
        action_frame, text="Iniciar Envio", style="Green.TButton",
        ### ALTERAÇÃO INÍCIO ###
        # Passamos as novas variáveis de delay
        command=lambda: iniciar_envio_wrapper(entrada_var, mensagem_var, imagem_var, progress_bar_var, {"btn_iniciar": btn_iniciar_ref}, delay_min_var, delay_max_var)
        ### ALTERAÇÃO FIM ###
    )
    btn_iniciar.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    btn_iniciar_ref = btn_iniciar

    btn_sobre = ttk.Button(action_frame, text="Sobre", style="Gray.TButton", command=exibir_sobre)
    btn_sobre.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    # --- Copyright ---
    ttk.Label(main_frame, text="Automação no Envio de Mensagens © 2025 by Gustavo Nascimento", font=('Helvetica', 8)).pack(pady=(10,0))


def selecionar_arquivo_dialog(string_var, file_types):
    """Função auxiliar para selecionar arquivos e atualizar StringVar."""
    caminho = filedialog.askopenfilename(filetypes=file_types)
    if caminho:
        string_var.set(caminho)

### ALTERAÇÃO INÍCIO ###
# Adicionamos os parâmetros delay_min_var e delay_max_var
def iniciar_envio_wrapper(entrada_var, mensagem_var, imagem_var, progress_bar_var, app_controls, delay_min_var, delay_max_var):
### ALTERAÇÃO FIM ###
    """Wrapper para iniciar o processo de envio em uma nova thread."""
    global api_client_global, config_env_path_global

    if not config_env_path_global or not api_client_global:
        messagebox.showwarning("Configuração Necessária", "Por favor, selecione e carregue um arquivo config.env válido primeiro.")
        return

    caminho_planilha = entrada_var.get()
    caminho_mensagem = mensagem_var.get()
    caminho_imagem = imagem_var.get()

    if not caminho_planilha or not caminho_mensagem:
        messagebox.showwarning("Arquivos Faltando", "Selecione a planilha de números e o arquivo de mensagem!")
        return
    
    ### ALTERAÇÃO INÍCIO ###
    # Validação dos valores de delay
    try:
        delay_min = float(delay_min_var.get())
        delay_max = float(delay_max_var.get())
        if delay_min < 0 or delay_max < 0:
            messagebox.showerror("Erro de Valor", "Os valores de delay não podem ser negativos.")
            return
        if delay_min > delay_max:
            messagebox.showerror("Erro de Valor", "O delay mínimo não pode ser maior que o delay máximo.")
            return
    except ValueError:
        messagebox.showerror("Erro de Valor", "Por favor, insira valores numéricos válidos para o delay (ex: 5.5).")
        return
    ### ALTERAÇÃO FIM ###
    
    btn_iniciar = app_controls.get("btn_iniciar")
    if btn_iniciar:
        btn_iniciar.config(state=tk.DISABLED)
    
    progress_bar_var.set(0)

    thread_processamento = threading.Thread(
        target=processar_planilha,
        ### ALTERAÇÃO INÍCIO ###
        # Passamos os valores de delay validados para a função de processamento
        args=(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar_var, app_controls, delay_min, delay_max),
        ### ALTERAÇÃO FIM ###
        daemon=True
    )
    thread_processamento.start()


def exibir_sobre():
    mensagem = (
        "========================================\n"
        "  Envio de Mensagens Automático v2.2\n"
        "  Criado por: Gustavo Nascimento (GN)\n"
        "========================================\n"
        "Copyright (C) 2025, Gustavo Nascimento\n"
        "Todos os direitos reservados.\n\n"
        "Este projeto está licenciado sob a CC BY-NC-ND 4.0:\n"
        "https://creativecommons.org/licenses/by-nc-nd/4.0/\n\n"
        "Você pode compartilhá-lo, mas não pode:\n"
        "- Usar para fins comerciais.\n"
        "- Modificar ou criar obras derivadas.\n"
    )
    messagebox.showinfo("Sobre o Aplicativo", mensagem)

# ==================================================
# Ponto de Entrada Principal
# ==================================================
if __name__ == "__main__":
    janela_principal = tk.Tk()
    criar_interface(janela_principal)
    janela_principal.mainloop()