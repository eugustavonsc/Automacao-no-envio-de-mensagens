# Automação no Envio de Mensagens © 2025 by Gustavo Nascimento
# Licenciado sob CC BY-NC-ND 4.0. Para detalhes, visite https://creativecommons.org/licenses/by-nc-nd/4.0/
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import pandas as pd
import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import time
import threading
from queue import Queue, Empty
import re
from mimetypes import guess_type
import logging
import random

# ==================================================
# CLASSES AUXILIARES
# ==================================================
class QueueHandler(logging.Handler):
    """ Envia registros de log para uma fila para serem processados pela GUI. """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

class APIClient:
    """ Encapsula a lógica de comunicação com a API de envio de mensagens. """
    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.api_token = api_token
        self.base_headers = {"Authorization": f"Bearer {self.api_token}"}

    def enviar_mensagem_texto(self, numero, mensagem, abrir_ticket=1, id_fila=203):
        headers = {**self.base_headers, "Content-Type": "application/json"}
        payload = {
            "number": numero,
            "openTicket": str(abrir_ticket),
            "queueId": str(id_fila),
            "body": mensagem
        }
        logger.info(f"[TEXTO] Enviando para {numero}...")
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=25)
            logger.debug(f"[TEXTO] Resposta: {response.text}")
            response.raise_for_status()
            logger.info(f"[TEXTO] Mensagem para {numero} enviada com sucesso.")
            return {"status": "Enviado", "detalhes": "Mensagem enviada com sucesso"}
        except Exception as e:
            logger.error(f"[TEXTO] Falha ao enviar para {numero}: {e}")
            return {"status": "Erro", "detalhes": str(e)}

    def enviar_mensagem_midia(self, numero, mensagem, caminho_arquivo, abrir_ticket=1, id_fila=203):
        headers = {**self.base_headers, "Origin": "https://sac.lifthubsolucoes.com.br", "Referer": "https://sac.lifthubsolucoes.com.br/"}
        logger.info(f"[MÍDIA 1/2] Enviando arquivo para {numero}...")
        try:
            with open(caminho_arquivo, "rb") as arquivo_midia:
                tipo_mime = detectar_tipo_mime(caminho_arquivo)
                data_payload = {
                    "number": numero,
                    "openTicket": str(abrir_ticket),
                    "queueId": str(id_fila)
                }
                files_payload = {
                    "medias": (os.path.basename(caminho_arquivo), arquivo_midia, tipo_mime)
                }
                response_media = requests.post(self.api_url, headers=headers, data=data_payload, files=files_payload, timeout=30)
                logger.debug(f"[MÍDIA 1/2] Resposta: {response_media.text}")
                response_media.raise_for_status()
                logger.info(f"[MÍDIA 2/2] Arquivo enviado. Enviando texto para {numero}.")
                return self.enviar_mensagem_texto(numero, mensagem, abrir_ticket, id_fila)
        except Exception as e:
            logger.error(f"[MÍDIA] Falha ao enviar mídia para {numero}: {e}")
            return {"status": "Erro (Mídia)", "detalhes": str(e)}

# ==================================================
# VARIÁVEIS GLOBAIS
# ==================================================
config_env_path_global = None
api_client_global = None
janela = None

# ==================================================
# FUNÇÕES DE LÓGICA E PROCESSAMENTO
# ==================================================
def carregar_config_env(caminho_config_str):
    global config_env_path_global, api_client_global
    config_path = Path(caminho_config_str)
    if not config_path.is_file():
        messagebox.showerror("Erro", f"config.env não encontrado: {config_path}")
        return False
    load_dotenv(dotenv_path=config_path)
    api_url, api_token = os.getenv("API_URL"), os.getenv("API_TOKEN")
    if not api_url or not api_token:
        messagebox.showerror("Erro", "API_URL ou API_TOKEN não encontrados no config.env.")
        return False
    try:
        api_client_global = APIClient(api_url, api_token)
        config_env_path_global = config_path
        logger.info("Config.env carregado e cliente API configurado com sucesso.")
        messagebox.showinfo("Sucesso", "Config.env carregado!")
        return True
    except ValueError as ve:
        messagebox.showerror("Erro de Configuração", str(ve))
        return False

def detectar_tipo_mime(caminho_arquivo):
    tipo_mime, _ = guess_type(caminho_arquivo)
    return tipo_mime or "application/octet-stream"

def padronizar_numero(numero):
    if pd.isna(numero) or numero is None: return None
    numero_str = str(numero)
    numero_limpo = re.sub(r"[^\d]", "", numero_str.lstrip('+'))
    if numero_limpo.startswith("55") and len(numero_limpo) > 11:
        numero_limpo = numero_limpo[2:]
    if len(numero_limpo) in [10, 11]:
        return f"55{numero_limpo}"
    return None

def processar_envio_individual_thread(fila_trabalho, fila_resultados, mensagem_universal, envia_midia, caminho_imagem, delay_min, delay_max, pause_event, cancel_event):
    if not api_client_global:
        logger.error("Cliente API não configurado.")
        return
    
    while not fila_trabalho.empty():
        if cancel_event.is_set():
            logger.warning("Cancelamento detectado. Encerrando thread de envio.")
            break
        
        pause_event.wait()
        
        try:
            index, row_data = fila_trabalho.get_nowait()
        except Empty:
            continue
            
        numero_original = row_data.get('Telefone Celular', '')
        numero_padronizado = padronizar_numero(numero_original)
        resultado = {"status": "Não Processado", "detalhes": "Número inválido ou ausente"}
        
        if numero_padronizado:
            if envia_midia and caminho_imagem:
                if not Path(caminho_imagem).is_file():
                    resultado = {"status": "Erro de Arquivo", "detalhes": f"Imagem não encontrada"}
                else:
                    resultado = api_client_global.enviar_mensagem_midia(numero_padronizado, mensagem_universal, caminho_imagem)
            else:
                resultado = api_client_global.enviar_mensagem_texto(numero_padronizado, mensagem_universal)
        
        fila_resultados.put((index, resultado['status'], resultado['detalhes']))
        
        if not cancel_event.is_set():
            tempo_de_espera = random.uniform(delay_min, delay_max)
            logger.info(f"Pausa de {tempo_de_espera:.1f}s...")
            time.sleep(tempo_de_espera)

        fila_trabalho.task_done()

def processar_planilha(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar_var, app_controls, delay_min, delay_max, pause_event, cancel_event):
    btn_iniciar = app_controls.get("btn_iniciar")
    btn_pausar = app_controls.get("btn_pausar")
    btn_cancelar = app_controls.get("btn_cancelar")

    try:
        logger.info("Iniciando processamento da planilha...")
        df = pd.read_excel(caminho_planilha, dtype={'Telefone Celular': str})
        with open(caminho_mensagem, "r", encoding="utf-8") as file:
            mensagem_universal = file.read().strip()
            
        df_para_processar = df[df['Telefone Celular'].notna() & (df['Telefone Celular'].astype(str).str.strip() != '')].copy()
        total_a_processar = len(df_para_processar)
        
        if total_a_processar == 0:
            logger.warning("Nenhum número válido encontrado na planilha.")
            messagebox.showinfo("Info", "Nenhum número válido para processar.")
            return
            
        logger.info(f"Encontrados {total_a_processar} números válidos para envio.")
        
        fila_trabalho, fila_resultados = Queue(), Queue()
        for index, row in df_para_processar.iterrows():
            fila_trabalho.put((index, row.to_dict()))
        
        threads = []
        num_threads = 5
        for _ in range(num_threads):
            thread = threading.Thread(target=processar_envio_individual_thread, args=(fila_trabalho, fila_resultados, mensagem_universal, bool(caminho_imagem), caminho_imagem, delay_min, delay_max, pause_event, cancel_event), daemon=True)
            thread.start()
            threads.append(thread)
        
        while fila_resultados.qsize() < total_a_processar:
            if cancel_event.is_set():
                logger.info("Processo de monitoramento encerrado devido ao cancelamento.")
                break
            if not any(t.is_alive() for t in threads) and fila_trabalho.empty():
                break
            progresso = (fila_resultados.qsize() / total_a_processar) * 100
            progress_bar_var.set(progresso)
            janela.update_idletasks()
            time.sleep(0.2)

        if 'status_envio' not in df.columns: df['status_envio'] = ''
        if 'detalhes_envio' not in df.columns: df['detalhes_envio'] = ''
        while not fila_resultados.empty():
            idx, status, detalhes = fila_resultados.get_nowait()
            df.loc[idx, 'status_envio'] = status
            df.loc[idx, 'detalhes_envio'] = detalhes
            
        caminho_final = f"{Path(caminho_planilha).stem}_RESULTADOS.xlsx"
        df.to_excel(caminho_final, index=False)
        logger.info(f"Planilha de resultados salva em: {caminho_final}")
        
        if not cancel_event.is_set():
            logger.info("Processamento finalizado normalmente.")
            messagebox.showinfo("Concluído", "Envios finalizados!")
            progress_bar_var.set(100)
        else:
            logger.info("Processamento interrompido pelo usuário.")
            messagebox.showwarning("Cancelado", "O processo de envio foi cancelado.")

    except Exception as e:
        logger.critical(f"Erro crítico no processamento: {e}", exc_info=True)
        messagebox.showerror("Erro Crítico", f"Ocorreu um erro inesperado: {e}")
    finally:
        logger.info("Resetando interface.")
        btn_iniciar.config(state=tk.NORMAL)
        btn_pausar.config(text="Pausar", state=tk.DISABLED)
        btn_cancelar.config(state=tk.DISABLED)
        progress_bar_var.set(0)

# ==================================================
# FUNÇÕES DE INTERFACE (GUI)
# ==================================================
def selecionar_config_env():
    caminho = filedialog.askopenfilename(title="Selecione o config.env", filetypes=[("Arquivos ENV", "*.env")])
    if caminho:
        carregar_config_env(caminho)
        
def selecionar_arquivo_dialog(string_var, file_types):
    """Função auxiliar para abrir a janela de seleção de arquivo."""
    caminho = filedialog.askopenfilename(title="Selecione o arquivo", filetypes=file_types)
    if caminho:
        string_var.set(caminho)

def criar_interface(root):
    global janela
    janela = root
    root.title("Envio de Mensagens Automatizado v2.5")
    root.geometry("700x650")

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Variáveis de Controle
    entrada_var, mensagem_var, imagem_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
    delay_min_var, delay_max_var = tk.StringVar(value="5"), tk.StringVar(value="15")
    progress_bar_var = tk.DoubleVar()

    # Frames
    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(expand=True, fill=tk.BOTH)
    config_frame = ttk.LabelFrame(main_frame, text="1. Configuração da API", padding="10")
    config_frame.pack(fill=tk.X, pady=5)
    files_frame = ttk.LabelFrame(main_frame, text="2. Arquivos de Entrada", padding="10")
    files_frame.pack(fill=tk.X, pady=5)
    delay_frame = ttk.LabelFrame(main_frame, text="3. Configuração de Delay", padding="10")
    delay_frame.pack(fill=tk.X, pady=5)
    action_frame = ttk.Frame(main_frame, padding="5 0")
    action_frame.pack(fill=tk.X)
    progress_frame = ttk.Frame(main_frame, padding="5 0")
    progress_frame.pack(fill=tk.X, pady=10)
    log_frame = ttk.LabelFrame(main_frame, text="Log de Atividades", padding="10")
    log_frame.pack(expand=True, fill=tk.BOTH, pady=5)

    # Widgets
    ttk.Button(config_frame, text="Selecionar Config.env", command=selecionar_config_env).pack()

    ttk.Label(files_frame, text="Planilha:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(files_frame, textvariable=entrada_var, width=60).grid(row=0, column=1, sticky="ew", pady=2)
    ttk.Button(files_frame, text="...", width=4, command=lambda: selecionar_arquivo_dialog(entrada_var, [("Excel", "*.xlsx")])).grid(row=0, column=2, padx=5, pady=2)

    ttk.Label(files_frame, text="Mensagem:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(files_frame, textvariable=mensagem_var, width=60).grid(row=1, column=1, sticky="ew", pady=2)
    ttk.Button(files_frame, text="...", width=4, command=lambda: selecionar_arquivo_dialog(mensagem_var, [("Texto", "*.txt")])).grid(row=1, column=2, padx=5, pady=2)

    ttk.Label(files_frame, text="Imagem (Opc):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(files_frame, textvariable=imagem_var, width=60).grid(row=2, column=1, sticky="ew", pady=2)
    ttk.Button(files_frame, text="...", width=4, command=lambda: selecionar_arquivo_dialog(imagem_var, [("Imagens", "*.jpg *.jpeg *.png")])).grid(row=2, column=2, padx=5, pady=2)
    files_frame.columnconfigure(1, weight=1)

    ttk.Label(delay_frame, text="Mín (s):").grid(row=0, column=0, padx=5)
    ttk.Entry(delay_frame, textvariable=delay_min_var, width=5).grid(row=0, column=1, padx=(0, 10))
    ttk.Label(delay_frame, text="Máx (s):").grid(row=0, column=2, padx=5)
    ttk.Entry(delay_frame, textvariable=delay_max_var, width=5).grid(row=0, column=3, padx=(0, 10))

    btn_iniciar = ttk.Button(action_frame, text="Iniciar Envio")
    btn_pausar = ttk.Button(action_frame, text="Pausar", state=tk.DISABLED)
    btn_cancelar = ttk.Button(action_frame, text="Cancelar", state=tk.DISABLED)
    
    ### CORREÇÃO ### - Botão "Sobre" adicionado aqui
    btn_sobre = ttk.Button(action_frame, text="Sobre", command=exibir_sobre)

    btn_iniciar.config(command=lambda: iniciar_envio_wrapper(entrada_var, mensagem_var, imagem_var, progress_bar_var,{"btn_iniciar": btn_iniciar, "btn_pausar": btn_pausar, "btn_cancelar": btn_cancelar}, delay_min_var, delay_max_var))

    btn_iniciar.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    btn_pausar.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    btn_cancelar.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 5))
    btn_sobre.pack(side=tk.LEFT, expand=True, fill=tk.X) ### CORREÇÃO ###
    
    ttk.Progressbar(progress_frame, variable=progress_bar_var).pack(fill=tk.X)

    log_widget = ScrolledText(log_frame, state='disabled', height=10, wrap=tk.WORD, font=("Consolas", 9))
    log_widget.pack(expand=True, fill=tk.BOTH)

    ttk.Label(main_frame, text="© 2025 by Gustavo Nascimento", font=('Helvetica', 8)).pack(side=tk.BOTTOM, pady=(10, 0))

    return log_widget

def iniciar_envio_wrapper(entrada_var, mensagem_var, imagem_var, progress_bar_var, app_controls, delay_min_var, delay_max_var):
    if not entrada_var.get() or not mensagem_var.get():
        messagebox.showwarning("Atenção", "Selecione a planilha e o arquivo de mensagem."); return
    
    pause_event = threading.Event()
    cancel_event = threading.Event()
    pause_event.set()
    
    btn_iniciar, btn_pausar, btn_cancelar = app_controls['btn_iniciar'], app_controls['btn_pausar'], app_controls['btn_cancelar']

    btn_pausar.config(command=lambda: toggle_pause(pause_event, btn_pausar))
    btn_cancelar.config(command=lambda: cancel_envio(cancel_event, pause_event))

    btn_iniciar.config(state=tk.DISABLED)
    btn_pausar.config(state=tk.NORMAL)
    btn_cancelar.config(state=tk.NORMAL)

    thread_processamento = threading.Thread(
        target=processar_planilha,
        args=(
            entrada_var.get(), mensagem_var.get(), imagem_var.get(), progress_bar_var,
            app_controls, float(delay_min_var.get()), float(delay_max_var.get()),
            pause_event, cancel_event
        ),
        daemon=True
    )
    thread_processamento.start()

def toggle_pause(pause_event, btn_pausar):
    if pause_event.is_set():
        pause_event.clear()
        btn_pausar.config(text="Continuar")
        logger.info("Envio pausado pelo usuário.")
    else:
        pause_event.set()
        btn_pausar.config(text="Pausar")
        logger.info("Envio retomado.")

def cancel_envio(cancel_event, pause_event):
    if messagebox.askyesno("Cancelar Envio", "Tem certeza que deseja cancelar o envio?"):
        logger.warning("Solicitação de cancelamento confirmada.")
        cancel_event.set()
        if not pause_event.is_set():
            pause_event.set()

def poll_log_queue(log_widget, log_queue):
    while True:
        try:
            record = log_queue.get(block=False)
        except Empty:
            break
        else:
            log_widget.config(state='normal')
            log_widget.insert(tk.END, record + '\n')
            log_widget.config(state='disabled')
            log_widget.see(tk.END)
    janela.after(100, poll_log_queue, log_widget, log_queue)
    
def exibir_sobre():
    messagebox.showinfo("Sobre", "Envio de Mensagens v2.5\nCriado por Gustavo Nascimento\nLicença CC BY-NC-ND 4.0")

## ==================================================
# PONTO DE ENTRADA PRINCIPAL
# ==================================================
if __name__ == "__main__":
    log_queue = Queue()
    queue_handler = QueueHandler(log_queue)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
    queue_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)
    
    janela_principal = tk.Tk()
    log_widget_ref = criar_interface(janela_principal)
    
    janela_principal.after(100, poll_log_queue, log_widget_ref, log_queue)
    janela_principal.mainloop()