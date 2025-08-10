# Documentação Técnica — Envio de Mensagens via API (v2.5)

Este documento descreve a arquitetura, fluxos principais e pontos de extensão do aplicativo Tkinter que automatiza o envio de mensagens (texto e mídia) via API.

## Arquitetura em alto nível

- GUI (Tkinter): janela principal, seleção de arquivos, botões de controle, barra de progresso e log em tempo real.
- Núcleo de envio (APIClient): abstrai chamadas HTTP (texto e mídia) com autenticação via Bearer token.
- Pipeline de processamento: leitura de Excel, normalização de números, fila de trabalho/resultados, threads de envio, delays aleatórios e salvamento de resultados.
- Logging assíncrono: handler que envia logs para uma Queue consumida pela GUI (não bloqueia a UI).

## Principais componentes e contratos

- APIClient(api_url: str, api_token: str)
  - enviar_mensagem_texto(number: str, mensagem: str, abrir_ticket: int = 1, id_fila: int = 203) -> dict
  - enviar_mensagem_midia(number: str, mensagem: str, caminho_arquivo: str, abrir_ticket: int = 1, id_fila: int = 203) -> dict
  - Headers: Authorization: Bearer <token>
  - Texto: POST JSON { number, openTicket, queueId, body }
  - Mídia: POST multipart/form-data { number, openTicket, queueId, medias }

- Funções utilitárias
  - carregar_config_env(caminho_config_str: str) -> bool
    - Lê API_URL, API_TOKEN (python-dotenv). Instancia APIClient.
  - detectar_tipo_mime(caminho_arquivo: str) -> str
  - padronizar_numero(numero: Any) -> Optional[str]
    - Remove símbolos, lida com +55, corta 55 duplicado, exige 10 ou 11 dígitos e prefixa 55.

- Processamento
  - processar_planilha(caminho_planilha, caminho_mensagem, caminho_imagem, progress_bar_var, app_controls, delay_min, delay_max, pause_event, cancel_event)
    - Lê Excel (pandas.read_excel) e mensagem (.txt UTF-8)
    - Filtra linhas com "Telefone Celular" não vazio
    - Preenche fila de trabalho e threads
    - Atualiza progress_bar_var conforme resultados chegam
    - Salva <arquivo>_RESULTADOS.xlsx com colunas status_envio/detalhes_envio

- Concorrência
  - 5 threads (daemon) consumindo Queue de trabalho
  - pause_event: controla pausa/retomada
  - cancel_event: interrompe o ciclo de envio

- GUI
  - criar_interface(root) -> ScrolledText
    - Frames: Configuração da API, Arquivos de Entrada, Delay, Ações, Progresso, Log
    - Botões: Iniciar, Pausar/Continuar, Cancelar, Sobre
  - iniciar_envio_wrapper(...): valida entradas, configura eventos e inicia thread de processamento

## Fluxo de execução

1. Usuário seleciona config.env e arquivos de entrada.
2. Aplicativo carrega API_URL e API_TOKEN e instancia APIClient.
3. Ao iniciar, planilha + mensagem são lidas; imagem opcional é validada.
4. Threads enviam mensagem texto/mídia conforme seleção.
5. Resultados são agregados e salvos no Excel final.
6. GUI exibe progresso e logs; usuário pode pausar/continuar/cancelar.

## Formatos e colunas

- Planilha de entrada: Excel (.xlsx), coluna obrigatória: "Telefone Celular".
- Resultado: adiciona colunas:
  - status_envio: Ex.: "Enviado", "Erro", "Erro (Mídia)", "Erro de Arquivo".
  - detalhes_envio: Texto com detalhes/trace do erro.

## Tratamento de erros e logs

- Todas as chamadas à API utilizam try/except com logger.info/debug/error/critical.
- GUI mostra messagebox em erros críticos (ex.: config ausente, variáveis não definidas).
- Tempo de espera entre envios (random.uniform) para reduzir risco de bloqueios.

## Dependências

- pandas, openpyxl, requests, python-dotenv, tkinter (padrão no Windows), logging

Arquivo requirements.txt sugerido:

```
pandas
openpyxl
requests
python-dotenv
```

## Pontos de extensão

- Suporte a outros canais: criar novas estratégias dentro do APIClient.
- Leitura de outras colunas (nome, tags) para personalização de mensagem.
- Rate-limiting inteligente conforme retorno da API.
- Persistência incremental de resultados (checkpoint) para evitar perda em cancelamentos.

## Segurança

- Não versionar config.env com segredos.
- Token é usado apenas em memória; evite logs com o valor do token.

## Changelog (v2.5 — 2025-08-10)

- Nova classe APIClient e reorganização das chamadas HTTP.
- Envio de mídia (multipart) seguido de texto.
- GUI revisada com botões de controle e "Sobre".
- Logs assíncronos via QueueHandler e barra de progresso.
- Normalização de números mais robusta.
- Threads múltiplas com delays configuráveis.
- Geração do Excel de resultados com status/detalhes por linha.
