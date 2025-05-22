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

# --- Variáveis Globais ---
# Idealmente, seriam gerenciadas dentro de uma classe de aplicação
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

    def enviar_mensagem_texto(self, numero, mensagem, abrir_ticket=0):
        """
        Envia uma mensagem de texto simples.
        Retorna um dicionário com 'status' e 'detalhes'.
        """
        headers = {**self.base_headers, "Content-Type": "application/json"}
        payload = {
            "number": numero,
            "openTicket": str(abrir_ticket), # API pode esperar string
            "body": mensagem
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=25) # Adicionado timeout
            response.raise_for_status() # Levanta HTTPError para respostas 4xx/5xx
            # Tenta decodificar JSON, mas trata caso de resposta vazia ou não-JSON
            try:
                response_data = response.json()
                # Adapte a verificação de sucesso conforme a resposta real da sua API
                # Exemplo: if response_data.get("success"):
                return {"status": "Enviado", "detalhes": response_data.get("message", "Mensagem enviada com sucesso")}
            except ValueError: # requests.exceptions.JSONDecodeError em versões mais novas
                 if response.text: # Se houver texto, pode ser um HTML de erro ou outra coisa
                     return {"status": "Enviado?", "detalhes": f"Resposta não-JSON, mas status {response.status_code}: {response.text[:100]}"}
                 return {"status": "Enviado", "detalhes": f"Mensagem enviada (status {response.status_code}), resposta vazia."}

        except requests.HTTPError as http_err:
            return {"status": "Erro HTTP", "detalhes": f"Erro {http_err.response.status_code}: {http_err.response.text}"}
        except requests.RequestException as req_err:
            return {"status": "Erro de Requisição", "detalhes": f"Erro de conexão/timeout: {req_err}"}
        except Exception as e:
            return {"status": "Erro Inesperado", "detalhes": f"Erro desconhecido: {e}"}

    def enviar_mensagem_midia(self, numero, mensagem, caminho_arquivo, abrir_ticket=0, id_fila=0):
        """
        Envia uma mensagem com arquivo de mídia.
        Retorna um dicionário com 'status' e 'detalhes'.
        """
        headers = {
            **self.base_headers,
            # "Origin" e "Referer" podem não ser necessários para todas as APIs
            # ou podem precisar ser configuráveis.
            "Origin": "https://sac.lifthubsolucoes.com.br",
            "Referer": "https://sac.lifthubsolucoes.com.br/",
        }
        try:
            with open(caminho_arquivo, "rb") as arquivo_midia:
                tipo_mime = detectar_tipo_mime(caminho_arquivo)
                
                data_payload = {
                    "number": numero,
                    "openTicket": str(abrir_ticket),
                    "queueId": str(id_fila),
                    "Body": mensagem
                }
                files_payload = {
                    "medias": (
                        os.path.basename(caminho_arquivo),
                        arquivo_midia,
                        tipo_mime
                    )
                }
                response = requests.post(self.api_url, headers=headers, data=data_payload, files=files_payload, timeout=30) # Timeout maior para uploads
                response.raise_for_status()
                try:
                    response_data = response.json()
                    return {"status": "Enviado", "detalhes": response_data.get("message", "Mensagem com mídia enviada com sucesso")}
                except ValueError:
                    if response.text:
                         return {"status": "Enviado?", "detalhes": f"Resposta não-JSON, mas status {response.status_code}: {response.text[:100]}"}
                    return {"status": "Enviado", "detalhes": f"Mensagem com mídia enviada (status {response.status_code}), resposta vazia."}

        except FileNotFoundError:
            return {"status": "Erro de Arquivo", "detalhes": f"Arquivo de mídia não encontrado: {caminho_arquivo}"}
        except requests.HTTPError as http_err:
            return {"status": "Erro HTTP", "detalhes": f"Erro {http_err.response.status_code}: {http_err.response.text}"}
        except requests.RequestException as req_err:
            return {"status": "Erro de Requisição", "detalhes": f"Erro de conexão/timeout: {req_err}"}
        except Exception as e:
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
def processar_envio_individual_thread(fila_trabalho, fila_resultados, mensagem_universal, envia_midia, caminho_imagem):
    """
    Thread worker para processar um único envio.
    Pega um item da fila_trabalho, envia a mensagem e coloca o resultado na fila_resultados.
    """
    global api_client_global # Acessa o cliente API global
    if not api_client_global:
        # Isso não deveria acontecer se a configuração for forçada antes do envio
        # Coloca um resultado de erro genérico para cada item que não pôde ser processado
        while not fila_trabalho.empty():
            try:
                index, _ = fila_trabalho.get_nowait() # Pega o índice para reportar o erro
                fila_resultados.put((index, "Erro de Config", "Cliente API não inicializado"))
                fila_trabalho.task_done()
            except Queue.Empty: # Fila pode esvaziar entre o while e o get_nowait
                break
        return

    while not fila_trabalho.empty():
        try:
            index, row_data = fila_trabalho.get_nowait()
        except Queue.Empty:
            break # Fila ficou vazia, encerra a thread

        numero_original = row_data.get('Telefone Celular', '') # Pega o número da linha
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
        time.sleep(1) # Pausa para não sobrecarregar a API (ajuste conforme necessário)
        fila_trabalho.task_done()


def padronizar_numero(numero):
    """Limpa e padroniza o número de telefone para o formato E.164 (Brasil)."""
    if pd.isna(numero) or numero is None: # Checa se é NaN ou None
        return None
    
    numero_str = str(numero)
    # Remove caracteres não numéricos, exceto o '+' se estiver no início
    if numero_str.startswith('+'):
        numero_limpo = '+' + re.sub(r"[^\d]", "", numero_str[1:])
    else:
        numero_limpo = re.sub(r"[^\d]", "", numero_str)

    # Lógica de padronização (exemplo para Brasil)
    # Remove DDI 55 se já presente para evitar duplicidade
    if numero_limpo.startswith("55") and len(numero_limpo) > 11 : # ex: 55119...
        numero_limpo = numero_limpo[2:]
    
    # Adiciona DDI 55 se não tiver e for um número brasileiro válido (10 ou 11 dígitos)
    if len(numero_limpo) == 10 or len(numero_limpo) == 11: # DDD + 8 ou 9 dígitos
        return f"55{numero_limpo}"
    elif numero_limpo.startswith("+55") and (len(numero_limpo) == 13 or len(numero_limpo) == 14): # Formato +55119...
        return numero_limpo
        
    return None # Retorna None se não conseguir padronizar


def processar_planilha(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar_var, app_controls):
    """
    Função principal para processar a planilha e disparar os envios.
    `app_controls` é um dicionário com widgets da GUI para controle (ex: botão de iniciar).
    """
    btn_iniciar = app_controls.get("btn_iniciar")

    try:
        # Validações iniciais
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

        df = pd.read_excel(caminho_planilha, dtype={'Telefone Celular': str}) # Lê 'Telefone Celular' como string
        
        if 'Telefone Celular' not in df.columns:
            messagebox.showerror("Erro na Planilha", "A coluna 'Telefone Celular' não foi encontrada na planilha.")
            return

        if 'status_envio' not in df.columns:
            df['status_envio'] = ''
        if 'detalhes_envio' not in df.columns:
            df['detalhes_envio'] = ''
        
        # Filtra linhas onde a coluna 'Telefone Celular' não é NaN/NaT e não é vazia após strip
        # A padronização posterior cuidará da validade do formato
        df_para_processar = df[df['Telefone Celular'].notna() & (df['Telefone Celular'].astype(str).str.strip() != '')].copy()
        
        total_numeros_para_processar = len(df_para_processar)
        if total_numeros_para_processar == 0:
            messagebox.showinfo("Informação", "Nenhum número válido para processar na planilha.")
            return

        fila_trabalho = Queue()
        fila_resultados = Queue()

        for index, row in df_para_processar.iterrows():
            # Coloca o índice original do DataFrame e os dados da linha na fila
            fila_trabalho.put((index, row.to_dict())) 

        progress_bar_var.set(0) # Reseta a barra de progresso

        num_threads = min(10, os.cpu_count() or 1 + 4) # Limita a 10 threads ou baseado em CPU

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(
                target=processar_envio_individual_thread,
                args=(fila_trabalho, fila_resultados, mensagem_universal, envia_midia, caminho_imagem),
                daemon=True # Threads daemon terminam quando o programa principal termina
            )
            thread.start()
            threads.append(thread)

        # Monitorar progresso e atualizar GUI (de forma segura)
        # Esta parte ainda roda na thread da GUI que chamou processar_planilha,
        # ou na thread que `iniciar_envio` criou.
        # Para atualizar a barra de progresso de forma mais suave:
        itens_processados_count = 0
        while itens_processados_count < total_numeros_para_processar:
            # Verifica se alguma thread ainda está viva; se não, pode haver um problema
            if not any(t.is_alive() for t in threads) and fila_trabalho.qsize() > 0 :
                # Todas as threads morreram, mas ainda há trabalho.
                # Pode ser que o api_client não foi inicializado.
                # Os itens restantes na fila_trabalho não serão processados.
                # Vamos consumir a fila de resultados e sair.
                break 
            
            # Atualiza a barra de progresso com base no número de resultados recebidos
            # Não bloqueia indefinidamente, apenas verifica o tamanho da fila de resultados
            resultados_atuais = fila_resultados.qsize() 
            # O progresso é baseado em quantos itens foram colocados na fila de resultados
            # (assumindo que cada item na fila de trabalho gera um resultado)
            
            # Para evitar que itens_processados_count ultrapasse total_numeros_para_processar
            # devido a itens que não foram para a fila de trabalho mas são contabilizados.
            # O progresso real é baseado nos itens que *entraram* na fila de trabalho.
            
            # Correção: O progresso deve ser baseado nos itens que SAÍRAM da fila de trabalho
            # e tiveram um resultado colocado na fila_resultados.
            # O total para a barra é total_numeros_para_processar.
            # O valor atual é o número de itens na fila_resultados.
            
            progresso_atual = (resultados_atuais / total_numeros_para_processar) * 100
            progress_bar_var.set(progresso_atual)
            
            # Se todos os resultados esperados foram recebidos, podemos sair do loop
            if resultados_atuais >= total_numeros_para_processar:
                 break
            
            janela.update_idletasks() # Atualiza a GUI
            time.sleep(0.1) # Pequena pausa para não sobrecarregar o loop da GUI


        fila_trabalho.join() # Espera que todos os itens da fila de trabalho sejam processados

        for t in threads: # Espera todas as threads terminarem
            t.join(timeout=5.0) # Adiciona um timeout para evitar bloqueio indefinido

        # Coletar todos os resultados
        while not fila_resultados.empty():
            try:
                idx, status, detalhes = fila_resultados.get_nowait()
                df.loc[idx, 'status_envio'] = status
                df.loc[idx, 'detalhes_envio'] = detalhes
                fila_resultados.task_done()
            except Queue.Empty:
                break
        
        progress_bar_var.set(100) # Garante que a barra chegue a 100%

        # Salva a planilha original com as novas colunas
        # Tenta salvar, com fallback para um novo nome se o original estiver aberto/bloqueado
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
            btn_iniciar.config(state=tk.NORMAL) # Reabilita o botão de iniciar
        progress_bar_var.set(0) # Reseta a barra ao final ou em caso de erro

# ==================================================
# Funções de Interface
# ==================================================
def criar_interface(root):
    """Cria e configura os widgets da interface gráfica."""
    global janela # Para update_idletasks
    janela = root
    root.title("Envio de Mensagens Automatizado v2.1")
    root.geometry("650x400") # Tamanho inicial da janela

    # --- Estilo ---
    style = ttk.Style(root)
    # Tenta usar um tema mais moderno se disponível
    available_themes = style.theme_names()
    if "clam" in available_themes:
        style.theme_use("clam")
    elif "vista" in available_themes: # Para Windows
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

    # Planilha
    ttk.Label(files_frame, text="Planilha de Números (.xlsx):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(files_frame, textvariable=entrada_var, width=50).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    ttk.Button(files_frame, text="Selecionar", command=lambda: selecionar_arquivo_dialog(entrada_var, [("Arquivos Excel", "*.xlsx")])).grid(row=0, column=2, padx=5, pady=5)

    # Mensagem
    ttk.Label(files_frame, text="Arquivo de Mensagem (.txt):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(files_frame, textvariable=mensagem_var, width=50).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    ttk.Button(files_frame, text="Selecionar", command=lambda: selecionar_arquivo_dialog(mensagem_var, [("Arquivos de Texto", "*.txt")])).grid(row=1, column=2, padx=5, pady=5)

    # Imagem (Opcional)
    ttk.Label(files_frame, text="Arquivo de Imagem (Opcional):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(files_frame, textvariable=imagem_var, width=50).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    ttk.Button(files_frame, text="Selecionar", command=lambda: selecionar_arquivo_dialog(imagem_var, [("Arquivos de Imagem", "*.jpg *.jpeg *.png *.gif")])).grid(row=2, column=2, padx=5, pady=5)
    
    files_frame.columnconfigure(1, weight=1) # Faz o Entry expandir

    # --- Barra de Progresso ---
    progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate", length=400, variable=progress_bar_var)
    progress_bar.pack(pady=10, fill=tk.X, padx=10)

    # --- Botões de Ação ---
    action_frame = ttk.Frame(main_frame, padding="5")
    action_frame.pack(fill=tk.X)

    btn_iniciar = ttk.Button(
        action_frame, text="Iniciar Envio", style="Green.TButton",
        command=lambda: iniciar_envio_wrapper(entrada_var, mensagem_var, imagem_var, progress_bar_var, {"btn_iniciar": btn_iniciar_ref})
    )
    btn_iniciar.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    btn_iniciar_ref = btn_iniciar # Referência para passar para processar_planilha

    btn_sobre = ttk.Button(action_frame, text="Sobre", style="Gray.TButton", command=exibir_sobre)
    btn_sobre.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    # --- Copyright ---
    ttk.Label(main_frame, text="Automação no Envio de Mensagens © 2025 by Gustavo Nascimento", font=('Helvetica', 8)).pack(pady=(10,0))


def selecionar_arquivo_dialog(string_var, file_types):
    """Função auxiliar para selecionar arquivos e atualizar StringVar."""
    caminho = filedialog.askopenfilename(filetypes=file_types)
    if caminho:
        string_var.set(caminho)

def iniciar_envio_wrapper(entrada_var, mensagem_var, imagem_var, progress_bar_var, app_controls):
    """Wrapper para iniciar o processo de envio em uma nova thread."""
    global api_client_global, config_env_path_global

    if not config_env_path_global or not api_client_global:
        messagebox.showwarning("Configuração Necessária", "Por favor, selecione e carregue um arquivo config.env válido primeiro.")
        return

    caminho_planilha = entrada_var.get()
    caminho_mensagem = mensagem_var.get()
    caminho_imagem = imagem_var.get() # Pode ser vazio

    if not caminho_planilha or not caminho_mensagem:
        messagebox.showwarning("Arquivos Faltando", "Selecione a planilha de números e o arquivo de mensagem!")
        return
    
    # Desabilita o botão de iniciar
    btn_iniciar = app_controls.get("btn_iniciar")
    if btn_iniciar:
        btn_iniciar.config(state=tk.DISABLED)
    
    progress_bar_var.set(0) # Reseta a barra de progresso

    # Executa o processamento em uma thread separada para não bloquear a GUI
    thread_processamento = threading.Thread(
        target=processar_planilha,
        args=(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar_var, app_controls),
        daemon=True
    )
    thread_processamento.start()


def exibir_sobre():
    mensagem = (
        "========================================\n"
        "  Envio de Mensagens Automático v2.1\n"
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
